# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Routines for reading performance results from a directory.

The directory should match the format created by the 'bootperf'
script; see comments in that script for a summary of the layout.
"""

import fnmatch
import json
import os
import re

import resultset


_PERF_KEYVAL_PATTERN = re.compile('(.*){perf}=(.*)\n')

def _ReadResultsJSONFile(results, file_):
  """Read a tast results-chart.json file and process the results.

  The `file_` parameter is a file object with contents in tast
  perf results-chart.json format:
      { <keyname>: { "summary": { "values": [<values (a list)>] } } }

  Each iteration's results are appended to the `results` parameter,
  which should be an instance of TestResultSet.

  Args:
    results: A TestResultSet where the result data will be
                 collected.
    file_: File object for the results file to be read.
  """
  # kvd: a dict of key => value dictionary.
  # Example: {'seconds_chrome_exec_to_login':'1.75', ...}.
  # Key and value are both string.
  # kvd_list is a list of kvd.
  kvd_list = []
  # Sample results-chart.json data:
  # {
  #   "seconds_kernel_to_startup": {
  #    "summary": {
  #     "units": "seconds",
  #     "improvement_direction": "down",
  #     "type": "list_of_scalar_values",
  #     "values": [
  #       1.4,
  #       1.41
  #     ]
  #    }
  #   },
  # }
  result_chart_json = json.load(file_)
  for key, res in result_chart_json.items():
    values = res['summary']['values']
    for i, val in enumerate(values):
      if i >= len(kvd_list):
        kvd_list.append({})
      kvd_list[i][key] = val
  for kvd in kvd_list:
    results.AddIterationResults(kvd)

_RESULTS_CHART = 'summary/tests/platform.BootPerf/results-chart.json'

def _ReadKeyvalFile(results, file_):
  """Read an autotest keyval file, and process the results.

  The `file_` parameter is a file object with contents in autotest
  perf keyval format:
      <keyname>{perf}=<value>

  Each iteration of the test is terminated with a single blank line,
  including the last iteration.  Each iteration's results are added
  to the `results` parameter, which should be an instance of
  TestResultSet.

  Args:
    results: A TestResultSet where the result data will be collected.
    file_: File object for the results file to be read.
  """
  kvd = {}
  for line in file_:
    if line == '\n':
      results.AddIterationResults(kvd)
      kvd = {}
      continue
    m = _PERF_KEYVAL_PATTERN.match(line)
    if m is None:
      continue
    kvd[m.group(1)] = m.group(2)


_RESULTS_KEYVAL = 'summary/platform_BootPerfServer/results/keyval'

def ReadResultsDirectory(dir_):
  """Process results from a 'bootperf' output directory.

  The accumulated results are returned in a newly created
  TestResultSet object.

  Args:
    dir_: The directory containing the test results keyval file.

  Returns:
    The TestResultSet object.
  """
  res_set = resultset.TestResultSet(dir_)
  dirlist = fnmatch.filter(os.listdir(dir_), 'run.???')
  dirlist.sort()
  for rundir in dirlist:
    keyval_path = os.path.join(dir_, rundir, _RESULTS_CHART)
    # Test if the run.??? dir contains a tast result-chart.json file.
    if os.path.exists(keyval_path):
      reader = _ReadResultsJSONFile
    else:
      # The directory is generated using autotest.
      keyval_path = os.path.join(dir_, rundir, _RESULTS_KEYVAL)
      reader = _ReadKeyvalFile

    try:
      kvf = open(keyval_path)
    except IOError as e:
      print('Warning: error in reading the test result: ', e)
      continue
    reader(res_set, kvf)
  res_set.FinalizeResults()
  return res_set
