#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This script has helper methods to facilitate CTS/CTS-V upload."""

from subprocess import check_call

import os
import shutil
import zipfile

class UploadUtils(object):
  """Internal Helper for CTS and CTS Verifier Upload scripts."""

  SPACE_COUNT_CTSV_BOARD_NAME = 14
  SPACE_COUNT_CTSV_BUILD_VERSION = 22
  SPACE_COUNT_VERIFIER_VERSION = 18
  SPACE_COUNT_ROW = 6
  SPACE_COUNT_TIMESTAMP = 17
  SPACE_COUNT_CTS_BOARD_NAME = 13
  SPACE_COUNT_CTS_BUILD_VERSION = 12
  SPACE_COUNT_CTS_BOARD_ABI = 13
  SPACE_COUNT_PACKAGE_NAME = 30
  SPACE_COUNT_FAILED_TESTS = 8
  SPACE_COUNT_PASSED_TESTS = 8
  SPACE_COUNT_TEST_NAME = 70
  TEST_PASS = '1'
  TEST_PASS_X86_64 = '2'
  TEST_FAIL = '1'
  C_PURPLE = '\033[95m'
  C_RED = '\033[91m'
  C_BLACK = '\033[98m'
  BOLD = '\033[1m'
  C_END = '\033[00m'
  TABLE_HEADER_CTS = ('RNO  : TIME STAMP            : BOARD    : '
                      'BUILD VERSION    : BOARD ABI  '
                      ' : TEST MODULE NAME         : TEST CASE NAME '
                      '                                                    '
                      ': FAILED : PASSED')
  TABLE_HEADER_CTSV = (' BUILD BOARD NAME : '
                       'BUILD BOARD VERSION : '
                       'CTS VERIFIER VERSION')
  def __init__(self):
    self.build_info_list = []
    self.passed_list = []
    self.failed_list = []
    self.obsolete_file_count = 0
    self.untested_file_count = 0
    self.build_mismatch_file_count = 0
    self.found = 0
    self.row_count = 0

  def PrintObsoleteFolderCount(self):
    """Prints obsolete file count in case of build id mismatch."""
    if self.build_mismatch_file_count != 0:
      err_msg = ('Build ID Mismatch!Pushed {0} invalid files to BuildID'
                 ' Mismatch Folder'.format(self.build_mismatch_file_count))
      print(self.BOLD + self.C_RED + err_msg +self.BOLD+ self.C_END)

  def PrintUntestedFolderCount(self):
    """Prints untested file count if untested tests exist."""
    if self.untested_file_count != 0:
      err_msg = ('Untested Test(s) Detected!Pushed {0} files to Untested'
                 ' Tests Folder'.format(self.untested_file_count))
      print(self.BOLD + self.C_RED + err_msg +self.BOLD+ self.C_END)

  def ExtractZipFile(self, zipped_file, dir_path):
    """Extracts Zip File contents to current working directory.

    Args:
      zipped_file: Input zip file.
      dir_path: Results directory path.
    """
    with zipfile.ZipFile(zipped_file, 'r') as zf:
      zf.extractall(dir_path)

  def CopyFileToDestination(self, src_path, src_file_name,
                            dest_path, dest_file_name):
    """Copies file from source path to destination path

    Args:
      src_path: source file path.
      src_file_name: source file name.
      dest_path: destination file path.
      dest_file_name: destination file name.
    """
    src_file = os.path.join(src_path, src_file_name)
    dest_file = os.path.join(dest_path, dest_file_name)
    try:
      shutil.copy(src_file, dest_file)
    except IOError as e:
      print('Unable to copy file. %s' % e)

  def SplitFileName(self, file_path):
    """Splits file to create file names with different extensions.

    Args:
      file_path: Input file path.
      Sample Input File: ~/Downloads/Manual/2017.09.22_14.27.09.zip

    Returns:
      List of base file names with different extensions.
      Sample base file names returned in split_file_list:
      base: 2017.09.22_14.27.09.zip
      basename: 2017.09.22_14.27.09
      basename_xml_file: 2017.09.22_14.27.09.xml
      basename_xml_gz_file: 2017.09.22_14.27.09.xml.gz
    """
    base = os.path.basename(file_path)
    basename = os.path.splitext(base)[0]
    basename_xml_file = '%s%s' % (basename, '.xml')
    basename_xml_gz_file = '%s%s%s' % (basename, '.xml', '.gz')
    return [base,
            basename,
            basename_xml_file,
            basename_xml_gz_file]

  def PrintFormattedDataCtsv(self, item):
    """Prints build information in a tabular form to the terminal.

    Sample table printed to terminal:
    Build Board Name : Build Board Version : CTS VERIFIER VERSION
    : relm           : R62-9901.20.0       : 7.1_r9

    Args:
      item: Information list to be printed to terminal.
    """
    print(('{:^%s}'%self.SPACE_COUNT_CTSV_BOARD_NAME).format(item[1]),
          ('{:>%s}'%self.SPACE_COUNT_CTSV_BUILD_VERSION).format(item[3]),
          ('{:>%s}'%self.SPACE_COUNT_VERIFIER_VERSION).format(item[4]))

  def SegregateCtsDataToPrint(self, item):
    """Segregates passed and failed results into two separate lists.

    Args:
      item: Board information.
    """
    rerun = 0
    if ((item[8] == self.TEST_PASS and
         item[7] != self.TEST_FAIL) or
        item[8] == self.TEST_PASS_X86_64):
      self.passed_list.append(item)

      for i in range(len(self.passed_list)):
        if(self.passed_list[i][1] == item[1] and
           self.passed_list[i][4] == item[4] and
           self.passed_list[i][6] == item[6]):
          rerun = rerun + 1
        if rerun > 1:
          break
      #Print valid passed result, reruns are not printed.
      if rerun == 1:
        self.PrintCtsResults(item)
    else:
      self.failed_list.append(item)

  def PrintCtsResults(self, item):
    """Prints build information in a tabular form to the terminal.

    Sample table printed to terminal:
    : Time Stamp         : Build Board Name : Build Version: Build BOARD ABI
    : PACKAGE NAME           : FAILED  : PASSED
    : 2017.09.22_14.27.09: relm             : R62-9901.20.0: x86
    : CtsUsageStatsTestCases : 0       : 1

    Args:
      item: Information List to be printed to terminal.
    """
    self.row_count = self.row_count + 1
    print(('{:<%i}'%self.SPACE_COUNT_ROW).format(self.row_count),
          ('{:>%s}'%self.SPACE_COUNT_TIMESTAMP).format(item[0]),
          ('{:^%s}'%self.SPACE_COUNT_CTS_BOARD_NAME).format(item[1]),
          ('{:^%s}'%self.SPACE_COUNT_CTS_BUILD_VERSION).format(item[3]),
          ('{:>%s}'%self.SPACE_COUNT_CTS_BOARD_ABI).format(item[4]),
          ('{:^%s}'%self.SPACE_COUNT_PACKAGE_NAME).format(item[5]),
          ('{:<%s}'%self.SPACE_COUNT_TEST_NAME).format(item[6]),
          ('{:<%s}'%self.SPACE_COUNT_FAILED_TESTS).format(item[7]),
          ('{:<%s}'%self.SPACE_COUNT_PASSED_TESTS).format(item[8]))

  def GetXmlTagNamesCtsv(self):
    """Get xml tag names.

    Returns:
      tag_list: List of xml tag names.
    """
    BUILD_N_XML_TAG = 'Build'
    RESULT_XML_TAG = 'Result'
    SUITE_VERSION_XML_TAG = 'suite_version'
    BUILD_BOARD_XML_TAG = 'build_board'
    BUILD_MODEL_XML_TAG = 'build_product'
    BUILD_ID_N_XML_TAG = 'build_id'
    TEST_XML_TAG = 'Test'
    return [BUILD_N_XML_TAG,
            RESULT_XML_TAG,
            SUITE_VERSION_XML_TAG,
            BUILD_BOARD_XML_TAG,
            BUILD_MODEL_XML_TAG,
            BUILD_ID_N_XML_TAG,
            TEST_XML_TAG]

  def GetXmlTagNamesCts(self):
    """Get xml tag names from test result xml file.

    Args:
      test_result_filename: Build Test Result file name.

    Returns:
      tag_list: List of xml tag names.
    """
    SUMMARY_XML_TAG = 'Summary'
    BUILD_N_XML_TAG = 'Build'
    BUILD_BOARD_VERSION_XML_TAG = 'build_board'
    BUILD_MODEL_VERSION_XML_TAG = 'build_product'
    BUILD_ID_N_XML_TAG = 'build_id'
    TEST_PACKAGE_LIST_N_XML_TAG = 'Module'
    TEST_PACKAGE_NAME_N_XML_TAG = 'name'
    BUILD_ABI_TYPE_XML_TAG = 'abi'
    FAILED_XML_TAG = 'failed'
    PASSED_XML_TAG = 'pass'
    TEST_XML_TAG = 'Test'
    NAME_XML_TAG = 'name'

    return [SUMMARY_XML_TAG,
            BUILD_N_XML_TAG,
            BUILD_BOARD_VERSION_XML_TAG,
            BUILD_MODEL_VERSION_XML_TAG,
            BUILD_ID_N_XML_TAG,
            TEST_PACKAGE_LIST_N_XML_TAG,
            TEST_PACKAGE_NAME_N_XML_TAG,
            BUILD_ABI_TYPE_XML_TAG,
            FAILED_XML_TAG,
            PASSED_XML_TAG,
            TEST_XML_TAG,
            NAME_XML_TAG]

  def UpdateBuildInfoList(self, obj):
    """Appends object to list.

    Args:
      obj: Contents to be appended to list.
    """
    self.build_info_list.append(obj)

  def CreateApfeFolder(self, filename, dir_path):
    """Creates hierarchy for uploading result files to APFE bucket.

    Args:
      filename: Valid file to upload to APFE folder.
      dir_path: Results directory path.
    """
    build_board = ''
    split_file_list = self.SplitFileName(filename)
    base = split_file_list[0]
    build_model = self.build_info_list[-1][2]
    build_board = self.build_info_list[-1][1]
    build_id_folder = self.build_info_list[-1][3]
    if build_board.startswith('veyron_') or build_board.startswith('auron_'):
      release_folder = '%s.%s-release' % (build_board, build_board)
    else:
      release_folder = '%s.%s-release' % (build_model, build_board)
    manual_folder = 'manual'
    apfe_path = os.path.join(dir_path, release_folder, build_id_folder,
                             manual_folder)
    if not os.path.exists(apfe_path):
      os.makedirs(apfe_path)
    self.CopyFileToDestination(dir_path, base, apfe_path, base)

  def CreateCtsvApfeFolder(self, filename, dir_path):
    """Creates hierarchy for uploading CTS-V result files to APFE bucket.

    Args:
      filename: Valid file to upload to APFE folder.
      dir_path: Results directory path.
    """
    build_board = ''
    split_file_list = self.SplitFileName(filename)
    base = split_file_list[0]
    build_board = self.build_info_list[-1][1]
    build_model = self.build_info_list[-1][2]
    build_id_folder = self.build_info_list[-1][3]

    if build_board.startswith('veyron_') or build_board.startswith('auron_'):
      release_folder = '%s.%s-release' % (build_board, build_board)
    else:
      release_folder = '%s.%s-release' %(build_model, build_board)
    apfe_path = os.path.join(dir_path, release_folder, build_id_folder)
    if not os.path.exists(apfe_path):
      os.makedirs(apfe_path)
    self.CopyFileToDestination(dir_path, base, apfe_path, base)


  def CreateCtsFolder(self, filename, dir_path):
    """Creates hierarchy for upload to CTS Dashboard bucket.

    Args:
      filename: Input File to be added to CTS folder.
      dir_path: Results directory path.
    """
    build_id = None
    build_board = None
    build_board = self.build_info_list[-1][1]
    build_id = self.build_info_list[-1][3]
    split_file_list = self.SplitFileName(filename)
    basename_xml_file = split_file_list[2]
    basename_xml_gz_file = split_file_list[3]
    build_id_board_folder = '%s_%s' % (build_id, build_board)
    cts_path = os.path.join(dir_path, build_id_board_folder)
    if not os.path.exists(cts_path):
      os.makedirs(cts_path)
    gzip_file_path = os.path.join(dir_path, basename_xml_file)
    check_call(['gzip', gzip_file_path])
    self.CopyFileToDestination(dir_path,
                               basename_xml_gz_file,
                               cts_path,
                               basename_xml_gz_file)

  def CreateUntestedFolder(self, filename, dir_path):
    """Creates Untested Folder to save files if there are UnTested Tests.

    Args:
      filename: Input file name.
      dir_path: Results directory path.
    """
    split_file_list = self.SplitFileName(filename)
    base = split_file_list[0]
    if self.untested_tests_exist is True:
      self.untested_file_count = self.untested_file_count + 1
    untested_folder = 'Untested Tests'
    untested_path = os.path.join(dir_path, untested_folder)
    if not os.path.exists(untested_path):
      os.makedirs(untested_path)
    self.CopyFileToDestination(dir_path, base, untested_path, base)

  def CreateObsoleteFolder(self, filename, dir_path):
    """Creates Obsolete Folder to save files if there is a BUILDID mismatch.

    Args:
      filename: Input file name.
      dir_path: Results directory path.
    """
    split_file_list = self.SplitFileName(filename)
    base = split_file_list[0]
    if self.build_mismatch_exist is True:
      self.build_mismatch_file_count = self.build_mismatch_file_count + 1
    if self.untested_tests_exist is True:
      self.untested_file_count = self.untested_file_count + 1
    obsolete_folder = 'BuildID Mismatch Folder'
    obsolete_path = os.path.join(dir_path, obsolete_folder)
    if not os.path.exists(obsolete_path):
      os.makedirs(obsolete_path)
    self.CopyFileToDestination(dir_path, base, obsolete_path, base)
