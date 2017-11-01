#!/bin/bash
# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This script with "build id" and "cts version" passed as an argument will
# fetch all .csv files in the current directory to schedule missing package
# of respective boards identified using individual .csv file name (i.e rename
# each .csv file to reflect its exact borad name by which the framework can
# identify specific board after downloading from plx dashboard)
# Copying run_missing_pck.sh at ~/chromiumos/src/scripts makes the script
# available in chroot. The chroot env is required to schedule missing test runs
# using test_that.

# Usage information
usage_info() {
  cat <<EOF
Usage:
./run_missing_pkg.sh [OPTION] <build_id> <cts_version>
Sample usage:
./run_missing_pkg.sh R64-10075.0.0 7.1_r10
EOF
}

main() {
  # Checking if mandatory arguments are provided.
  if [ $# -ne 2 ]; then
    usage_info
    exit 0
  fi

  # Reading the build number.
  BUILD=$1

  # Reading the CTS version.
  CTS_VERSION=$2

  # Extracting ANDROID_VERSION from CTS_VERSION.
  ANDROID_VERSION="${CTS_VERSION%.*}"

  # Adding PREFIX for ANDROID_VERSION
  if [ $ANDROID_VERSION == 7 ]; then
    PREFIX="cheets_CTS_N"
  else
    echo "CTS version should not be other than 7"
    exit 1
  fi

  # Iterating all csv files from the current directory.
  for file in *.csv
    do
      #Extracting BOARD name from each csv file.
      BOARD=$(echo $file | cut -d. -f1)
      echo $BOARD
      # Initialize to NULL before each csv iteration.
      PACKAGE_SYNTAX=""
      LIST_OF_PACKAGES=""
      # This skips the header of each csv file and blank lines if available.
      PROCESSED_CSV=$(cut -d, -f1,2 $file | sed 1d | sed /^$/d)
      for i in $PROCESSED_CSV
      do
        # Extracting PACKAGE name from each line from the csv file.
        PACKAGE=$(echo $i | cut -d, -f1)
        # Extracting ARCHITECTURE name from each line from the csv file.
        ARCHITECTURE=$(echo $i | cut -d, -f2 | cut -c 1-3)
        # Building PACKAGE_SYNTAX.
        PACKAGE_SYNTAX="$PREFIX.$CTS_VERSION.$ARCHITECTURE.$PACKAGE"
        LIST_OF_PACKAGES="$LIST_OF_PACKAGES $PACKAGE_SYNTAX"
      done
      test_that :lab: --max_runtime_mins 600 -b $BOARD -i \
        $BOARD-release/$BUILD -p cts $LIST_OF_PACKAGES &
      # This sleep time will make sure test_that to produce the job id during
      # exectuion followed by the former board name(echo $BORAD) one by one
      # properly on the console for respective boards.
      sleep 15
  done
}

main "$@"
