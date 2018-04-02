#!/bin/bash
# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This script uses "build id" and "cts version" as an argument.It
# fetches all ".csv" files in the current directory to schedule missing packages
# of respective boards identified through its file name (note: naming
# each .csv file should match standard board name by which framwork recognize
# it correctly) An example for proper board name is "veyron_tiger" instead of
# "tiger". Copy "run_missing_pkg.sh" script and all ".csv" files(Missing Tests)
# downloaded from plx dashboard to ~/chromiumos/src/scripts to make them
# available in chroot environment(cros_sdk). This script must be used only in
# chroot enviroment and make it as an executable.

# Usage information
usage_info() {
  cat <<EOF
Usage:
./run_missing_pkg.sh [build_id] [cts_version]
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

  # Reading the build id.
  BUILD=$1

  # Reading the CTS version.
  CTS_VERSION=$2

  # Extracting ANDROID_VERSION from CTS_VERSION.
  ANDROID_VERSION=${CTS_VERSION%.*}

  # Adding PREFIX for ANDROID_VERSION
  if [ $ANDROID_VERSION == 7 ]; then
    PREFIX="cheets_CTS_N"
  else
    echo "This script only works for ANDROID_VERSION 7"
    exit 1
  fi

  # Iterating all csv files from the current directory.
  # Eg:asuka.csv,banon.csv,veyron_tiger.csv etc(For board name convention
  # refer the comments in the header section)
  for file in *.csv
    do
      # Extracting BOARD name from each csv file name
      BOARD=$(echo $file | cut -d. -f1)
      echo $BOARD
      # Initialize to NULL before each csv iteration.
      PACKAGE_SYNTAX=""
      LIST_OF_PACKAGES=""
      # This skips header of each csv file and blank lines if available.
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
      # Below sleep time can be adjusted as per the user need. This
      # timer should be set in a way "test_that" should get enough
      # time to execute and produce the job id for each run before
      # moving to the next board. Proper sleep time result in
      # cleaner console message i.e Board name followed by
      # test_that syntax used and its job id sequencially.
      sleep 40
  done
}

main "$@"
