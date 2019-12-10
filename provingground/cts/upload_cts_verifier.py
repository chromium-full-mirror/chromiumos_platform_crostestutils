#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This script uploads CTS Verifier results to CTS and APFE gs:// buckets."""

from lib.upload_utils import UploadUtils
from xml.dom import minidom

import argparse
import getopt
import os.path
import sys


class UploadCtsVerifier(UploadUtils):
  """Helps upload CTS-V results to gs:// buckets.

  Prints CTS-V test results with their pass/fail status to terminal.
  Prints gsutil links to the terminal to upload CTS-V results to gs:// buckets
  to get the results in the tooling.

  Attributes:
    build_mismatch_exist: A boolean indicating if build mismatch exists.
    failed_tests_exist: A boolean indicating if failed tests exist.
    valid_files_exist: A boolean indicating if any valid file with the
                       correct build version exists.
    untested_tests_exist: A boolean indicating if untested tests exist.
    test_board_name_list: List of test board names.
  """

  def __init__(self):
    super(UploadCtsVerifier, self).__init__()
    self.build_mismatch_exist = False
    self.failed_tests_exist = False
    self.valid_files_exist = False
    self.untested_tests_exist = False
    self.test_board_name_list = []

  def PrintBuildInfoList(self):
    """Sorts build information by build board and prints to the terminal."""
    self.build_info_list.sort(key=lambda x: x[1])
    for item in self.build_info_list:
      if item[1] not in self.test_board_name_list:
        title_msg = 'List of files for %s' % item[1]
        table_column_header = self.TABLE_HEADER_CTSV
        print(self.BOLD +
              self.C_PURPLE +
              title_msg +
              self.BOLD +
              self.C_END)
        print(self.BOLD +
              self.C_BLACK +
              table_column_header +
              self.BOLD +
              self.C_END)

        self.test_board_name_list.append(item[1])
        self.PrintFormattedDataCtsv(item)
    print('\n')

  def PrintGsutilLinks(self, dir_path):
    """Prints gsutil links to upload results to CTS dashboard and APFE buckets.

       CTS-V APFE :board.board for non-unibuild.
       CTS-V APFE :model.board for unibuild.
       Appended veyron_ and auron_ to model name for veyron and auron boards.
       Sample:auron_yuna.auron_yuna-release,veyron_mighty.veyron_mighty-release

    Args:
      dir_path: Results directory path.
    """
    for item in self.build_info_list:
      if item[1].startswith('veyron') or item[1].startswith('auron'):
        gsutil_msg_apfe = ('gsutil cp -r {0}/{1}.{2}-release/ '
                           'gs://chromeos-ctsverifier-results/'
                           .format(dir_path, item[1], item[1]))
      else:
        gsutil_msg_apfe = ('gsutil cp -r {0}/{1}.{2}-release/ '
                           'gs://chromeos-ctsverifier-results/'
                           .format(dir_path, item[2], item[1]))
      gsutil_msg_cts = ('gsutil cp -r {0}/{1}_{2}/ '
                        'gs://chromeos-cts-results/ctsVerifier'
                        .format(dir_path, item[3], item[1]))
      print(self.BOLD +
            self.C_PURPLE +
            gsutil_msg_cts +
            self.BOLD +
            self.C_END)
      print(self.BOLD +
            self.C_PURPLE +
            gsutil_msg_apfe +
            self.BOLD +
            self.C_END)

  def PrintIfAllTestsPassed(self):
    """Print message to terminal if all tests have passed."""
    if not self.failed_tests_exist and self.build_mismatch_file_count == 0:
      print('All Cts Verifier Tests passed!')

  def PrintFailedTestResults(self, tests):
    """Prints failed results if any to the terminal.

    Args:
      tests: CTS Verifier Test Results.
    """
    test_title = ' '
    result = ' '
    for test in tests:
      test_title = test.getAttribute('name')
      result = test.getAttribute('result')
      if result == 'fail' or result == 'not-executed':
        self.failed_tests_exist = True
        print('Test Title:%s, Result:%s' % (test_title, result))
        print('\n')

  def ParseXmlFile(self, abs_input_file_path, dir_path):
    """Gets build information from CTS Verifier xml file.

    Parses the CTS Verifier Xml File to obtain Build Information such as
    basename, build_board, build_id, suite_version.

    Args:
      abs_input_file_path: Absolute Input file path.
                           Eg: ~/Downloads/ctsv/2017.09.21_17.13.04-
                           CTS_VERIFIER-google-relm-relm_cheets-R62-9901.20.0
      dir_path: Results directory path.
                Eg: ~/Downloads/Manual

    Returns:
      tests: CTS Verifier Test Results.
    """
    test_result_filename_n_build = 'test_result.xml'
    tag_list = self.GetXmlTagNamesCtsv()
    build_version = tag_list[0]
    result = tag_list[1]
    suite_version = tag_list[2]
    build_board = tag_list[3]
    build_model = tag_list[4]
    build_id_n = tag_list[5]
    test = tag_list[6]
    split_file_list = self.SplitFileName(abs_input_file_path)
    basename = split_file_list[1]
    full_base_name = os.path.join(dir_path, basename)
    basename_xml_file = split_file_list[2]
    absolute_base_xml_file = os.path.join(dir_path, basename_xml_file)
    self.CopyFileToDestination(full_base_name,
                               test_result_filename_n_build,
                               dir_path,
                               basename_xml_file)
    xml_doc = minidom.parse(absolute_base_xml_file)
    build = xml_doc.getElementsByTagName(build_version)
    verifier_info = xml_doc.getElementsByTagName(result)
    suite_version = verifier_info[0].attributes[suite_version].value
    build_board = build[0].attributes[build_board].value
    build_model = build[0].attributes[build_model].value
    build_id = build[0].attributes[build_id_n].value
    tests = xml_doc.getElementsByTagName(test)
    self.UpdateBuildInfoList(
        [basename, build_board, build_model, build_id, suite_version])
    return tests

  def ProcessFilesToUpload(self, input_build_id, dir_path):
    """Process Files to Upload to CTS Verifier Bucket.

    Parses the test_result.xml file to obtain build information.
    Pushes valid files to appropriate folders to upload to CTS-V bucket.
    Pushes invalid files to Obsolete Folder.
    Print Build results to terminal.

    Args:
      input_build_id: Build ID for which results are to be uploaded.
      dir_path: Results directory path.
    """
    build_id = ' '
    item = ' '
    for the_file in os.listdir(dir_path):
      if the_file.endswith('.zip'):
        full_file = os.path.join(dir_path, the_file)
        self.ExtractZipFile(full_file, dir_path)
        tests = self.ParseXmlFile(the_file, dir_path)
        for item in self.build_info_list:
          build_id = item[3]
        if build_id == input_build_id:
          self.valid_files_exist = True
          self.failed_tests_exist = False
          self.CreateCtsvApfeFolder(full_file, dir_path)
          self.CreateCtsFolder(full_file, dir_path)
          self.PrintBuildInfoList()
          self.PrintFailedTestResults(tests)
          self.PrintIfAllTestsPassed()
        else:
          self.build_mismatch_exist = True
          self.build_info_list.remove(item)
          self.CreateObsoleteFolder(full_file, dir_path)

