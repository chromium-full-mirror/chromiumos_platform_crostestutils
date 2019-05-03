#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Wrapper for tests that are run on builders."""

from __future__ import print_function

import argparse
import os
import sys

import constants
sys.path.append(constants.SOURCE_ROOT)
sys.path.append(constants.CROS_PLATFORM_ROOT)

from chromite.lib import cros_build_lib
from chromite.lib import cros_logging as logging
from crostestutils.lib import image_extractor
from crostestutils.lib import test_helper


class TestException(Exception):
  """Thrown by RunAUTestHarness if there's a test failure."""


class CTest(object):
  """Main class with methods to generate payloads and test them.

  Variables:
    base: Base image to test from.
    board: the board for the latest image.
    archive_dir: Location where images for past versions are archived.
    crosutils_root: Location of crosutils.
    jobs: Numbers of threads to run in parallel.
    no_graphics: boolean: If True, disable graphics during vm test.
    remote: ip address for real test harness run.
    target: Target image to test.
    test_results_root: Root directory to store au_test_harness results.
    type: which test harness to run.  Possible values: real, vm, gce.
    whitelist_chrome_crashes: Whether to treat Chrome crashes as non-fatal.
  """

  def __init__(self, opts):
    """Initializes the test object.

    Args:
      opts: Parsed args for module.
    """
    self.base = None
    self.board = opts.board
    self.archive_dir = opts.archive_dir
    self.crosutils_root = os.path.join(constants.SOURCE_ROOT, 'src', 'scripts')
    self.no_graphics = opts.no_graphics
    self.remote = opts.remote
    self.target = opts.target_image
    self.test_results_root = opts.test_results_root
    self.type = opts.type
    self.whitelist_chrome_crashes = opts.whitelist_chrome_crashes
    self.jobs = opts.jobs

    # An optional ssh private key used for testing.
    self.ssh_private_key = opts.ssh_private_key
    self.ssh_port = opts.ssh_port

  def FindTargetAndBaseImages(self):
    """Initializes the target and base images for CTest."""
    if not self.target:
      # Grab the latest image we've built.
      board_images = os.path.join(constants.SOURCE_ROOT, 'src/build/images',
                                  self.board)
      latest = os.path.join(board_images, 'latest')
      version_dir = os.readlink(latest)
      latest_image_dir = os.path.join(board_images, version_dir)

      self.target = os.path.join(
          latest_image_dir, image_extractor.ImageExtractor.IMAGE_TO_EXTRACT)

    # Grab the latest official build for this board to use as the base image.
    if self.archive_dir:
      target_version = os.path.realpath(self.target).rsplit('/', 2)[-2]
      extractor = image_extractor.ImageExtractor(self.archive_dir)
      latest_image_dir = extractor.GetLatestImage(target_version)
      if latest_image_dir:
        self.base = extractor.UnzipImage(latest_image_dir)

    if not self.base:
      logging.info('Could not find a latest image to use. '
                   'Using target instead.')
      self.base = self.target

  def GenerateUpdatePayloads(self, full):
    """Generates payloads for the test harness.

    Args:
      full: Build payloads for full test suite.
    """
    generator = ('../platform/crostestutils/'
                 'generate_test_payloads/cros_generate_test_payloads.py')

    cmd = [generator]
    cmd.append('--target=%s' % self.target)
    cmd.append('--base=%s' % self.base)
    cmd.append('--board=%s' % self.board)
    cmd.append('--jobs=%d' % self.jobs)

    if full:
      cmd.append('--full_suite')
    else:
      cmd.append('--basic_suite')

    if self.type != 'vm':
      cmd.append('--novm')
    try:
      cros_build_lib.RunCommand(cmd, cwd=self.crosutils_root)
    except cros_build_lib.RunCommandError:
      logging.error('We failed to generate all the update payloads required '
                    'for testing. Please see the logs for more info. We print '
                    'out the log from a failing call to '
                    'cros_generate_update_payload for error handling.')
      sys.exit(1)

  def RunAUTestHarness(self, only_verify, quick_update, suite):
    """Runs the auto update test harness.

    The auto update test harness encapsulates testing the auto-update mechanism
    for the latest image against the latest official image from the channel.
    This also tests images with suite:smoke (built-in as part of its
    verification process).

    Args:
      only_verify: Only verify the target image.
      quick_update: Do a quick update test.
      suite: The suite of tests to run.

    Raises:
      TestException: If the cros_au_test_harness command returns an error code.
    """
    path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    cmd = [os.path.join(path, 'au_test_harness', 'cros_au_test_harness.py'),
           '--base_image=%s' % self.base,
           '--target_image=%s' % self.target,
           '--board=%s' % self.board,
           '--type=%s' % self.type,
           '--remote=%s' % self.remote,
           '--verbose',
           '--jobs=%d' % self.jobs,
          ]

    if self.ssh_private_key is not None:
      cmd.append('--ssh_private_key=%s' % self.ssh_private_key)
    if self.ssh_port is not None:
      cmd.append('--ssh_port=%s' % self.ssh_port)

    if suite:
      cmd.append('--verify_suite_name=%s' % suite)

    if only_verify:
      cmd.append('--test_prefix=SimpleTestVerify')
    elif quick_update:
      cmd.append('--test_prefix=SimpleTestUpdateAndVerify')

    if self.test_results_root:
      cmd.append('--test_results_root=%s' % self.test_results_root)
    if self.no_graphics:
      cmd.append('--no_graphics')
    if self.whitelist_chrome_crashes:
      cmd.append('--whitelist_chrome_crashes')

    # Give tests 10 minutes to clean up before shut down.
    res = cros_build_lib.RunCommand(cmd, cwd=self.crosutils_root,
                                    error_code_ok=True, kill_timeout=10 * 60)
    if res.returncode != 0:
      raise TestException('%s exited with code %d: %s' % (' '.join(res.cmd),
                                                          res.returncode,
                                                          res.error))


