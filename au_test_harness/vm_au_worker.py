# -*- coding: utf-8 -*-
# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Module containing implementation of an au_worker for virtual machines."""

from __future__ import print_function

import os
import shutil
import subprocess
import tempfile

from chromite.cbuildbot import constants as buildbot_constants
from chromite.lib import constants as chromite_constants
from chromite.lib import cros_build_lib
from chromite.lib import cros_logging as logging
from crostestutils.au_test_harness import au_worker


class VMAUWorker(au_worker.AUWorker):
  """Test harness for updating virtual machines."""

  def __init__(self, options, test_results_root):
    """Processes vm-specific options."""
    super(VMAUWorker, self).__init__(options, test_results_root)
    self.verbose = options.verbose
    self.graphics_flag = '--no-display' if options.no_graphics else ''
    if not self.board:
      cros_build_lib.Die('Need board to convert base image to vm.')
    self.whitelist_chrome_crashes = options.whitelist_chrome_crashes

  def _StopVM(self):
    """Stops an existing VM."""
    cros_build_lib.run(['./cros_vm', '--stop',
                        '--ssh-port=%s' % self._ssh_port],
                       print_cmd=False, check=False,
                       cwd=chromite_constants.CHROMITE_BIN_DIR)

  def CleanUp(self):
    """Stop the vm after a test."""
    self._StopVM()

  def PrepareBase(self, image_path, signed_base=False):
    """Creates an update-able VM based on base image."""
    original_image_path = self.PrepareVMBase(image_path, signed_base)
    # This worker may be running in parallel with other VMAUWorkers, as
    # well as the archive stage of cbuildbot. Make a private copy of
    # the VM image, to avoid any conflict.
    _, private_image_path = tempfile.mkstemp(
        prefix='%s.' % buildbot_constants.VM_DISK_PREFIX)
    shutil.copy(self.vm_image_path, private_image_path)
    self.TestInfo('Copied shared disk image %s to %s.' %
                  (self.vm_image_path, private_image_path))
    self.vm_image_path = private_image_path
    # Although we will run the VM with |private_image_path|, we return
    # |original_image_path|, because our return value is used to find the
    # update files. And the update files are shared across the tests
    # that share the original image.
    return original_image_path

  def _HandleFail(self, log_directory, fail_directory):
    parent_dir = os.path.dirname(fail_directory)
    if not os.path.isdir(parent_dir):
      os.makedirs(parent_dir)

    # Copy logs. Must be done before moving image, as this creates
    # |fail_directory|.
    try:
      shutil.copytree(log_directory, fail_directory)
    except shutil.Error as e:
      logging.warning('Ignoring errors while copying logs: %s', e)

    # Copy VM disk image.
    try:
      self._StopVM()
      shutil.move(self.vm_image_path, fail_directory)
    except shutil.Error as e:
      logging.warning('Ignoring errors while copying VM files: %s', e)

  def VerifyImage(self, unittest, percent_required_to_pass=100, test=''):
    # VMAUWorker disregards |unittest| and |percent_required_to_pass|.
    return self._VerifyImage(test)

  # pylint: disable=W0221
  def _VerifyImage(self, test=''):
    """Runs vm smoke suite or any single test to verify image.

    Returns True upon success.  Prints test output and returns False otherwise.
    """
    log_directory, fail_directory = self.GetNextResultsPath('autotest_tests')
    # image_to_live already verifies lsb-release matching.  This is just
    # for additional steps.
    if not test:
      test = self.verify_suite
    command = ['./cros_run_test',
               '--board=%s' % self.board,
               '--image-path=%s' % self.vm_image_path,
               '--ssh-port=%s' % self._ssh_port,
               '--results-dir=%s' % log_directory,
               '--autotest=%s' % test,
              ]
    if self.graphics_flag:
      command.append(self.graphics_flag)
    if self.whitelist_chrome_crashes:
      command.append('--test_that-args=--whitelist-chrome-crashes')
    if self.ssh_private_key:
      command.append('--private-key=%s' % self.ssh_private_key)

    self.TestInfo('Running %s suite to verify image.' % test)

    result = cros_build_lib.run(
        command, print_cmd=self.verbose, stderr=subprocess.STDOUT,
        cwd=chromite_constants.CHROMITE_BIN_DIR, check=False,
        capture_output=not self.verbose, encoding='utf-8')
    # If the command failed or printed warnings, print the output.
    # TODO(pwang): result.stdout should contain the output of the command even
    # though verbose is set to print to stdout.
    if result.stdout is None:
      out = ''
    else:
      out = result.stdout
    if result.returncode != 0 or '@@@STEP_WARNINGS@@@' in out:
      print(out)
      self._HandleFail(log_directory, fail_directory)

    return result.returncode == 0
