# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Module that contains the interface for au_test_harness workers.

An au test harnss worker is a class that contains the logic for performing
and validating updates on a target.  This should be subclassed to handle
various types of target.  Types of targets include VM's, real devices, etc.
"""

from __future__ import print_function

import inspect
import os

from chromite.lib import cros_logging as logging


class AUWorker(object):
  """Interface for a worker that updates and verifies images."""

  def __init__(self, options, test_results_root):
    """Processes options for the specific-type of worker."""
    self.board = options.board
    self.test_results_root = test_results_root
    self.all_results_root = os.path.join(test_results_root, 'all')
    self.fail_results_root = os.path.join(test_results_root, 'failed')
    self.use_delta_updates = options.delta
    self.verbose = options.verbose
    self.vm_image_path = None
    self.verify_suite = 'suite:%s' % (options.verify_suite_name or 'smoke')
    self.ssh_private_key = options.ssh_private_key

    # Attributes to be initialized in Initialize.
    self._ssh_port = None
    self._kvm_pid_file = None

    # Initialize test results directory.
    self.test_name = None
    self.all_results_directory = None
    self.fail_results_directory = None
    self.results_count = 0

  def CleanUp(self):
    """Called at the end of every test."""

  def GetUpdateMessage(self, update_target, update_base, from_vm, proxy):
    """Returns the update message that should be printed out for this update."""
    if update_base:
      msg = 'Performing a delta update from %s to %s' % (
          update_base, update_target)
    else:
      msg = 'Performing a full update to %s' % update_target

    if from_vm:
      msg += ' in a VM'
    if proxy:
      msg += ' using a proxy on port ' + str(proxy)
    return msg

  def PrepareBase(self, image_path, signed_base):
    """Method to be called to prepare target for testing this test.

    Subclasses must override this method with the correct procedure for
    preparing the test target.

    Returns the path to the base image (might have changed for vm's).

`   Args:
      image_path: The image that should reside on the target before the test.
      signed_base: If True, use the signed image rather than the actual image.
    """

  def UpdateImage(self, image_path, src_image_path='', stateful_change='old',
                  proxy_port=None):
    """Implementation of an actual update.

    Subclasses must override this method with the correct update procedure for
    the class.
    """

  def VerifyImage(self, unittest, percent_required_to_pass=100, test=''):
    """Verifies the image with tests.

    Verifies that the test images passes the percent required.  Subclasses must
    override this method with the correct update procedure for the class.

    Args:
      unittest: Pointer to a unittest to fail if we cannot verify the image.
      percent_required_to_pass: Percentage required to pass.  This should be
          fall between 0-100.
      test: Test that will be used to verify the image. If omitted or equal to
          the empty string the code will use self.verify_suite.

    Returns:
      Returns the percent that passed.
    """

  def PrepareRealBase(self, image_path, signed_base):
    """Prepares a remote device for worker test by updating it to the image."""
    real_image_path = image_path
    if not signed_base:
      self.UpdateImage(real_image_path)
    else:
      real_image_path = real_image_path + '.signed'
      self.UpdateImage(real_image_path)

    return real_image_path

  def PrepareVMBase(self, image_path, signed_base):
    """Prepares a VM image for worker test."""
    # Tells the VM tests to use the Qemu image as the start point.
    self.vm_image_path = os.path.join(os.path.dirname(image_path),
                                      'chromiumos_qemu_image.bin')
    if signed_base:
      self.vm_image_path = self.vm_image_path + '.signed'

    return self.vm_image_path

  def AssertEnoughTestsPassed(self, unittest, output, percent_required_to_pass):
    """Helper function that asserts a sufficient number of tests passed.

    Args:
      unittest: the unittest object running this test.
      output: stdout from a test run.
      percent_required_to_pass: percentage required to pass.  This should be
          fall between 0-100.

    Returns:
      percent that passed.
    """
    percent_passed = self.ParseGeneratedTestOutput(output)
    self.TestInfo('Percent passed: %d vs. Percent required: %d' % (
        percent_passed, percent_required_to_pass))
    if percent_passed < percent_required_to_pass:
      print(output)
      unittest.fail('%d percent of tests are required to pass' %
                    percent_required_to_pass)

    return percent_passed

  def TestInfo(self, message):
    logging.info('%s: %s', self.test_name, message)

  def Initialize(self, port):
    """Initializes test specific variables for each test.

    Each test needs to specify a unique ssh port.

    Args:
      port: Unique port for ssh access.
    """
    # Initialize port vars.
    self._ssh_port = port
    self._kvm_pid_file = '/tmp/kvm.%d' % self._ssh_port

    # Initialize test results directory.
    self.test_name = inspect.stack()[1][3]
    self.all_results_directory = os.path.join(self.all_results_root,
                                              self.test_name)
    self.fail_results_directory = os.path.join(self.fail_results_root,
                                               self.test_name)
    self.results_count = 0

  def GetNextResultsPath(self, label):
    """Returns a tuple results directories to use for this label.

    Prefixes directory returned for worker with time called i.e. 1_label,
    2_label, etc.  The directory returned is outside the chroot so if passing
    to an script that is called with enther_chroot, make sure to use
    path_util.ToChrootPath(). The first dir returned is the one where results
    should be stored. The second is one where failed test results should be
    stored. Only the former is created as the latter should only be created if
    the test fails.

    Args:
      label: The label used to describe this test phase.

    Returns:
      Returns a path for the results directory to use for this label.
    """
    self.results_count += 1
    results_dir = os.path.join(self.all_results_directory, '%s_%s' % (
        self.results_count, label))
    fail_dir = os.path.join(self.fail_results_directory, '%s_%s' % (
        self.results_count, label))
    if not os.path.exists(results_dir):
      os.makedirs(results_dir)

    return results_dir, fail_dir

  def ParseGeneratedTestOutput(self, output):
    """Returns the percentage of tests that passed based on output.

    Args:
      output: Output string for generate_test_report.py.

    Returns:
      The percentage of tests that passed.
    """
    percent_passed = 0
    lines = output.split('\n')

    for line in lines:
      if line.startswith('Total PASS:'):
        # FORMAT: ^TOTAL PASS: num_passed/num_total (percent%)$
        percent_passed = line.split()[3].strip('()%')
        break

    return int(percent_passed)
