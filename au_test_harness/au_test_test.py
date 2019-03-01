#!/usr/bin/python2
# -*- coding: utf-8 -*-
# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for au_test."""

from __future__ import print_function

import os
import signal
import sys
import time
import unittest
import mock

from multiprocessing import Process, Value

import constants
sys.path.append(constants.CROS_PLATFORM_ROOT)
sys.path.append(constants.SOURCE_ROOT)

from crostestutils.au_test_harness.au_test import AUTest


class AuTestTest(unittest.TestCase):
  """Test for autest.AUTest."""

  def testSigtermAndSigintHandled(self):
    """Tests that worker.CleanUp is always called."""
    def _ChildProcess(shared_integer):
      class _FakeWorker(object):
        """A fake worker class to use as a mock."""
        def __init__(self, options, test_results_root):
          pass

        def CleanUp(self):
          shared_integer.value = 1

      with mock.patch.object(AUTest, 'SimpleTestVerify', autospec=True,
                             side_effect=lambda _: time.sleep(60)):
        AUTest.worker_class = _FakeWorker
        AUTest.options = None
        AUTest.test_results_root = None
        test_suite = unittest.TestSuite()
        test_suite.addTest(AUTest('SimpleTestVerify'))
        test_runner = unittest.TextTestRunner()
        # This is going to block for 60 seconds.
        test_runner.run(test_suite)

    for signum in (signal.SIGINT, signal.SIGTERM):
      # Start a child process to run VerifyImage.
      shared_integer = Value('i', 0)
      child = Process(target=_ChildProcess, args=(shared_integer,))
      child.start()

      # Wait till it gets into SimpleTestVerify.
      time.sleep(2)
      # Send signal to the child process - test should abort, and if signal is
      # not caught and handled, the child will terminate without calling
      # worker.CleanUp.
      os.kill(child.pid, signum)
      child.join()
      # Assert that worker.CleanUp is called.
      self.assertEqual(1, shared_integer.value)

if __name__ == '__main__':
  suite = unittest.TestSuite()
  suite.addTest(AuTestTest('testSigtermAndSigintHandled'))
  unittest.TextTestRunner().run(suite)
