#!/usr/bin/python2
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


def output_values(device, hw_id, fw_version, fw_file, ebuild_file):
  """Formats and prints results for a single type of hardware."""
  print('%s\t%s\t%s\t%s\t%s' % (
      device, hw_id, fw_version, fw_file, ebuild_file))


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
  result = re.findall(r'^%s=["\'](.*)["\']' % var, text, re.MULTILINE)
  if not result:
    return ''
  return result[-1]


def reduce_string(link, text):
  """Finds the absolute value of the given string.

  Assumes variables embedded in a string are in ${VAR} format.
  E.g., given '"${PRODUCT_ID_TP}_${FIRMWARE_VERSION_TP}.bin"' return
  '"85.0_7.0.bin"', after following all variables.
  Assumes the entire string could be a varible of the form
  $VAR (no { }).

  Args:
    link: the string which contains variables to reduce.
    text: the text containing the variable definitions.

  Returns:
    The given string with all variables replaced, or '' if error.
  """
  search = re.search(r'\$\{(.*?)\}', link)
  if not search:
    search = re.search(r'\$([^\s]*)', link)
    if not search:
      return link

  variable = search.group(1)
  value = find_value_of_variable(variable, text)
  if not value:
    return ''
  new_link = link.replace('${%s}' % variable, value)
  return reduce_string(new_link, text)


def find_values_from_line(device, line, text):
  """Finds the values to be output for the given dosym line.

  Makes exceptions for known formatting problems.

  Args:
    device: the name of the device, e.g., 'squawks'
    line: the dosym line to evaluate.  Passed in the form of a list:
        [linked from argument, NA, linked to argument].
    text: the text of the ebuild file.

  Returns:
    The hardware version, firmware version, and firmware filename.
    A value of None indicates that this entry should be skipped, and a value
    of '' indicates an error.
  """
  link_from = reduce_string(line[0], text) # dosym FROM
  link_to = reduce_string(line[2], text) # dosym TO

  # Find needed value from the symlink filenames.
  hw_id, fw_version, fw_file = '', '', ''
  if link_from != '':
    search = re.search(r'/([^/]*)_(.*)\.', link_from)
    if search:
      hw_id = search.group(1)
      fw_version = search.group(2)
  if link_to != '':
    search = re.search(r'/([^/]*?)(\.bin|\.fw)?"', link_to)
    if search:
      fw_file = search.group(1)

  # Exceptions for unfortunately formatted files.
  if device == 'lulu' and fw_file == '':
    bad_fmt = 'SYNA_TP_SYM_LINK_PATH=}'
    good_fmt = bad_fmt.replace('=', '')
    new_line = list(line)
    if bad_fmt in line[2]:
      new_line[2] = line[2].replace(bad_fmt, good_fmt)
      hw_id, fw_version, fw_file = find_values_from_line(
          device, new_line, text)
  elif device == 'kip' and link_from.find('dummy') >= 0:
    hw_id = None
  elif (device == 'sumo' and
        link_to and 'fw.bin' not in link_to):
    hw_id = None

  return hw_id, fw_version, fw_file


def find_values_in_file(path):
  """Finds all dosym lines in the file and outputs values as needed.

  If anything went wrong, outputs the devicename for manual inspection.

  Args:
    path: the path to the ebuild file.
  """
  device = re.search('overlay-(variant-)?([^/]*?)(-private)?/', path).group(2)
  with open(path) as fh:
    text = fh.read()

    # Find all symlinks for firmware and config files.  Some lines are
    # actually multiline in the file, so use findall to get the entirety.
    if not re.search('dosym', text):
      return
    search = re.findall(r'dosym\s([^\s]*)\s*(\\*\s*\n)?\s*([^\s]*)', text,
                        re.MULTILINE)
    if not search:
      return device

    # Each line has the format [from, N/A, to]
    problems_found = False
    for line in search:
      hw_id, fw_version, fw_file = find_values_from_line(device, line, text)
      # None = skip me.  '' = problem.
      if hw_id != None:
        if hw_id == '' or fw_version == '' or fw_file == '':
          problems_found = True
        else:
          output_values(device, hw_id, fw_version, fw_file, path)

    if problems_found:
      return device

def main():
  """Finds all touch-firmware files and find their firmware values."""
  file_dir = os.path.realpath(os.path.dirname(__file__))
  src_dir = os.path.join(file_dir, SRC_DIR)
  os.chdir(src_dir)
  find_output = ''
  cmd = 'find %s -name *touch-firmware-*-0.0.[0-9].ebuild'
  for d in ['private-overlays/', 'overlays/']:
    find_output += subprocess.check_output((cmd % d).split(' '))
  ebuilds = find_output.split()
  ebuilds.sort()

  # Find and output values.
  problem_devices = []
  for path in ebuilds:
    err = find_values_in_file(path)
    if err:
      problem_devices.append(err)

  # Output any problematic devices found, if any.
  if len(problem_devices) > 0:
    print('ERROR: please review %s' % problem_devices)

if __name__ == '__main__':
  main()
