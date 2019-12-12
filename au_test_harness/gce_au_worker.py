# -*- coding: utf-8 -*-
# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Module containing a class that implements an au_worker for GCE instances."""

from __future__ import print_function

import datetime
import os
import random
import shutil
import tempfile
import time
import urllib2

from multiprocessing import Process

from chromite.lib import cros_build_lib
from chromite.lib import cros_logging as logging
from chromite.lib import gce
from chromite.lib import gs
from chromite.lib import path_util
from crostestutils.au_test_harness import au_worker
from crostestutils.au_test_harness import constants

# Information of the GCE project and default instance properties.
GCE_PROJECT = 'cros-autotest-bots'
GCE_ALL_ZONES = (
    'us-central1-a',
    'us-central1-b',
    'us-central1-c',
    'us-central1-f',
)
GCE_DEFAULT_ZONE = 'us-central1-a'
GCE_DEFAULT_NETWORK = 'network-vpc'
GCE_DEFAULT_SUBNET = 'subnet-us-central-192'
GCE_DEFAULT_MACHINE_TYPE = 'n1-standard-8'
GCE_JSON_KEY = '/creds/service_accounts/service-account-cros-autotest-bots.json'
GCS_BUCKET = 'chromeos-test-gce-tarballs'
DEFAULT_INSTANCE_SCOPES = (
    'https://www.googleapis.com/auth/cloud.useraccounts.readonly',
    'https://www.googleapis.com/auth/devstorage.read_only',
    'https://www.googleapis.com/auth/logging.write',
    'https://www.googleapis.com/auth/cloudimagemanagement',
)
# Number of times to try until a GCE instance is created successfully.
CREATE_INSTANCE_ATTEMPTS = 3