def main(argv):
  """Processes result files and prints gsutil links to upload CTS-V results.

    Displays help message when script is called without expected arguments.
    Displays Usage: upload_cts_verifier.py <build_id> <results_dir_path>
  """
  parser = argparse.ArgumentParser()
  parser.add_argument('build_id',
                      help='Usage: upload_cts_verifier.py'
                           '<build_id>'
                           '<results_dir_path>')
  parser.add_argument('dir_path',
                      help='Usage: upload_cts_verifier.py'
                           '<build_id>'
                           '<results_dir_path>')
  args = parser.parse_args()
  input_build_id = args.build_id
  dir_path = args.dir_path
  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  parser.parse_args()
  try:
    opts, args = getopt.getopt(argv, 'hb:', ['buildID='])
  except getopt.GetoptError:
    print('upload_cts_verifier.py <build_id> <results_dir_path>')
    sys.exit(2)
  ctsv = UploadCtsVerifier()
  for opt in opts:
    if opt == '-h':
      ctsv.usage()
      sys.exit()
  ctsv.ProcessFilesToUpload(input_build_id, dir_path)
  if ctsv.valid_files_exist is True:
    ctsv.PrintGsutilLinks(dir_path)
  if ctsv.build_mismatch_exist is True:
    ctsv.PrintObsoleteFolderCount()

if __name__ == '__main__':
  main(sys.argv[1:])
