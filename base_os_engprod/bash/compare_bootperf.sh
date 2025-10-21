#!/bin/bash
#
# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This script compares two "cbmem -t" output files and points out stages
# during boot that differ by more than the passed in delta number of uSeconds,
# A delta of 10000 is a good starting point

# Check for the correct number of arguments
if [ "$#" -lt 3 ]; then
  echo "Usage: compare_bootperf.sh <input_file1> <input_file2> <max_delta>"
  echo "  <input_file1>: Path to the first input file."
  echo "  <input_file2>: Path to the second input file."
  echo "  <max_delta>: The maximum absolute delta in microseconds"
  echo "    between the boot times of the two files allowed before"
  echo "    discrepency is logged."
  echo ""
  echo "Example: compare_bootperf.sh last_qual_cbmem_output.txt"
  echo "    this_qual_cbmem_output.txt 10000"
  echo "  This example command will display any stages between the two"
  echo "  quals that differ by more than 10 miliseconds."
  exit 1
fi

file1="$1"
file2="$2"
max_delta_threshold="$3"

# Validate max_delta_threshold is a positive integer
if ! [[ "${max_delta_threshold}" =~ ^[0-9]+$ ]] || \
   [ "${max_delta_threshold}" -lt 0 ]; then
  echo "Error: <max_delta> must be a non-negative integer."
  exit 1
fi

# Check if both input files exist
if [ ! -f "${file1}" ]; then
  echo "Error: File '${file1}' not found."
  exit 1
fi

if [ ! -f "${file2}" ]; then
  echo "Error: File '${file2}' not found."
  exit 1
fi

echo "Comparing bootperf from 'cbmem -t' output files:"
echo "File 1: ${file1}"
echo "File 2: ${file2}"
echo "Filter for deltas >= ${max_delta_threshold} uS"
echo "---------------------------------------------------"

# Use grep to filter each file, ensuring only lines with timestamps are
# read. This prevents the loop from getting out of sync if there are
# differing header/footer lines.
while IFS= read -r line1 <&3 && IFS= read -r line2 <&4; do
  # First, check that we are comparing the same boot stages.
  # Use sed to remove both timestamps from the end of the line for a more
  # reliable comparison of the stage description.
  stage1=$(echo "${line1}" | \
    sed -E 's/ +[0-9,]+ +\([0-9,]+\) *$//')
  stage2=$(echo "${line2}" | \
    sed -E 's/ +[0-9,]+ +\([0-9,]+\) *$//')

  echo_warning=0
  if [ "${stage1}" != "${stage2}" ]; then
    if ! echo "${stage1}" | grep "device enumeration" > /dev/null; then
      echo "Error: Mismatched boot stages detected."
      echo "Unable to compare ${file1} and ${file2}."
      echo "Difference found at:"
      echo "${file1}: ${line1}"
      echo "${file2}: ${line2}"
      exit 1
    else
      echo_warning=1
    fi
  fi

  num1=""
  num2=""

  # Extract number from line1
  if [[ ${line1} =~ \(([0-9,]+)\)[[:space:]]*$ ]]; then
    num1=$(echo "${BASH_REMATCH[1]}" | tr -d ',')
  fi

  # Extract number from line2
  if [[ ${line2} =~ \(([0-9,]+)\)[[:space:]]*$ ]]; then
    num2=$(echo "${BASH_REMATCH[1]}" | tr -d ',')
  fi

  # Perform comparison if both numbers were found
  if [[ -n "${num1}" ]] && [[ -n "${num2}" ]]; then
    delta=$((num2 - num1))
    absolute_delta=${delta#-}

    # Check if the absolute delta meets the threshold
    if (( absolute_delta >= max_delta_threshold )); then
      if [ "${delta}" -eq "${absolute_delta}" ]; then
        speedStr="SLOWER"
      else
        speedStr="FASTER"
      fi

      if [ "${echo_warning}" -eq 1 ]; then
        echo "NOTE: The following stage strings are different:"
      fi

      echo "File 1: ${line1}"
      echo "File 2: ${line2}"
      echo "File 2 Delta : ${absolute_delta} uS ${speedStr}"
      echo ""
    fi
  fi

done 3< <(grep -E '\([0-9,]+\) *$' "${file1}") \
     4< <(grep -E '\([0-9,]+\) *$' "${file2}")
