#!/bin/bash
# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# This script downloads the Android-cts suite from the below website:
# https://source.android.com/compatibility/cts/downloads.
# The downloaded zip file is unzipped and placed according to the versioning.

# Usage information to be displayed.
usage_info() {
  cat <<EOF
Usage:
./cts_download.sh --download_path <path> --cts_version <cts_version>
Sample usage:
./cts_download.sh --download_path ~/Desktop --cts_version 7.1_r6
EOF
}

main() {
  # Display the help information if the parameter is -h or --help.
  if [[ $1 == "-h" || $1 == "--help" ]]; then
    usage_info
    exit 0
  fi

  # Checking if all the #4 parameters are provided.
  if [[ $# -ne 4 ]]; then
    usage_info
    exit 0
  fi

  # Reading the Download Path.
  DOWNLOAD_PATH=$2

  # Reading the CTS Version.
  CTS_VERSION=$4

  readonly CTS_FOLDER="android-cts"

  # Verifying the Download Path.
  if [[ ! -d "${DOWNLOAD_PATH}" ]]; then
    echo The Download path provided is invalid
    exit 1
  fi

  # Verifying the CTS VERSION format provided.
  if echo "${CTS_VERSION}" | \
    egrep -i -v -q '^[0-9]+.+[0-9]+_+[r]+[[0-9]|[1-9][0-9]$'; then
    cat <<EOF
    Specified CTS Version format is mismatched
    Sample CTS Version Format is 7.1_r6
EOF
  exit 1
  fi

  # Extracting the Android version from CTS version.
  ANDROID_VERSION="${CTS_VERSION%.*}"

  # Creating Folders according to the Android version.
  # "M" for 6 (Marshmallow).
  # "N" for 7 (Nougat).
  # "O" for 8 (Yet to be named).

  declare -A MAPPING=(
    [6]="M"
    [7]="N"
    [8]="O"
  )
  ANDROID_VERSION_NAME=${MAPPING[${ANDROID_VERSION}]}
  if [[ -z "${ANDROID_VERSION_NAME}" ]]; then
    echo "CTS version shall start with 6, 7 or 8"
    exit 1
  fi

  # Creating a temp directory to download the android file.
  mkdir -p tmp
  # Download, unzip and move to the CTS file to the provided location.
  for ABI in x86 arm; do
    if [[ "${ABI}" = "x86" ]]; then
      ANDROID_FILE=android-cts-"${CTS_VERSION}"-linux_x86-x86.zip
    elif [[ "${ABI}" = "arm" ]]; then
      ANDROID_FILE=android-cts-"${CTS_VERSION}"-linux_x86-arm.zip
    fi
    # Downloading the zipped Android Test Suite from the URL:
    # https://source.android.com/compatibility/cts/downloads.
    if wget  "https://dl.google.com/dl/android/cts/"$ANDROID_FILE \
      -P tmp/ ; then
      # Clearing the previous unzip file.
      rm -rf "${CTS_FOLDER}"
      # Unzipping the Android version.
      unzip tmp/"${ANDROID_FILE}"
      # Creating directory for x86.
      mkdir -p \
      "${DOWNLOAD_PATH}"/CTS/"${ANDROID_VERSION_NAME}"/"${CTS_VERSION}"/"${ABI}"
      # Moving android-cts folder to x86 hierarchy.
      mv -b android-cts \
      "${DOWNLOAD_PATH}"/CTS/"${ANDROID_VERSION_NAME}"/"${CTS_VERSION}"/"${ABI}"
      # Clearing the previous downloaded ZIP file.
      rm tmp/android*.zip*
    else
      # URL not found.
      echo Requested CTS verison does not exists @\
      https://source.android.com/compatibility/cts/downloads
      exit 1
    fi
  done
  echo "The android-cts files are downloaded successfully to "\
  "${DOWNLOAD_PATH}"/CTS/"${ANDROID_VERSION_NAME}"/"${CTS_VERSION}"
}
main "$@"
