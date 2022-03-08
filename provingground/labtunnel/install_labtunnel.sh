#!/bin/bash
# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

INSTALL_DIR=~/lib/depot_tools
function print_help {
  cat <<END
Usage: install_labtunnel.sh [options]

Options:
 --dir|-d <path>    Path to directory where labtunnel is to be installed, which
                    should be in your \$PATH (default = '~/lib/depot_tools').
END
}

# Parse args
while [[ $# -gt 2 ]]; do
  case $1 in
    --dir|-d)
      INSTALL_DIR="$2"
      shift 2
      ;;
    *)
      echo "Error: Invalid option '$1'"
      print_help
      exit 1
      break
      ;;
  esac
done
if [ $# -eq 1 ]; then
  if [ "$1" == "help" ]; then
    print_help
    exit
  fi
  echo "Error: Invalid option '$1'"
  print_help
  exit 1
fi

# Resolve path of bash script
SCRIPT_DIR="$(dirname "$(realpath -e "${BASH_SOURCE[0]}")")"
SCRIPT_PATH="${SCRIPT_DIR}/labtunnel.sh"
if [ ! -f "${SCRIPT_PATH}" ]; then
  echo "Error: Failed to resolve path to ./labtunnel.sh"
  exit 1
fi

# Create a link to the bash script in the install dir
INSTALL_PATH="${INSTALL_DIR}/labtunnel"
if [ -L "${INSTALL_PATH}" ]; then
  unlink "${INSTALL_PATH}"
fi

set -e
ln -s "${SCRIPT_PATH}" "${INSTALL_PATH}"
chmod +x "${INSTALL_PATH}"

echo "Successfully installed labtunnel to '${INSTALL_PATH}'"
