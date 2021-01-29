#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This module runs a suite of Auto Update tests.

  The tests can be run on either a virtual machine or actual device depending
  on parameters given.  Specific tests can be run by invoking --test_prefix.
  Verbose is useful for many of the tests if you want to see individual commands
  being run during the update process.
"""

from __future__ import print_function

import argparse
import functools
import os
import sys
import tempfile
import unittest
import errno

import constants
sys.path.append(constants.CROS_PLATFORM_ROOT)
sys.path.append(constants.SOURCE_ROOT)

# pylint: disable=wrong-import-position
from chromite.lib import cros_build_lib
from chromite.lib import cros_logging as logging
from chromite.lib import parallel
import sudo  # TODO(crbug.com/1170006): Move back to chromite.
from chromite.lib import timeout_util

from crostestutils.au_test_harness import au_test
from crostestutils.lib import test_helper


class _LessBacktracingTestResult(unittest._TextTestResult):
  """TestResult class that suppresses stacks for AssertionError."""
  # pylint: disable=W0212
  def addFailure(self, test, err):
    """Overrides unittest.TestCase.addFailure to suppress stack traces."""
    exc_type = err[0]
    if exc_type is AssertionError:  # There's already plenty of debug output.
      self.failures.append((test, ''))
    else:
      super(_LessBacktracingTestResult, self).addFailure(test, err)


class _LessBacktracingTestRunner(unittest.TextTestRunner):
  """TestRunner class that suppresses stacks for AssertionError.

  This class also prints an error message and exits whenever a test fails,
  and further throws a TimeoutException if a test takes longer than
  MAX_TIMEOUT_SECONDS.
  """
  def _makeResult(self):
    return _LessBacktracingTestResult(self.stream,
                                      self.descriptions,
                                      self.verbosity)

  def run(self, *args, **kwargs):
    """Run the requested test suite.

    If the test suite fails, raise a BackgroundFailure.
    """
    with timeout_util.Timeout(constants.MAX_TIMEOUT_SECONDS):
      test_result = super(_LessBacktracingTestRunner, self).run(*args, **kwargs)
      if test_result is None or not test_result.wasSuccessful():
        msg = 'Test harness failed. See logs for details.'
        raise parallel.BackgroundFailure(msg)


def _PrepareTestSuite(opts):
  """Returns a prepared test suite given by the opts and test class."""
  au_test.AUTest.ProcessOptions(opts)
  test_loader = unittest.TestLoader()
  test_loader.testMethodPrefix = opts.test_prefix
  return test_loader.loadTestsFromTestCase(au_test.AUTest)


def _RunTestsInParallel(opts):
  """Runs the tests given by the opts in parallel."""
  test_suite = _PrepareTestSuite(opts)
  steps = []
  for test in test_suite:
    test_name = test.id()
    test_case = unittest.TestLoader().loadTestsFromName(test_name)
    steps.append(functools.partial(_LessBacktracingTestRunner().run, test_case))

  logging.info('Running tests in test suite in parallel.')
  try:
    parallel.RunParallelSteps(steps, max_parallel=opts.jobs)
  except parallel.BackgroundFailure as ex:
    cros_build_lib.Die(ex)


def CheckOpts(parser, opts):
  """Assert given opts are valid.

  Args:
    parser: Parser used to parse opts.
    opts: Parsed opts.
  """

  def _IsValidImage(image):
    """Asserts that |image_path| is a valid image file for |opts.type|."""
    return (image is not None) and os.path.isfile(image)

  if not _IsValidImage(opts.target_image):
    parser.error('Testing requires a valid target image.\n'
                 'Given: type=%s, target_image=%s.' %
                 (opts.type, opts.target_image))

  if not opts.base_image:
    logging.info('No base image supplied.  Using target as base image.')
    opts.base_image = opts.target_image

  if not _IsValidImage(opts.base_image):
    parser.error('Testing requires a valid base image.\n'
                 'Given: type=%s, base_image=%s.' %
                 (opts.type, opts.base_image))

  if opts.ssh_private_key and not os.path.isfile(opts.ssh_private_key):
    parser.error('Testing requires a valid path to the ssh private key.')

  if opts.ssh_port and opts.ssh_port < 1024:
    parser.error('Testing requires a valid port higher than 1024.')

  if opts.ssh_port and not opts.test_prefix:
    parser.error('Testing with ssh_port requires test_prefix specified.')

  if opts.test_results_root:
    if not 'chroot/tmp' in opts.test_results_root:
      parser.error('Must specify a test results root inside tmp in a chroot.')

    if not os.path.exists(opts.test_results_root):
      os.makedirs(opts.test_results_root)

  else:
    chroot_tmp = os.path.join(constants.SOURCE_ROOT, 'chroot', 'tmp')
    opts.test_results_root = tempfile.mkdtemp(
        prefix='au_test_harness', dir=chroot_tmp)

  # Force absolute path for target_image, since a chdir occurs deeper in the
  # codebase.
  if opts.type != 'gce':
    # In this case target_image is a not a Google Storage path.
    opts.target_image = os.path.abspath(opts.target_image)

  opts.test_results_root = os.path.abspath(opts.test_results_root)

  if not opts.base_image:
    logging.info('Did not pass the base image to use. Using target instead.')
    opts.base_image = opts.target_image


def main():
  test_helper.SetupCommonLoggingFormat()
  parser = argparse.ArgumentParser()
  parser.add_argument('--base_image',
                      help='path to the base image.')
  parser.add_argument('--board', required=True,
                      help='board for the images.')
  parser.add_argument('--no_graphics', action='store_true',
                      help='Disable graphics for the vm test.')
  parser.add_argument('-j', '--jobs',
                      default=test_helper.CalculateDefaultJobs(), type=int,
                      help='Number of simultaneous jobs')
  parser.add_argument('--target_image', required=True,
                      help='path to the target image.')
  parser.add_argument('--test_results_root', default=None,
                      help='Root directory to store test results.  Should '
                      'be defined relative to chroot root.')
  parser.add_argument('--test_prefix', default='test',
                      help='Only runs tests with specific prefix i.e. '
                      'testFullUpdateWipeStateful.')
  parser.add_argument('--type', default='vm', choices=('vm', 'gce'),
                      help='type of test to run: [vm, gce]. Default: vm.')
  parser.add_argument('--verbose', default=True, action='store_true',
                      help='Print out rather than capture output as much as '
                      'possible.')
  parser.add_argument('--allow_chrome_crashes', default=False,
                      dest='allow_chrome_crashes', action='store_true',
                      help='Treat Chrome crashes as non-fatal.')
  parser.add_argument('--verify_suite_name', default=None,
                      help='Specify the verify suite to run.')
  parser.add_argument('--parallel', default=False, dest='parallel',
                      action='store_true',
                      help='Run multiple test stages in parallel (applies only '
                      'to vm tests). Default: False')
  parser.add_argument('--ssh_private_key', default=None,
                      help='Path to the private key to use to ssh into the '
                      'image as the root user.')
  parser.add_argument('--ssh_port', default=None, type=int,
                      help='ssh port used to ssh into image. (Should only be'
                      ' used with --test_prefix)')
  opts = parser.parse_args()

  CheckOpts(parser, opts)

  # Create download folder for payloads for testing.
  download_folder = os.path.join(os.path.realpath(os.path.curdir),
                                 'latest_download')
  try:
    os.makedirs(download_folder)
  except OSError as e:
    if e.errno != errno.EEXIST:
      raise

  with sudo.SudoKeepAlive():
    if opts.parallel:
      _RunTestsInParallel(opts)
    else:
      test_suite = _PrepareTestSuite(opts)
      test_result = unittest.TextTestRunner().run(test_suite)
      if not test_result.wasSuccessful():
        cros_build_lib.Die('Test harness failed.')


if __name__ == '__main__':
  main()
