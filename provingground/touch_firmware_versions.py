#!/usr/bin/env python2
# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Lists out supported touch hardware and fw versions for all devices.

1. Finds the touch firmware ebuilds in both private and public overlays.
2. In those files, looks for "dosym" lines.
3. In the dosym lines, follows all shell variables to their absolute values.
4. As touch firmware names follow an expected format, figures out
   hwid_fwversion and fwname from the absolute values.
5. Handles a few formatting exceptions.
6. Outputs device, hwid, fw version, fw file_name, ebuild filepath for each
   unique hardware on each found device.

Format assumptions:
  - firmware names are of the form HWID_FWVERSION
  - variable definitions are in the format VAR_NAME="DEF" or 'DEF'
  - variable usage is ${VAR_NAME}
"""

from __future__ import print_function

import os
import re
import subprocess

SRC_DIR = '../../../' # Relative path from this file to source directory


class firmwareInfo(object):
  """Information about a particular firmware file."""
  def __init__(self, device, path):
    self.device = device
    self.ebuild_filepath = path

    self.hw_id = None
    self.fw_id = None
    self.fw_file = None

    self.problem_found = False
    self.error = ''

  def __str__(self):
    return ('%s\t%s\t%s\t%s\t%s' % (
        self.device, self.hw_id, self.fw_id, self.fw_file,
        self.ebuild_filepath))

  def set_ids(self, hwid, fwid, filename):
    self.hw_id = hwid
    self.fw_id = fwid
    self.fw_file = filename


def find_value_of_variable(var, text):
  """Returns the value as defined for the given variable in the given text.

  Assumes variable definitions are in VAR="DEF" or VAR='DEF' format.
  E.g., given 'FOO', find 'FOO="BAR"' in the text and return 'BAR'.

  Args:
    var: the name of the variable.
    text: the text which has the variable definition.

  Returns:
    A string of the value or '' if not found.
  """
  result = re.findall(r'^%s=["\']?(.*?)["\']?\n' % var, text, re.MULTILINE)
  if not result:
    return ''
  return result[-1]


def reduce_string(link, text):
  """Finds the absolute value of the given string.

  Assumes variables embedded in a string are in ${VAR} or \s$VAR\s format.
  E.g., given '"${PRODUCT_ID_TP}_${FIRMWARE_VERSION_TP}.bin"' return
  '85.0_7.0.bin', after following all variables.
  Assumes the entire string could be a varible of the form $VAR (no { }).

  Args:
    link: the string which contains variables to reduce.
    text: the text containing the variable definitions.

  Returns:
    The given string with all variables replaced, or '' if error.
  """
  var_formats = [r'\$\{(.*?)\}', r'\$([^\s]*)']
  for var_format in var_formats:
    search = re.search(var_format, link)
    if search:
      break
  else:
    return link.replace('"', '')

  variable = search.group(1)
  value = find_value_of_variable(variable, text)
  if not value:
    return ''

  # Whatever the variable format ended up being, swap in the value found.
  variable_format = search.group(0).replace(search.group(1), '%s')
  new_link = link.replace(variable_format % variable, value)

  return reduce_string(new_link, text)


def find_info_from_line(info, line, text):
  """Finds the info to be output for the given dosym line.

  Makes exceptions for known formatting problems.

  Args:
    info: the firmwareInfo class for this firmware line.  This function will
        update this object with hardware id, firmware id, and firmware path.
    line: the dosym line to evaluate.  Passed in the form of a list:
        [linked from argument, NA, linked to argument].
    text: the text of the ebuild file.
  """
  link_from = reduce_string(line[0], text) # dosym FROM
  link_to = reduce_string(line[2], text) # dosym TO

  # Find needed value from the symlink filenames.
  hw_id, fw_version, fw_file = '', '', ''
  if link_from != '':
    search = re.search(r'([^/"]*)_(.*)\.', link_from)
    if search:
      hw_id = search.group(1).replace('"', '')
      fw_version = search.group(2).replace('"', '')
  if link_to != '':
    fw_file = os.path.basename(link_to)

  info.set_ids(hw_id, fw_version, fw_file)

  # Exceptions for unfortunately formatted files.
  if (info.device == 'lulu' or info.device == 'umaro') and fw_file == '':
    bad_fmt = 'SYNA_TP_SYM_LINK_PATH=}'
    good_fmt = bad_fmt.replace('=', '')
    new_line = list(line)
    if bad_fmt in line[2]:
      new_line[2] = line[2].replace(bad_fmt, good_fmt)
      find_info_from_line(info, new_line, text)
  elif info.device == 'kip' and link_from.find('dummy') >= 0:
    info.hw_id = None
  elif info.device == 'sumo' and link_to and 'fw.bin' not in link_to:
    info.hw_id = None


def find_firmwares_in_file(path):
  """Finds all dosym lines in the file and outputs values as needed.

  If anything went wrong, outputs the devicename for manual inspection.

  Args:
    path: the path to the ebuild file.
  """
  def create_error_info(device, path, error):
    error_values = firmwareInfo(device, path)
    error_values.problem_found = True
    error_values.error = error
    return error_values

  search = re.search('/(overlay-)?(variant-)?(baseboard-)?([^/]*?)(-private)?/',
                     path)
  if not search:
    return [create_error_info(
        path, path, 'Project path did not match expected format!')]

  device = search.group(4)

  with open(path) as fh:
    text = fh.read()

  # Special case for unified reef, look for "install_firmware".
  if device == 'reef':
    if not re.search('install_fw', text):
      return [create_error_info(
          device, path, 'No "install_fw" lines found in this file!')]

    search = re.findall(r'install_fw\s([^\s]*)\s*(\\*\s*\n)?\s*([^\s]*)', text,
                        re.MULTILINE)

  # For all other boards, find all symlinks for firmware and config files.
  else:
    if not re.search('dosym', text):
      return [create_error_info(
          device, path, 'No "dosym" lines found in this file!')]

    search = re.findall(r'dosym\s([^\s]*)\s*(\\*\s*\n)?\s*([^\s]*)', text,
                        re.MULTILINE)
  if not search:
    return [create_error_info(
        device, path, 'The dosym lines did not match expected format!')]

  # Each line has the format [from, N/A, to]
  values_list = []
  for line in search:
    values = firmwareInfo(device, path)
    find_info_from_line(values, line, text)
    if values.hw_id != None:
      if values.hw_id == '' or values.fw_id == '' or values.fw_file == '':
        values.problem_found = True
        values.error = ('Values did not make sense: %s, %s, %s' % (
            values.hw_id, values.fw_id, values.fw_file))
      values_list.append(values)

  return values_list


def firmware_versions():
  """Finds all touch-firmware files and their firmware values."""
  file_dir = os.path.realpath(os.path.dirname(__file__))
  src_dir = os.path.join(file_dir, SRC_DIR)
  os.chdir(src_dir)

  # Find ebuild files, e.g. chromeos-touch-firmware-caroline-0.0.1.ebuild
  find_output = ''
  cmd = 'find %s -regex .*touch-firmware-.*-[0-9.]+\.ebuild'
  for d in ['private-overlays/', 'overlays/']:
    find_output += subprocess.check_output((cmd % d).split(' '))
  ebuilds = find_output.split()
  ebuilds.sort()

  values_list = []
  for path in ebuilds:
    values_list += find_firmwares_in_file(path)

  values_list.sort(key=lambda x: x.device)
  return values_list

def main():
  values_list = firmware_versions()
  problem_devices = {}
  for values in values_list:
    if values.problem_found:
      problem_devices[values.device] = values.error
    else:
      print(values)

  # Output any problematic devices found, if any.
  if len(problem_devices) > 0:
    print('ERROR: please review %s' % problem_devices)


if __name__ == '__main__':
  main()