class GCEAUWorker(au_worker.AUWorker):
  """Test harness for updating GCE instances.

  Attributes:
    gce_context: An utility for GCE operations.
    gscontext: An utility for GCS operations.
    network: Default network to create instances in.
    machine_type: Default machine type to create instances with.
    gcs_bucket: The GCS bucket to upload image tarballs to.
    instance_scopes: Scopes for the "default" service account on the instance.
    tarball_local: Local path to the tarball of test image.
    tarball_remote: GCS path to the tarball of test image.
    image: A single GCE image associated with a worker.
    image_link: The URL to the image created.
    instance: GCE VM instance associated with a worker.
    address_name: Name of the static IP address reserved for |instance|.
    address: IP address of |address_name|.
    internal_ip: Internal IP address of |instance|.
  """
  _GS_PATH_COMMON_PREFIX = 'gs://'
  _GS_URL_COMMON_PREFIX = 'https://storage.googleapis.com/'
  _IMAGE_PREFIX = 'test-'
  _INSTANCE_PREFIX = 'test-'
  _TEST_REPORT_FILENAME = 'test_report.log'

  def __init__(self, options, test_results_root,
               project=GCE_PROJECT,
               zone=GCE_DEFAULT_ZONE,
               network=GCE_DEFAULT_NETWORK,
               machine_type=GCE_DEFAULT_MACHINE_TYPE,
               json_key_file=GCE_JSON_KEY,
               gcs_bucket=GCS_BUCKET,
               instance_scopes=DEFAULT_INSTANCE_SCOPES):
    """Processes GCE-specific options."""
    super(GCEAUWorker, self).__init__(options, test_results_root)
    self.gce_context = gce.GceContext.ForServiceAccountThreadSafe(
        project, zone, json_key_file=json_key_file)
    self.json_key_file = json_key_file
    self.gscontext = gs.GSContext()
    self.network = network
    self.machine_type = machine_type
    self.gcs_bucket = gcs_bucket
    self.instance_scopes = instance_scopes
    self.tarball_local = None
    self.tarball_remote = None
    self.image = None
    self.image_link = None
    self.instance = None
    self.address = None
    self.address_name = None
    self.internal_ip = None

    # Background processes that delete throw-away instances.
    self._bg_delete_processes = []

    # In indicator of whether or not the worker is run from a GCE builder. Some
    # of the logic in this module needs to be compatible with non-GCE builders.
    self._on_gce = _OnGCE()


  def CleanUp(self):
    """Deletes throw-away instances and images."""
    logging.info('Waiting for GCP resources to be deleted.')
    self._WaitForBackgroundDeleteProcesses()
    self._DeleteExistingResources()
    logging.info('All resources are deleted.')

  def PrepareBase(self, image_path, signed_base=False):
    """Auto-update to base image to prepare for test."""
    return self.PrepareRealBase(image_path, signed_base)

  def UpdateImage(self, image_path, src_image_path='', stateful_change='old',
                  proxy_port=None):
    """Updates the image on the GCE instance.

    Unlike vm_au_worker, UpdateImage always creates a new image and a new
    instance.
    """
    # Delete existing resources in the background if any.
    bg_delete = Process(target=self._DeleteExistingResources)
    bg_delete.start()
    self._bg_delete_processes.append(bg_delete)

    log_directory, fail_directory = self.GetNextResultsPath('update')
    try:
      self._CreateInstance(image_path)
    except:
      self._HandleFail(log_directory, fail_directory)
      raise

  def VerifyImage(self, unittest, percent_required_to_pass=100, test=''):
    if not test:
      test = self.verify_suite

    log_directory, fail_directory = self.GetNextResultsPath('autotest_tests')
    (_, _, log_directory_in_chroot) = log_directory.rpartition('chroot')

    # Copy GCE key file in a temporary file inside the chroot and
    # make sure to remove it before return.
    with tempfile.NamedTemporaryFile(
        dir=path_util.FromChrootPath('/tmp')) as gce_key_copy:
      shutil.copy(self.json_key_file, gce_key_copy.name)

      args = 'gce_project=%s gce_zone=%s gce_instance=%s gce_key_file=%s' % (
          self.gce_context.project, self.gce_context.zone, self.instance,
          path_util.ToChrootPath(gce_key_copy.name))

      dut_ip = self.internal_ip if self._on_gce else self.address
      cmd = ['test_that', '-b', self.board, '--no-quickmerge',
             '--results_dir=%s' % log_directory_in_chroot, dut_ip, test,
             '--args=%s' % args]

      if self.ssh_private_key is not None:
        cmd.append('--ssh_private_key=%s' %
                   path_util.ToChrootPath(self.ssh_private_key))

      logging.info('Running test %s to verify image.', test)
      result = cros_build_lib.run(cmd, check=False, enter_chroot=True,
                                  encoding='utf-8', stdout=True,
                                  cwd=constants.CROSUTILS_DIR)
      percent_passed = self.ParseGeneratedTestOutput(result.stdout)
      passed = percent_passed >= percent_required_to_pass
      if not passed:
        self._HandleFail(log_directory, fail_directory)
        test_report = self._GetTestReport(log_directory)
        print(test_report)
        if unittest is not None:
          unittest.fail('Not all tests passed.')
      return passed

  # --- PRIVATE HELPER FUNCTIONS ---
  def _GetTestReport(self, results_path):
    """Returns the content of test_report.log created by test_that.

    Args:
      results_path: Path to the directory where results are saved.

    Returns:
      Content of test_report.log, or None if report is not found.
    """
    report_path = os.path.join(results_path, self._TEST_REPORT_FILENAME)
    if os.path.isfile(report_path):
      with open(report_path) as f:
        return f.read()
    logging.warning('Test log not found in %s', results_path)
    return None

  def _CreateInstance(self, image_path):
    """Uploads the gce tarball and creates an instance with it."""
    ts = datetime.datetime.fromtimestamp(time.time()).strftime(
        '%Y-%m-%d-%H-%M-%S')

    # Upload the GCE tarball to Google Cloud Storage.
    self.tarball_local = image_path
    gs_directory = ('gs://%s/%s' % (self.gcs_bucket, ts))
    self.tarball_remote = '%s/%s' % (gs_directory,
                                     os.path.basename(self.tarball_local))
    self.gscontext.CopyInto(self.tarball_local, gs_directory)

    # Create an image from |image_path|.
    self.image = self._IMAGE_PREFIX + ts
    self.image_link = self.gce_context.CreateImage(
        self.image, self._GsPathToUrl(self.tarball_remote))

    self.instance = self._INSTANCE_PREFIX + ts

    if not self._on_gce:
      # Have to use a static external IP address if not on GCE.
      self.address_name = self.instance
      self.address = self.gce_context.CreateAddress(self.address_name)

    # Create an instance.
    service_accounts = [
        {
            'email': 'default',
            'scopes': self.instance_scopes,
        },
    ]

    # Though rare, the create instance operation may fail due to zonal outages.
    # Retry a couple of times for redundancy.
    for i, zone in enumerate(random.sample(GCE_ALL_ZONES,
                                           CREATE_INSTANCE_ATTEMPTS)):
      try:
        self.gce_context.zone = zone
        self.gce_context.CreateInstance(
            name=self.instance,
            image=self.image_link,
            machine_type=self.machine_type,
            network=GCE_DEFAULT_NETWORK,
            subnet=GCE_DEFAULT_SUBNET,
            serviceAccounts=service_accounts,
            static_address=None if self._on_gce else self.address)

      except gce.Error as e:
        logging.error('Failed to create instance [attempt %d/%d]: %r', i + 1,
                      CREATE_INSTANCE_ATTEMPTS, e)
      else:
        break

    # Get the internal IP of the instance.
    self.internal_ip = self.gce_context.GetInstanceInternalIP(self.instance)

  def _DeleteExistingResources(self):
    """Deletes all allocated GCP resources."""
    # There are cases where resources are created at the backend but the
    # resource creation calls fail, for example due to network errors that
    # happen when the response is being delivered. So we always make sure to
    # delete all allocated resources (images, instances, addresses) regardless
    # of whether the corresponding Create operation succeeded.

    # Delete the GCE instance.
    if self.instance:
      self.gce_context.DeleteInstance(self.instance)
      self.instance = None

    # Delete the static IP address.
    if self.address_name:
      self.gce_context.DeleteAddress(self.address_name)
      self.address_name = self.address = None

    # Delete the GCE image.
    # Have to delete the image after all instances are deleted because if the
    # image is being used to create an instance (e.g., current process is asked
    # to terminate during instance creation), it cannot be deleted until the
    # instance creation ends.
    if self.image:
      self.gce_context.DeleteImage(self.image)
    self.image = self.image_link = None

    # Delete the tarball uploaded GCS.
    # For the same reason, it's safer to delete the tarball after the image is
    # deleted.
    if self.tarball_remote:
      self.gscontext.DoCommand(['rm', self.tarball_remote])
    self.tarball_remote = None

  def _HandleFail(self, log_directory, fail_directory):
    """Handles test failures.

    In case of a test failure, copy necessary files, i.e., the GCE tarball and
    ssh private key, to |fail_directory|, which will be later archived and
    uploaded to a GCS bucket by chromite.

    Args:
      log_directory: The root directory where test logs are stored.
      fail_directory: The directory to copy files to.
    """
    parent_dir = os.path.dirname(fail_directory)
    if not os.path.isdir(parent_dir):
      os.makedirs(parent_dir)

    try:
      # Copy logs. Must be done before moving image, as this creates
      # |fail_directory|.
      shutil.copytree(log_directory, fail_directory)

      # Copy GCE tarball and ssh private key for debugging.
      shutil.copy(self.tarball_local, fail_directory)
      if self.ssh_private_key is not None:
        shutil.copy(self.ssh_private_key, fail_directory)
    except (shutil.Error, OSError, IOError) as e:
      logging.warning('Ignoring error while copying logs: %s', e)

  def _GsPathToUrl(self, gs_path):
    """Converts a gs:// path to a URL.

    A formal URL is needed when creating an image from a GCS object.

    Args:
      gs_path: A GS path, e.g., gs://foo-bucket/bar.tar.gz.

    Returns:
      A GCS URL to the same object.

    Raises:
      ValueError if |gs_path| is not a valid GS path.
    """
    if not gs_path.startswith(self._GS_PATH_COMMON_PREFIX):
      raise ValueError('Invalid GCS path: %s' % gs_path)
    return gs_path.replace(self._GS_PATH_COMMON_PREFIX,
                           self._GS_URL_COMMON_PREFIX, 1)

  def _WaitForBackgroundDeleteProcesses(self):
    """Waits for all background proecesses to finish."""
    for p in self._bg_delete_processes:
      p.join()
    self._bg_delete_processes = []


def _OnGCE():
  """Checks if running on a GCE VM or not."""
  try:
    urllib2.urlopen('http://metadata.google.internal', timeout=10)
    return True
  except urllib2.URLError:
    return False
