#!/bin/sh
# Copyright 2018 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This module runs at system startup on Chromium OS test images. It runs through
# a set of hooks to keep a DUT from being bricked without manual intervention.
# Example hook:
#   Check to see if ethernet is connected. If its not, unload and reload the
#   ethernet driver.

LOG_DIR=/var/log/recover_duts
LOG_FILE="${LOG_DIR}/recover_duts.log"
LONG_REBOOT_DELAY=90
SLEEP_DELAY=60

_log() {
  local prio="$1"
  local msg="$2"

  local ts="$(date +"%F %T,%N" | cut -b -23)"
  echo "${ts} - ${prio} - ${msg}" >> "${LOG_FILE}"
}

log_dbg() {
  local msg="$1"

  _log DEBUG "${msg}"
}

log_err() {
  local msg="$1"

  _log ERROR "${msg}"
}

main() {
  local hooks_dir="$(dirname "$0")/hooks"
  local script output ret

  if [ $# -ne 0 ]; then
    echo "Usage: $(basename "$0")" >&2
    exit 1
  fi

  mkdir -p "${LOG_DIR}"

  # Additional sleep as networking not be up in the case of a long reboot.
  sleep "${LONG_REBOOT_DELAY}"

  while true; do
    log_dbg "starting loop"

    for script in "${hooks_dir}"/*.hook; do
      log_dbg "Running hook: ${script}"

      output="$("${script}" 2>&1)"
      ret="$?"
      if [ "${ret}" = "0" ]; then
        if [ -z "${output}" ]; then
          log_dbg "Running of ${script} succeeded"
        else
          log_dbg "Running of ${script} succeeded with output: ${output}"
        fi
      else
        if [ -z "${output}" ]; then
          log_err "Running of ${script} failed with no output (exit status: ${ret})"
        else
          log_err "Running of ${script} failed with output (exit status: ${ret}): ${output}"
        fi
      fi
    done

    sleep "${SLEEP_DELAY}"
  done
}

main "$@"
