#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This module generates update payloads for testing in parallel.

This module generates update payloads in parallel using the devserver. After
running this module, test payloads are generated and left in the devserver
cache. In addition, this module produces a serialized dictionary stored
with the target image that contains a mapping from the update payload name
to the path it is stored in the devserver cache.  This dictionary can then be
used by other testing scripts i.e. au_test_harness, to locate and use these
payloads for testing in virtual machines.

FOR USE OUTSIDE CHROOT ONLY.
"""

from __future__ import print_function

import hashlib
import optparse
import os
import pickle
import shutil
import sys

import constants
sys.path.append(constants.CROS_PLATFORM_ROOT)
sys.path.append(constants.SOURCE_ROOT)

from chromite.lib import cros_logging as logging
from chromite.lib import dev_server_wrapper
from chromite.lib import locking
from chromite.lib import sudo

from chromite.lib.paygen import paygen_payload_lib
from chromite.lib.paygen import paygen_stateful_payload_lib

from crostestutils.au_test_harness import cros_au_test_harness

from crostestutils.lib import public_key_manager
from crostestutils.lib import test_helper


def _GetFileMd5(path):
  """Calculates the Md5 hash of a file."""
  hash_md5 = hashlib.md5()
  with open(path, "rb") as f:
    for chunk in iter(lambda: f.read(4096 * 10), b""):
      hash_md5.update(chunk)
  return hash_md5.hexdigest()


class UpdatePayload(object):
  """Wrapper around an update payload.

  This class defines an update payload that should be generated.  The only
  required variable to be set is |target|.  If the base image is set to None,
  this defines a full update payload to the target image.

  Variables:
    target: Create payload for this image.
    base: If not None, a delta payload with this image as the source.
    key: If set, signed payload using this private key.
    for_vm: Whether we want the payload for a VM image.
  """
  NAME_SPLITTER = '_'

  def __init__(self, target, base, key=None, for_vm=False):
    self.base = base
    self.target = target
    self.key = key
    self.for_vm = for_vm

    self.payload_dir = None

    self._CalculateUpdateCacheLabel()

  def UpdateId(self):
    """Generates a unique update id the test harness can understand."""
    return dev_server_wrapper.GenerateUpdateId(self.target, self.base,
                                               self.key, self.for_vm)

  def _CalculateUpdateCacheLabel(self):
    """Calculates the label associated with this payload.

    It is exactly what devserver does.
    """
    self.label = ''
    if self.base:
      self.label += _GetFileMd5(self.base) + '_'
    self.label += _GetFileMd5(self.target)
    if self.key:
      self.label += '+' + _GetFileMd5(self.key)

  def __str__(self):
    my_repr = self.target
    if self.base:
      my_repr = self.base + '->' + my_repr

    if self.key:
      my_repr = my_repr + '+' + self.key

    if self.for_vm:
      my_repr = my_repr + '+' + 'for_vm'

    return my_repr

  def __eq__(self, other):
    return str(self) == str(other)

  def __hash__(self):
    return hash(str(self))


class UpdatePayloadGenerator(object):
  """Class responsible for generating update payloads."""

  PATH_TO_CACHE_DIR = os.path.join(
      constants.SOURCE_ROOT, 'chroot/var/lib/devserver/static/cache')

  def __init__(self, options):
    """Initializes a generator object from parsed options.

    Args:
      options: Parsed options from main().
    """
    self.target = options.target
    self.base = options.base
    self.target_signed = None  # Set later when creating the image.

    # For vm tests we use the _qemu name for the images.  Regardless of vm or
    # non vm, these no_vm names are guaranteed to be non-qemu base/target names.
    self.base_no_vm = self.base
    self.target_no_vm = self.target

    # Keys.
    self.public_key = options.public_key
    self.private_key = options.private_key

    # Affect what payloads we create.
    self.board = options.board
    self.basic_suite = options.basic_suite
    self.full_suite = options.full_suite
    self.payloads = set([])

    self.jobs = options.jobs

    self.vm = _ShouldGenerateVM(options)


  def _AddUpdatePayload(self, target, base, key=None, for_vm=False):
    """Adds a new required update payload.  If base is None, a full payload."""
    payload = UpdatePayload(target, base, key, for_vm)

    payload.payload_dir = os.path.join(self.PATH_TO_CACHE_DIR, payload.label)

    self.payloads.add(payload)

  def GenerateImagesForTesting(self):
    # All vm testing requires a VM'ized target.
    if self.vm:
      self.target = test_helper.CreateVMImage(self.target, self.board)

    if self.full_suite:
      if self.public_key:
        self.target_signed = self.target + '.signed'
        if not os.path.exists(self.target_signed):
          logging.info('Creating a signed image for signed payload test.')
          shutil.copy(self.target, self.target_signed)

        public_key_manager.PublicKeyManager(self.target_signed,
                                            self.public_key).AddKeyToImage()

      # The full suite may not have a VM image produced for the test image yet.
      # Ensure this is created.
      self.base = test_helper.CreateVMImage(self.base, self.board)

  def GeneratePayloadRequirements(self):
    """Generate Payload Requirements for AUTestHarness and NPlus1 Testing."""
    if self.full_suite:
      if self.target != self.base:
        # N-1->N. But only add it if the base is different than the target.
        self._AddUpdatePayload(self.target, self.base, for_vm=self.vm)

      # N->N after N-1->N.
      self._AddUpdatePayload(self.target, self.target, for_vm=self.vm)

      # Need a signed payload for the signed payload test.
      if self.target_signed:
        self._AddUpdatePayload(self.target_signed, self.target_signed,
                               self.private_key, for_vm=self.vm)

    if self.basic_suite:
      # Update image to itself from VM base.
      self._AddUpdatePayload(self.target, self.target, for_vm=self.vm)

  def GenerateUpdatePayloads(self):
    """Iterates through payload requirements and generates them.

    This is the main method of this class.  It iterates through payloads
    it needs, generates them, and builds a Cache that can be used by the
    test harness to reference these payloads.

    Returns:
      The cache as a Python dict.
    """

    def GenerateUpdatePayload(payload):
      """Generates an update payload and writes it into payload file.

      Args:
        payload: An object of UpdatePayload that defines the parameters of the
                 payload.
      """
      payload_file = os.path.join(payload.payload_dir, 'update.gz')

      logging.info('Generating a%s %s payload %s to %s %s',
                   ' signed' if payload.key else 'n unsigned',
                   'delta' if payload.base else 'full',
                   ('from %s' % payload.base) if payload.base else '',
                   payload.target,
                   'and not patching the kernel.' if payload.for_vm else '')

      paygen_payload_lib.GenerateUpdatePayload(payload.target, payload_file,
                                               src_image=payload.base,
                                               private_key=payload.key)

      # Generating the stateful update as devserver would've done.
      paygen_stateful_payload_lib.GenerateStatefulPayload(payload.target,
                                                          payload.payload_dir)

    for p in self.payloads:
      GenerateUpdatePayload(p)

    # Build the dictionary from our id's and returned cache paths.
    return {p.UpdateId(): os.path.join('update', 'cache', p.label)
            for p in self.payloads}

  def DumpCacheToDisk(self, cache):
    """Dumps the cache to the same folder as the images."""
    if not self.basic_suite and not self.full_suite:
      logging.info('Not dumping payload cache to disk as payloads for the '
                   'test harness were not requested.')
    else:
      cache_file = os.path.join(os.path.dirname(self.target),
                                cros_au_test_harness.CACHE_FILE)

      logging.info('Dumping %s', cache_file)
      with open(cache_file, 'w') as file_handle:
        pickle.dump(cache, file_handle)


def _ShouldGenerateVM(options):
  """Returns true if we will need a VM version of our images."""
  # This is a combination of options.vm and whether or not we are generating
  # payloads for vm testing.
  return options.vm and (options.basic_suite or options.full_suite)


def CheckOptions(parser, options):
  """Checks that given options are valid.

  Args:
    parser: Parser used to parse options.
    options: Parse options from OptionParser.
  """
  if not options.target or not os.path.isfile(options.target):
    parser.error('Target image must exist.')

  if not options.base:
    logging.info('Using target image as base image.')
    options.base = options.target

  if not os.path.isfile(options.base):
    parser.error('Base image must exist.')

  if options.private_key:
    if not os.path.isfile(options.private_key):
      parser.error('Private key must exist.')

    if not os.path.isfile(options.public_key):
      parser.error('Public key must exist.')

  if _ShouldGenerateVM(options):
    if not options.board:
      parser.error('Board must be set to generate update '
                   'payloads for vm.')


def main():
  test_helper.SetupCommonLoggingFormat()
  parser = optparse.OptionParser()

  # Options related to which payloads to generate.
  parser.add_option('--basic_suite', default=False, action='store_true',
                    help='Prepare to run the basic au test suite.')
  parser.add_option('--full_suite', default=False, action='store_true',
                    help='Prepare to run the full au test suite.')

  # Options related to how to generate test payloads for the test harness.
  parser.add_option('--novm', default=True, action='store_false', dest='vm',
                    help='Test Harness payloads will not be tested in a VM.')
  parser.add_option('--private_key',
                    help='Private key to sign payloads for test harness.')
  parser.add_option('--public_key',
                    help='Public key to verify payloads for test harness.')

  # Options related to the images to test.
  parser.add_option('--board', help='Board used for the images.')
  parser.add_option('--base', help='Image we want to test updates from.')
  parser.add_option('--target', help='Image we want to test updates to.')

  # Miscellaneous options.
  parser.add_option('--jobs', default=test_helper.CalculateDefaultJobs(),
                    type=int,
                    help='Number of payloads to generate in parallel.')

  options = parser.parse_args()[0]
  CheckOptions(parser, options)

  # Don't allow this code to be run more than once at a time.
  lock_path = os.path.join(os.path.dirname(__file__), '.lock_file')
  with locking.FileLock(lock_path, 'generate payloads lock') as lock:
    lock.write_lock()
    with sudo.SudoKeepAlive():
      generator = UpdatePayloadGenerator(options)
      generator.GenerateImagesForTesting()
      generator.GeneratePayloadRequirements()
      cache = generator.GenerateUpdatePayloads()
      generator.DumpCacheToDisk(cache)


if __name__ == '__main__':
  main()
