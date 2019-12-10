#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This script can be used to upload CTS results to CTS and APFE buckets."""

from lib.upload_utils import UploadUtils
from xml.dom import minidom

import argparse
import getopt
import os.path
import sys


class UploadCts(UploadUtils):
  """Helps upload CTS results to gs:// buckets.

  Prints CTS test results with their pass/fail status to terminal.
  Prints gsutil links to the terminal to upload CTS results to gs:// buckets
  to get the results in the tooling.

  Attributes:
    test_board_name: Test board name.
    current_test_board_name: Temporary string to hold current test board name.
    build_mismatch_exist: A boolean indicating if build mismatch exists.
    failed_tests_exist: A boolean indicating if failed tests exist.
    valid_exist: A boolean indicating if any valid file with the
                 correct build version exists.
    untested_tests_exist: A boolean indicating if untested tests exist.
  """
  def __init__(self, input_build_id, dir_path):
    super(UploadCts, self).__init__()
    self.test_board_name = None
    self.current_test_board_name = None
    self.build_mismatch_exist = False
    self.valid_exist = False
    self.untested_tests_exist = False
    self.obsolete_files_exist = False
    self.input_build_id = input_build_id
    self.dir_path = dir_path
    self.nextelem = 0
    self.idx = 0

  def PrintBuildInfoList(self):
    """Sorts build information by build board and prints to the terminal."""
    self.build_info_list.sort(key=lambda x: x[1])
    for item in self.build_info_list:
      self.idx = (self.idx + 1) % len(self.build_info_list)
      self.nextelem = self.build_info_list[self.idx]
      if self.current_test_board_name != item[1]:
        title_msg = 'List of files for %s' % item[1]
        table_column_header = self.TABLE_HEADER_CTS

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

        self.current_test_board_name = item[1]
        if self.failed_list:
          self.failed_list.clear()
        if self.passed_list:
          self.passed_list.clear()
        self.row_count = 0

      self.SegregateCtsDataToPrint(item)
      #Print failed result if there is only one item in the list.
      if len(self.build_info_list) == 1:
        if self.failed_list:
          for i in range(len(self.failed_list)):
            self.PrintCtsResults(self.failed_list[i])

      #If there is a mix of passed & failed results, print only valid failures.
      if self.failed_list:
        if self.passed_list:
        #If a test has passed at least once, the results are not printed.
          for i in range(len(self.failed_list)):
            for j in range(len(self.passed_list)):
              if(self.failed_list[i][1] == self.passed_list[j][1] and
                 self.failed_list[i][3] == self.passed_list[j][3] and
                 self.failed_list[i][5] == self.passed_list[j][5]):
                self.found = 1
              else:
                if self.found != 1:
                  self.found = 0
          #Check no more results to parse for board and print valid failure.
          if self.found == 0 and self.nextelem[1] != item[1]:
            for i in range(len(self.failed_list)):
              self.PrintCtsResults(self.failed_list[i])
    print('\n')

  def PrintGsutilLinks(self, dir_path):
    """Prints gsutil links to upload results to CTS and APFE buckets.

       Sample APFE:board.board for non-unibuild.
       Sample APFE:model.board for unibuild.
       Append veyron_ and auron_ to model name for veyron and auron boards.
       Sample:auron_yuna.auron_yuna-release,veyron_mighty.veyron_mighty-release

    Args:
      dir_path: Results directory path.
    """
    for item in self.build_info_list:
      if self.test_board_name != item[1]:
        if item[1].startswith('veyron') or item[1].startswith('auron'):
          print('gsutil cp -r {0}/{1}.{2}-release/ '
                'gs://chromeos-cts-apfe/'
                .format(dir_path, item[1], item[1]))
        else:
          print('gsutil cp -r {0}/{1}.{2}-release/ gs://chromeos-cts-apfe/'
                .format(dir_path, item[2], item[1]))
        print('gsutil cp -r {0}/{1}_{2}/ '
              'gs://chromeos-cts-results/manual'
              .format(dir_path, item[3], item[1]))
        self.test_board_name = item[1]


  def ParseXmlFile(self, abs_input_file_path, test_result_filename, dir_path):
    """Gets build information from test_result.xml file.

    Parses the test result xml file to obtain build information. Adds build
    information to a list. Handles Untested tests if they exist. Untested
    tests may not have complete build information or may have partial
    build information in the test_result.xml file.

    Args:
      abs_input_file_path: Absolute input file path.
                           Eg: ~/Downloads/Manual/2017.09.22_14.27.09.zip
      test_result_filename: test result file name.
                            Eg: test_result.xml
      dir_path: Results directory path.
                Eg: ~/Downloads/Manual
    """
    self.GetXmlTagNamesCts()
    tag_list = self.GetXmlTagNamesCts()
    summary = tag_list[0]
    build_version = tag_list[1]
    build_board_version = tag_list[2]
    build_model_version = tag_list[3]
    build_id_type = tag_list[4]
    test_package_list = tag_list[5]
    test_package_v = tag_list[6]
    build_abi_type = tag_list[7]
    failed = tag_list[8]
    passed = tag_list[9]
    test = tag_list[10]
    name = tag_list[11]
    split_file_list = self.SplitFileName(abs_input_file_path)
    basename = split_file_list[1]
    full_base_name = os.path.join(dir_path, basename)
    basename_xml_file = split_file_list[2]
    absolute_base_xml_file = os.path.join(dir_path, basename_xml_file)
    timestamp = basename
    self.CopyFileToDestination(full_base_name,
                               test_result_filename,
                               dir_path,
                               basename_xml_file)
    xml_doc = minidom.parse(absolute_base_xml_file)
    summary = xml_doc.getElementsByTagName(summary)
    build_info = xml_doc.getElementsByTagName(build_version)
    test_package_list = xml_doc.getElementsByTagName(test_package_list)
    test = xml_doc.getElementsByTagName(test)
    if not build_info:
      self.UpdateBuildInfoList([timestamp,
                                'null',
                                'null',
                                'null',
                                'null',
                                '0',
                                '0'])
      self.untested_tests_exist = True
    elif not build_info[0].hasAttribute(build_board_version):
      self.UpdateBuildInfoList([timestamp,
                                'null',
                                'null',
                                'null',
                                'null',
                                '0',
                                '0'])
      self.untested_tests_exist = True
    elif not test_package_list:
      self.UpdateBuildInfoList([timestamp,
                                'null',
                                'null',
                                'null',
                                'null',
                                '0',
                                '0'])
      self.untested_tests_exist = True
    else:
      build_board = build_info[0].attributes[build_board_version].value
      build_model = build_info[0].attributes[build_model_version].value
      build_id = build_info[0].attributes[build_id_type].value
      test_package = test_package_list[0].attributes[test_package_v].value
      build_abi = test_package_list[0].attributes[build_abi_type].value
      failed = summary[0].attributes[failed].value
      passed = summary[0].attributes[passed].value
      test = test[0].attributes[name].value
      self.UpdateBuildInfoList([timestamp,
                                build_board,
                                build_model,
                                build_id,
                                build_abi,
                                test_package,
                                test,
                                failed,
                                passed])

  def ProcessFilesToUpload(self, input_build_id, dir_path):
    """Process Files to Upload to CTS and APFE Buckets.

    Parses the test_result.xml file to obtain build information.Checks for file
    validity by comparing with provided input BuildID. Pushes valid files to
    appropriate folders to upload to APFE and CTS buckets.Pushes invalid
    files to Obsolete Folder.Pushes untested files if any to UnTested
    Folder.

    Args:
      input_build_id: BuildID command line argument.
      dir_path: Results directory path.
    """
    test_result_filename_n_build = 'test_result.xml'
    build_id = ' '
    item = ' '
    for the_file in os.listdir(dir_path):
      if the_file.endswith('.zip'):
        full_file_path = os.path.join(dir_path, the_file)
        self.ExtractZipFile(full_file_path, dir_path)
        self.ParseXmlFile(full_file_path,
                          test_result_filename_n_build,
                          dir_path)

        for item in self.build_info_list:
          build_id = item[3]

        if build_id == input_build_id:
          self.valid_exist = True
          self.CreateApfeFolder(full_file_path, dir_path)
          self.CreateCtsFolder(full_file_path, dir_path)

        else:
          self.obsolete_files_exist = True
          if self.untested_tests_exist is True:
            self.build_info_list.remove(item)
            self.CreateUntestedFolder(full_file_path, dir_path)
            self.untested_tests_exist = False
          else:
            self.build_mismatch_exist = True
            self.build_info_list.remove(item)
            self.CreateObsoleteFolder(full_file_path, dir_path)

  def PrintData(self, dir_path):
    """Print results/gsutil links or error message if invalid files exist."""
    if not self.obsolete_files_exist:
      self.PrintBuildInfoList()
      self.PrintGsutilLinks(dir_path)

    if self.build_mismatch_exist is True and self.valid_exist is True:
      self.PrintBuildInfoList()
      self.PrintGsutilLinks(dir_path)
      self.PrintObsoleteFolderCount()

    if self.untested_file_count > 0 and self.valid_exist is True:
      self.PrintBuildInfoList()
      self.PrintGsutilLinks(dir_path)
      self.PrintUntestedFolderCount()

    if self.obsolete_files_exist is True and not self.valid_exist:
      self.PrintObsoleteFolderCount()
      self.PrintUntestedFolderCount()

def main(argv):
  """Processes result files and prints gsutil links to upload CTS results.

  Displays help message when script is called without expected arguments.
  Displays Usage: upload_cts.py <build_id> <results_dir_path>.
  """
  parser = argparse.ArgumentParser()
  parser.add_argument('build_id',
                      help='upload_cts.py <build_id> <results_dir_path>')
  parser.add_argument('dir_path',
                      help='upload_cts.py <build_id> <results_dir_path>')
  args = parser.parse_args()

  cts = UploadCts(args.build_id, args.dir_path)

  if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)
  parser.parse_args()
  try:
    opts, args = getopt.getopt(argv, 'hb:', ['build_id='])
  except getopt.GetoptError:
    sys.exit(2)
  for opt in opts:
    if opt == '-h':
      cts.usage()
      sys.exit()
  cts.ProcessFilesToUpload(cts.input_build_id, cts.dir_path)
  os.system('stty cols 120')
  cts.PrintData(cts.dir_path)

if __name__ == '__main__':
  main(sys.argv[1:])
