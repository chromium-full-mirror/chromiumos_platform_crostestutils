#!/usr/bin/env python2
#
# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for gce_au_worker."""

from __future__ import print_function

import mock
import os
import sys
import unittest

import constants
sys.path.append(constants.CROS_PLATFORM_ROOT)
sys.path.append(constants.SOURCE_ROOT)

from chromite.lib.gce import GceContext
from chromite.lib import cros_build_lib
from chromite.lib import cros_test_lib
from chromite.lib import osutils
from chromite.lib import path_util
from crostestutils.au_test_harness.au_worker import AUWorker
from crostestutils.au_test_harness.gce_au_worker import GCEAUWorker


class Options(object):
  """A fake class to hold command line options."""

  def __init__(self):
    self.board = 'lakitu'
    self.delta = False
    self.verbose = False
    self.quick_test = False
    self.verify_suite_name = 'gce-smoke'


class GceAuWorkerTest(cros_test_lib.MockTempDirTestCase):
  """Test suite for GCEAUWorker."""

  NETWORK = 'default'
  MACHINE_TYPE = 'f1-micro'

  def setUp(self):
    # Fake out environment.
    self.options = Options()
    self.options.ssh_private_key = './ssh_key'

    self.json_key_file = os.path.join(self.tempdir, 'service_account.json')
    osutils.Touch(self.json_key_file)

    self.image_path = './gce_tar_ball.tar.gz'

    # Mock out model or class level methods.
    self.PatchObject(AUWorker, 'GetNextResultsPath', autospec=True,
                     return_value=('./log', './fail'))
    self.PatchObject(GceContext, 'ForServiceAccountThreadSafe',
                     spec=GceContext.ForServiceAccountThreadSafe)

  def testCreateInstance(self):
    """Verifies _CreateInstance creates an instance with |image_path|.

    Also, verifies that correct instance properties are applied.
    """
    worker = GCEAUWorker(self.options, './log', network=self.NETWORK,
                         machine_type=self.MACHINE_TYPE,
                         json_key_file=self.json_key_file)
    self.PatchObject(worker.gscontext, 'CopyInto', autospec=True)
    self.PatchObject(worker.gce_context, 'CreateImage', autospec=True)
    self.PatchObject(worker.gce_context, 'CreateAddress', autospec=True)
    self.PatchObject(worker.gce_context, 'CreateInstance', autospec=True)

    worker._CreateInstance(self.image_path)  # pylint: disable=protected-access

    worker.gscontext.CopyInto.assert_called_once_with(self.image_path, mock.ANY)
    self.assertEqual(1, worker.gce_context.CreateImage.call_count)
    self.assertEqual(1, worker.gce_context.CreateAddress.call_count)
    worker.gce_context.CreateInstance.assert_called_once_with(
        mock.ANY, mock.ANY, machine_type=self.MACHINE_TYPE,
        network=self.NETWORK, static_address=mock.ANY, serviceAccounts=mock.ANY)

  def testUpdateImage(self):
    """Verifies UpdateImage always creates a new instance."""
    worker = GCEAUWorker(self.options, './log',
                         json_key_file=self.json_key_file)

    self.PatchObject(worker, '_CreateInstance', autospec=True)

    worker.UpdateImage(self.image_path)
    worker.UpdateImage(self.image_path)

    # pylint: disable=protected-access
    self.assertEqual(2, worker._CreateInstance.call_count)
    # pylint: enable=protected-access

  def CheckVerifyImage(self, worker, passed_in_test, expected_test_ran):
    """Helper function that checks correct test is run by VerifyImage."""

    def _MockRunCommand(cmd, *_args, **_kwargs):
      """A mock cros_build_lib.RunCommand that verifies passed-in arguments."""
      self.assertIn('test_that', cmd)
      self.assertIn(expected_test_ran, cmd)
      return cros_build_lib.CommandResult()

    self.PatchObject(path_util, 'ToChrootPath', autospec=True)
    self.PatchObject(cros_build_lib, 'RunCommand', side_effect=_MockRunCommand,
                     autospec=True)
    self.PatchObject(AUWorker, 'ParseGeneratedTestOutput', autospec=True,
                     return_value=100)

    worker.VerifyImage(None, test=passed_in_test)
    # Ensure that the checks in _MockRunCommand did take place.
    self.assertEqual(1, cros_build_lib.RunCommand.call_count)

  def testVerifyImage(self):
    """Verifies that VerifyImage runs the correct test.

    Specifically, if no test is specified, worker.verify_suite should be ran.
    """
    worker = GCEAUWorker(self.options, './log',
                         json_key_file=self.json_key_file)
    self.CheckVerifyImage(worker, passed_in_test='suite:foo',
                          expected_test_ran='suite:foo')
    self.CheckVerifyImage(worker, passed_in_test='',
                          expected_test_ran=worker.verify_suite)

  def testVerifyImageFails(self):
    """Verifies VerifyImage calls _HandleFail when test fails."""
    worker = GCEAUWorker(self.options, './log',
                         json_key_file=self.json_key_file)
    self.PatchObject(path_util, 'ToChrootPath', autospec=True)
    self.PatchObject(cros_build_lib, 'RunCommand', autospec=True)
    self.PatchObject(worker, '_HandleFail', autospec=True)
    self.PatchObject(worker, '_GetTestReport', autospec=True,
                     return_value='report')
    # Returning 0 means the none the tests passed.
    self.PatchObject(AUWorker, 'ParseGeneratedTestOutput', autospec=True,
                     return_value=0)
    worker.VerifyImage(None)
    # pylint: disable=protected-access
    self.assertEqual(1, worker._HandleFail.call_count)
    # pylint: enable=protected-access

  def testCleanUp(self):
    """Tests that CleanUp deletes all GCS/GCE resources."""
    worker = GCEAUWorker(self.options, 'foo',# self.test_results_root,
                         json_key_file=self.json_key_file)
    worker.image = 'fake-image'
    worker.instance = 'fake-instance'
    worker.address_name = 'fake-address'
    worker.tarball_remote = 'gs://fake-tarball'

    for cmd in ['DeleteImage', 'DeleteInstance', 'DeleteAddress']:
      self.PatchObject(worker.gce_context, cmd, autospec=True)
    self.PatchObject(worker.gscontext, 'DoCommand', autospec=True)

    worker.CleanUp()

    # Assert that existing resources are cleaned up.
    worker.gce_context.DeleteInstance.assert_called_once_with('fake-instance')
    worker.gce_context.DeleteAddress.assert_called_once_with('fake-address')
    worker.gce_context.DeleteImage.assert_called_once_with('fake-image')
    worker.gscontext.DoCommand.assert_called_once_with(['rm',
                                                        'gs://fake-tarball'])


if __name__ == '__main__':
  unittest.main()