def main():
  test_helper.SetupCommonLoggingFormat()
  parser = argparse.ArgumentParser()
  parser.add_argument('-b', '--board',
                      help='board for the image to compare against.')
  parser.add_argument('--archive_dir',
                      help='Directory containing previously archived images.')
  parser.add_argument('--cache', default=False, action='store_true',
                      help='Cache payloads')
  parser.add_argument('--jobs', default=test_helper.CalculateDefaultJobs(),
                      type=int,
                      help='Number of threads to run in parallel.')
  parser.add_argument('--no_graphics', action='store_true', default=False,
                      help='Disable graphics for the vm test.')
  parser.add_argument('--only_verify', action='store_true', default=False,
                      help='Only run basic verification suite.')
  parser.add_argument('--quick_update', action='store_true',
                      help='Run a quick update test. This will run a subset of '
                      'test suite after running autoupdate from target '
                      'image to itself.')
  parser.add_argument('--remote', default='0.0.0.0',
                      help='For real tests, ip address of the target machine.')
  parser.add_argument('--target_image', default=None,
                      help='Target image to test.')
  parser.add_argument('--suite', default=None, help='Test suite to run.')
  parser.add_argument('--test_results_root', default=None,
                      help='Root directory to store test results.  Should '
                      'be defined relative to chroot root.')
  parser.add_argument('--type', default='vm',
                      help='type of test to run: [vm, real, gce]. Default: vm.')
  parser.add_argument('--verbose', default=False, action='store_true',
                      help='Print out added debugging information')
  parser.add_argument('--whitelist_chrome_crashes', default=False,
                      dest='whitelist_chrome_crashes', action='store_true',
                      help='Treat Chrome crashes as non-fatal.')
  parser.add_argument('--ssh_private_key', default=None,
                      help='Path to the private key to use to ssh into the '
                      'image as the root user')
  parser.add_argument('--ssh_port', default=None, type=int,
                      help='ssh port used to ssh into image. (Should only be'
                      ' used with either --quick_update or --only_verify)')

  opts = parser.parse_args()

  if not opts.board:
    parser.error('Need board for image to compare against.')
  if opts.only_verify and opts.quick_update:
    parser.error(
        'Only one of --only_verify or --quick_update should be specified.')
  if opts.ssh_port and not (opts.only_verify or opts.quick_update):
    parser.error(
        'ssh_port should be specified with either --only_verify or '
        '--quick_update')

  # force absolute path for these opts, since a chdir occurs deeper in the
  # codebase.
  for x in ('target_image', 'test_results_root'):
    if x == 'target_image' and opts.type == 'gce':
      # In this case |target_image| is a Google Storage path.
      continue
    val = getattr(opts, x)
    if val is not None:
      setattr(opts, x, os.path.abspath(val))

  ctest = CTest(opts)
  ctest.FindTargetAndBaseImages()
  if not opts.only_verify:
    ctest.GenerateUpdatePayloads(not opts.quick_update)
  try:
    ctest.RunAUTestHarness(opts.only_verify, opts.quick_update,
                           opts.suite)
  except TestException as e:
    if opts.verbose:
      cros_build_lib.Die(str(e))

    sys.exit(1)


if __name__ == '__main__':
  main()
