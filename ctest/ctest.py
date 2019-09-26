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

# pylint: disable=wrong-import-position
from chromite.lib import cros_build_lib
from chromite.lib import cros_logging as logging

from crostestutils.lib import test_helper


class TestException(Exception):
  """Thrown by RunTestHarness if there's a test failure."""


class CTest(object):
  """Main class with methods to generate payloads and test them.

  Variables:
    base: Base image to test from.
    board: the board for the latest image.
    crosutils_root: Location of crosutils.
    no_graphics: boolean: If True, disable graphics during vm test.
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
    self.crosutils_root = os.path.join(constants.SOURCE_ROOT, 'src', 'scripts')
    self.no_graphics = opts.no_graphics
    self.target = opts.target_image
    self.test_results_root = opts.test_results_root
    self.type = opts.type
    self.whitelist_chrome_crashes = opts.whitelist_chrome_crashes

    # An optional ssh private key used for testing.
    self.ssh_private_key = opts.ssh_private_key
    self.ssh_port = opts.ssh_port

  def RunTestHarness(self, only_verify, suite):
    """Runs the test harness (suite:smoke).

    This tests images with suite:smoke (built-in as part of its verification
    process).

    Args:
      only_verify: Only verify the target image.
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
           '--verbose',
          ]

    if self.ssh_private_key is not None:
      cmd.append('--ssh_private_key=%s' % self.ssh_private_key)
    if self.ssh_port is not None:
      cmd.append('--ssh_port=%s' % self.ssh_port)

    if suite:
      cmd.append('--verify_suite_name=%s' % suite)

    if only_verify:
      cmd.append('--test_prefix=SimpleTestVerify')

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
  parser.add_argument('--no_graphics', action='store_true', default=False,
                      help='Disable graphics for the vm test.')
  parser.add_argument('--only_verify', action='store_true', default=False,
                      help='Only run basic verification suite.')
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
                      ' used with --only_verify)')

  opts = parser.parse_args()

  if opts.ssh_port and not opts.only_verify:
    parser.error('ssh_port should be specified with either --only_verify')

  ctest = CTest(opts)
  try:
    ctest.RunTestHarness(opts.only_verify, opts.suite)
  except TestException as e:
    if opts.verbose:
      cros_build_lib.Die(str(e))

    sys.exit(1)


if __name__ == '__main__':
  main()
