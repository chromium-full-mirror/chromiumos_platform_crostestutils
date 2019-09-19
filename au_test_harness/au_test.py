# -*- coding: utf-8 -*-
# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Module containing a test suite that is run to test auto updates."""

from __future__ import print_function

import os
import signal
import sys
import unittest

from functools import partial

from chromite.lib import cros_logging as logging
from chromite.lib import signals
from crostestutils.au_test_harness import gce_au_worker
from crostestutils.au_test_harness import vm_au_worker


class AUTest(unittest.TestCase):
  """Test harness that uses an au_worker to perform and validate updates.

  Defines a test suite that is run using an au_worker.  An au_worker can
  be created to perform and validates updates on both virtual and real devices.
  See documentation for au_worker for more information.
  """

  def __init__(self, *_args, **_kwargs):
    super(AUTest, self).__init__(*_args, **_kwargs)

    # Original signal handlers.
    self._old_sigint = None
    self._old_sigterm = None

    # Verify that the signals modules is actually usable, and won't segfault
    # upon invocation of getsignal. See signals.SignalModuleUsable for the
    # details and upstream python bug.
    self._use_signals = signals.SignalModuleUsable()

  @classmethod
  def ProcessOptions(cls, options):
    """Processes options for the test suite and sets up the worker class.

    Args:
      options: options class to be parsed from main class.
    """
    cls.base_image_path = options.base_image
    cls.target_image_path = options.target_image
    cls.test_results_root = options.test_results_root
    if options.type == 'vm':
      cls.worker_class = vm_au_worker.VMAUWorker
    elif  options.type == 'gce':
      cls.worker_class = gce_au_worker.GCEAUWorker
    else:
      raise ValueError('Invalid au_worker type: %s' % options.type)

    # Cache away options to instantiate workers later.
    cls.options = options

  # --- UNITTEST SPECIFIC METHODS ---
  def setUp(self):
    """Overrides unittest.TestCase.setUp and called before every test.

    Sets instance specific variables and initializes worker.
    """
    super(AUTest, self).setUp()
    # Install custom signal handlers that call worker.CleanUp on the receipt of
    # SIGINT and SIGTERM. This is particularly useful in cases where the worker
    # allocates resources in prepare stage, but is taking too long at test stage
    # and the caller decides to terminate it (by sending a SIGTERM). The default
    # action of SIGTERM is terminate, which leaves expensive resources leaked
    # and/or local environment tainted.
    if self._use_signals:
      self._InstallHandlers()
    self.worker = self.worker_class(self.options, AUTest.test_results_root)
    self.download_folder = os.path.join(os.path.realpath(os.path.curdir),
                                        'latest_download')

  def tearDown(self):
    """Overrides unittest.TestCase.tearDown and called after every test."""
    self.worker.CleanUp()
    # Restore signal handlers.
    if self._use_signals:
      self._RestoreHandlers()

  def SimpleTestVerify(self):
    """Test that only verifies the target image.

    We explicitly don't use test prefix so that isn't run by default.  Can be
    run using test_prefix option.
    """
    self.worker.Initialize(self.options.ssh_port or 9228)
    self.worker.PrepareBase(self.target_image_path)
    self.assertTrue(self.worker.VerifyImage(self))

  # --- PRIVATE HELPER FUNCTIONS ---
  def _InstallHandlers(self):
    """Installs signal handlers for SIGINT and SIGTERM."""
    self._old_sigint = signal.getsignal(signal.SIGINT)
    self._old_sigterm = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGINT, partial(self._SigintAndSigtermHandler,
                                         self._old_sigint))
    signal.signal(signal.SIGTERM, partial(self._SigintAndSigtermHandler,
                                          self._old_sigterm))

  def _RestoreHandlers(self):
    """Restores signal handlers for SIGINT and SIGTERM."""
    signal.signal(signal.SIGINT, self._old_sigint)
    signal.signal(signal.SIGTERM, self._old_sigterm)

  def _SigintAndSigtermHandler(self, original_handler, signum, frame):
    """Common signal handler for SIGINT and SIGTERM.

    It tries to clean up allocated resources, and relays the signal to the
    original handler.

    Args:
      original_handler: The original signal handler.
      signum: The number of the signal to handle.
      frame: Current stack frame. See signal.signal for details on |signum| and
          |frame|.
    """
    logging.warning('Received signal %d', signum)
    if signum:
      # If we've been invoked because of a signal, ignore delivery of that
      # signal from this point forward. The invoking context of this method
      # restores signal delivery to what it was prior; we suppress future
      # delivery till then since this code handles SIGINT/SIGTERM fully
      # including delivering the signal to the original handler on the way out.
      #
      # Mask both SIGINT and SIGTERM so that the cleanup won't be interrupted.
      # They will be turned back on once cleanup finishes.
      signal.signal(signal.SIGINT, signal.SIG_IGN)
      signal.signal(signal.SIGTERM, signal.SIG_IGN)
    self.worker.CleanUp()
    if not signals.RelaySignal(original_handler, signum, frame):
      logging.warning('Failed to relay signal %d to original handler.', signum)
      sys.exit('Received signal %d.' % signum)
