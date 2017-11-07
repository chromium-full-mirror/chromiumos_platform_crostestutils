#!/bin/bash
# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# This script downloads the Android-cts and Android-cts-verifier suites
# from @ https://source.android.com/compatibility/cts/downloads.
# The downloaded zip file is unzipped and placed according to the versioning.
# Usage information to be displayed.
usage_info() {
  cat <<EOF
Usage:
./cts_download.sh [OPTION] --path <path> --version <cts_version>
Positions           (1)     (2)    (3)      (4)        (5)

Sample usage:
./cts_download.sh [OPTION] --path ~/Desktop --version 7.1_r6

[OPTION]
Please provide one of them.
    -v,          to download only Verifier suites
    -m,          to download only Manual Test suites
    -vm,-mv      to download both Manual and Verifier Test suites
EOF
}

Download_Suite()
{
  # Downloading the Zipped Android File from the URL:
  # https://source.android.com/compatibility/cts/downloads
  Download_Url="https://dl.google.com/dl/android/cts/$ANDROID_FILE"
  if wget $Download_Url -P tmp/ ; then
    # Clearing the previous unzip file.
    rm -rf "${CTS_Folder}"
    # Unzipping the Android version.
    unzip "tmp/$ANDROID_FILE"
    # Creating directory for x86
    DDIR="$DOWNLOAD_PATH/CTS"
    DDIR="$DDIR/$ANDROID_VERSION_NAME/$CTS_VERSION"
    DDIR="$DDIR/$FOLDER_NAME/$ABI"
    mkdir -p $DDIR
    mv -b $CTS_Folder $DDIR
    rm tmp/android*.zip*
  else
    echo "Requested CTS verison does not exists @"
    echo "https://source.android.com/compatibility/cts/downloads."
    exit 0
  fi
}
main() {

  # Checking if all the #5 parameters are provided.
    if [[ $# -ne 5 ]]; then
      usage_info
      exit 0
    fi

  # Checking if the second parameter is "--path".
    if [[ $2 != "--path" ]]; then
      echo "Second parameter should be --path"
      usage_info
      exit 0
    fi

  # Checking if the 4th paramter is "--version".
    if [[ $4 != "--version" ]]; then
      echo "Fourth Parameter should be --version"
      usage_info
      exit 0
    fi


  # Reading the OPTION.
  OPTION="$1"


  # Reading the Download Path.
  DOWNLOAD_PATH="$3"

  # Reading the CTS Version.
  CTS_VERSION="$5"

  # Verifying the Download Path.
  if [[ ! -d "$DOWNLOAD_PATH" ]]; then
    echo "The Download path provided is invalid"
    exit 1
  fi

  # Verifying the CTS VERSION format provided.
  CTS_VERSION_FORMAT='^[0-9]+.+[0-9]+_+[r]+[[0-9]|[1-9][0-9]$'
  if egrep -i -q -v $CTS_VERSION_FORMAT <<<$CTS_VERSION; then
    cat <<EOF
    Specified CTS Version format is mismatched.
    Sample CTS Version Format is 7.1_r6.
EOF
    exit 1
  fi

  # Extracting the Android version from CTS version.
  ANDROID_VERSION="${CTS_VERSION%.*}"

  # Creating Folders according to the Android version.
  # "N" for 7 (Nougat).
  # "O" for 8 (Yet to be named).
  declare -A MAPPING=(
    [7]="N"
    [8]="O"
  )

  ANDROID_VERSION_NAME=${MAPPING[$ANDROID_VERSION]}
  if [[ -z "$ANDROID_VERSION_NAME" ]]; then
    echo "CTS version shall start with 7,8 and so on.."
    exit 1
  fi

  # Creating a temp directory to download the android file.
  mkdir -p tmp

  # Checking if the Verifier OPTION is submitted
  # If yes, setting Verifier_Tests flag.
  if  [ "${OPTION:1:1}" = "v" ] || [ "${OPTION:2:2}" = "v" ]; then
    Verifier_Tests="SET"
  fi

  # Checking if the Manual Suite OPTION is submitted
  # If yes, setting Manual_Tests flag.
  if  [ "${OPTION:1:1}" = "m" ] || [ "${OPTION:2:2}" = "m" ]; then
    Manual_Tests="SET"
  fi

  readonly x86_folder="linux_x86-x86"
  readonly arm_folder="linux_x86-arm"

  # If the Verifier OPTION is provided, Download the Verifier Tests Suite
  if [ "$Verifier_Tests" ]; then
    CTS_Folder="android-cts-verifier"
    # Download, unzip and move the Verifier Tests suite to the path
    for ABI in x86 arm; do
      if    [ "$ABI" = "x86" ]; then
        ANDROID_FILE="android-cts-verifier-${CTS_VERSION}-${x86_folder}.zip"
      elif  [ "$ABI" = "arm" ]; then
        ANDROID_FILE="android-cts-verifier-${CTS_VERSION}-${arm_folder}.zip"
      fi
      FOLDER_NAME="Verifier_Tests"
      Download_Suite
    done
  fi

  # If the Manual OPTION is provided, Download the Manual Tests Suite
  if [ "$Manual_Tests" ]; then
    # Download, unzip and move the Manual Tests suite to the path
    CTS_Folder="android-cts"
    for ABI in x86 arm; do
      if    [ "$ABI" = "x86" ]; then
        ANDROID_FILE="android-cts-${CTS_VERSION}-${x86_folder}.zip"
      elif  [ "$ABI" = "arm" ]; then
        ANDROID_FILE="android-cts-${CTS_VERSION}-${arm_folder}.zip"
      fi
      FOLDER_NAME="Manual_Tests"
      Download_Suite
    done
  fi

  echo "The cts files are loaded successfully to "\
  "$DOWNLOAD_PATH/CTS/$ANDROID_VERSION_NAME/$CTS_VERSION"
}
main "$@"
