#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (c) 2013 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Integration test to test the basic functionality of dev-install.

This module contains a test that runs some sanity integration tests against
a VM. First it starts a VM test image and turns it into a base image by wiping
all of the stateful partition. Once done, runs dev_install to restore the
stateful partition.
"""

from __future__ import print_function

import argparse
import os
import shutil
import sys
import tempfile

import constants
sys.path.append(constants.SOURCE_ROOT)
sys.path.append(constants.CROS_PLATFORM_ROOT)

from chromite.lib import constants as chromite_constants
from chromite.lib import cros_build_lib
from chromite.lib import cros_logging as logging
from chromite.lib import dev_server_wrapper
from chromite.lib import osutils
from chromite.lib import remote_access
from chromite.lib import vm

from crostestutils.lib import mount_helper
from crostestutils.lib import test_helper


class TestError(Exception):
  """Raised on any error during testing. It being raised is a test failure."""


class DevModeTest(object):
  """Wrapper for dev mode tests."""

  # qemu hardcodes 10.0.2.2 as the host from the guest's point of view
  # https://wiki.qemu.org/Documentation/Networking#User_Networking_.28SLIRP.29
  # When the host's eth0 IP address is also 10.0.2.*, and the guest tries to
  # access it, the requests will be handled by qemu and never be seen by the
  # host. Instead, let the guest always connect to 10.0.2.2.
  HOST_IP_ADDRESS = '10.0.2.2'

  def __init__(self, image_path, board, binhost):
    """Initializes DevModeTest.

    Args:
      image_path: Filesystem path to the image to test.
      board: Board of the image under test.
      binhost: Binhost override. Binhost as defined here is where dev-install
               go to search for binary packages. By default this will
               be set to the devserver url of the host running this script.
               If no override i.e. the default is ok, set to None.
    """
    self.image_path = image_path
    self.board = board
    self.binhost = binhost
    self.tmpdir = tempfile.mkdtemp('DevModeTest')
    self.working_image_path = None
    self.devserver = None
    self.device = None
    self.port = None

  def Cleanup(self):
    """Cleans up any state at the end of the test."""
    try:
      if self.devserver:
        self.devserver.Stop()
      self.devserver = None
      if self.device:
        self.device.Cleanup()
      self.device = None
      if self.port:
        cros_build_lib.RunCommand(['./cros_vm', '--stop',
                                   '--ssh-port=%d' % self.port],
                                  cwd=chromite_constants.CHROMITE_BIN_DIR,
                                  error_code_ok=True)
      self.port = None
      osutils.RmDir(self.tmpdir, ignore_missing=True)
      self.tmpdir = None
    except Exception:
      logging.exception('Received error during cleanup')

  def _WipeDevInstall(self):
    """Wipes the devinstall state."""
    logging.info('Wiping /usr/local/bin from the image.')
    r_mount_point = os.path.join(self.tmpdir, 'm')
    s_mount_point = os.path.join(self.tmpdir, 's')
    dev_image_path = os.path.join(s_mount_point, 'dev_image')
    mount_helper.MountImage(self.working_image_path,
                            r_mount_point, s_mount_point, read_only=False,
                            safe=True)
    try:
      osutils.RmDir(dev_image_path, sudo=True)
    finally:
      mount_helper.UnmountImage(r_mount_point, s_mount_point)

  def PrepareTest(self):
    """Pre-test modification to the image and env to setup test."""
    logging.info('Setting up the image %s for vm testing.', self.image_path)
    vm_path = vm.CreateVMImage(image=self.image_path, board=self.board,
                               updatable=False)

    logging.info('Making copy of the vm image %s to manipulate.', vm_path)
    self.working_image_path = os.path.join(self.tmpdir,
                                           os.path.basename(vm_path))
    shutil.copyfile(vm_path, self.working_image_path)
    logging.debug('Copy of vm image stored at %s.', self.working_image_path)

    self._WipeDevInstall()

    self.port = remote_access.GetUnusedPort()
    logging.info('Starting the vm on port %d.', self.port)
    vm_cmd = ['./cros_vm', '--ssh-port=%d' % self.port,
              '--image-path=%s' % self.working_image_path, '--start']
    cros_build_lib.RunCommand(vm_cmd, cwd=chromite_constants.CHROMITE_BIN_DIR)

    self.device = remote_access.ChromiumOSDevice(
        remote_access.LOCALHOST, port=self.port, base_dir=self.tmpdir)
    if not self.device.MountRootfsReadWrite():
      raise TestError('Failed to make rootfs writeable')

    if not self.binhost:
      logging.info('Starting the devserver.')
      self.devserver = dev_server_wrapper.DevServerWrapper()
      self.devserver.Start()
      self.binhost = self.devserver.GetDevServerURL(
          ip=self.HOST_IP_ADDRESS, port=self.devserver.port,
          sub_dir='static/pkgroot/%s/packages' % self.board)

    logging.info('Using binhost %s', self.binhost)

  def TestDevInstall(self):
    """Tests that we can run dev-install and have python work afterwards."""
    try:
      logging.info('Running dev install in the vm.')
      self.device.RunCommand(
          ['bash', '-l', '-c',
           '"/usr/bin/dev_install --yes --binhost=%s"' % self.binhost])

      logging.info('Verifying that python works on the image.')
      # crbug.com/955147: /usr/local/bin/python symlink doesn't exist.
      # Use python-wrapper instead.
      self.device.RunCommand(['sudo', '-u', 'chronos', '--', 'python-wrapper',
                              '-c', '"print(\'hello world\')"'])
    except (cros_build_lib.RunCommandError,
            remote_access.SSHConnectionError) as e:
      self.devserver.PrintLog()
      logging.error('dev-install test failed. See devserver log above for more '
                    'details.')
      raise TestError('dev-install test failed with: %s' % str(e))

  def Run(self):
    try:
      self.PrepareTest()
      self.TestDevInstall()
      logging.info('All tests passed.')
    finally:
      self.Cleanup()


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--binhost', metavar='URL',
                      help='binhost override. By default, starts up a devserver'
                      ' and uses it as the binhost.')
  parser.add_argument('board', nargs=1, help='board to use.')
  parser.add_argument('image_path', nargs=1, help='path to test|vm image.')
  parser.add_argument('-v', '--verbose', default=False, action='store_true',
                      help='Print out added debugging information')
  options = parser.parse_args()

  test_helper.SetupCommonLoggingFormat(verbose=options.verbose)
  DevModeTest(os.path.realpath(options.image_path[0]), options.board[0],
              options.binhost).Run()

if __name__ == '__main__':
  main()
