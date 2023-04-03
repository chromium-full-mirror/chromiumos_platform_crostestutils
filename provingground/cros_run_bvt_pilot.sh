#!/bin/bash
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# TODO(b:269503867): De-shell this utility.
# This script requires that you run build_packages first.

# Special because this can only run inside the chroot.
if [ ! -r /mnt/host/source/src/scripts/common.sh ]; then
  echo "Must run within chroot" >&2
  exit 1
fi
. /mnt/host/source/src/scripts/common.sh


# Flags
DEFINE_string board "${DEFAULT_BOARD}" \
  "Target board of DUT running the tests"
DEFINE_boolean smoke "${FLAGS_FALSE}" \
  "Run a minimal set of tests for smoke"
DEFINE_boolean commit "${FLAGS_FALSE}" \
  "Run the tests required to pass the Commit Queue"
DEFINE_boolean labqual "${FLAGS_FALSE}" \
  "Run the BVT tests required for lab qualification"
DEFINE_boolean debug "${FLAGS_FALSE}" \
  "Print commands that would've been run without doing anything"

# These options only matter if we're using Servo, which only
# happens when --labqual is specified.
DEFINE_string servo_host "" \
  "When running servo tests, specifies the host running servod"
DEFINE_string servo_port "" \
  "When running servo tests, specifies the port for contacting servod"
# Free-form string to check against servod's reported servo type.
DEFINE_string servo_type "" \
  "When running servo tests, specifies the servo type"

# Parse command line; die on errors
FLAGS_HELP="usage: $(basename "$0") [flags] <hostname-or-ipaddr>"
FLAGS "${@}" || exit 1
eval set -- "${FLAGS_ARGV}"
set -e

if [ -z "${FLAGS_board}" ]; then
  die "--board required"
fi

DEBUG=
if [ "${FLAGS_debug}" -eq "${FLAGS_TRUE}" ]; then
  DEBUG="echo"
fi

if [ $# -ne 1 ]; then
  die "Must specify exactly one DUT"
fi

DUT="$1"
OPTIONS=( --board="${FLAGS_board}" )
TESTS=( suite:{labqual,bvt-{inline,cq,perbuild,tast-cq}} )
GET_SERVO_TYPE_CMD=( "dut-control" "--value_only" )

SUITE_CHECK=0
if [ "${FLAGS_smoke}" -eq "${FLAGS_TRUE}" ]; then
  SUITE_CHECK=$(( SUITE_CHECK + 1 ))
  TESTS=( suite:bvt-inline )
fi
if [ "${FLAGS_commit}" -eq "${FLAGS_TRUE}" ]; then
  SUITE_CHECK=$(( SUITE_CHECK + 1 ))
  TESTS=( suite:bvt-{inline,cq,tast-cq} )
fi
if [ "${FLAGS_labqual}" -eq "${FLAGS_TRUE}" ]; then
  SUITE_CHECK=$(( SUITE_CHECK + 1 ))
  TESTS=( suite:labqual)

  # Handle Servo options for the lab qualification tests.
  if [ -z "${FLAGS_servo_type}" ]; then
    die "servo type must be specified for labquals to prevent false positives"
  fi
  if [ -n "${FLAGS_servo_host}" ]; then
    SERVO_ARGS="--args=servo_host=${FLAGS_servo_host}"
    if [ -n "${FLAGS_servo_port}" ]; then
      SERVO_ARGS="${SERVO_ARGS} servo_port=${FLAGS_servo_port}"
    fi
    OPTIONS+=( "${SERVO_ARGS}" )
  elif [ -n "${FLAGS_servo_port}" ]; then
    OPTIONS+=( "--args=servo_port=${FLAGS_servo_port}" )
  fi

  if [ -n "${FLAGS_servo_host}" ]; then
    GET_SERVO_TYPE_CMD+=( "--host=${FLAGS_servo_host}" )
  fi
  if [ -n "${FLAGS_servo_port}" ]; then
    GET_SERVO_TYPE_CMD+=( "--port=${FLAGS_servo_port}" )
  fi
  GET_SERVO_TYPE_CMD+=( "servo_type" )

  DETECTED_SERVO_TYPE=""
  if [ -n "${DEBUG}" ]; then
    echo "${GET_SERVO_TYPE_CMD[@]}"
  else
    DETECTED_SERVO_TYPE=$("${GET_SERVO_TYPE_CMD[@]}")
  fi
  if [ -z "${DEBUG}" ]; then
    if [ "${DETECTED_SERVO_TYPE}" != "${FLAGS_servo_type}" ]; then
      die "detected servo type does not match expected servo type"
    fi
  fi
fi

if [ "${SUITE_CHECK}" -gt 1 ]; then
  die "can specify at most one of --smoke --commit or --labqual"
fi

${DEBUG} test_that "${OPTIONS[@]}" "${DUT}" "${TESTS[@]}"
AUTOTEST_STATUS=$?

TAST_STATUS=0
if [ "${FLAGS_labqual}" -eq "${FLAGS_TRUE}" ]; then
  # Run a subset of Tast tests for qualifying a model before lab deployment.
  ${DEBUG} tast -verbose run -build=false "${DUT}" '("group:labqual")'
  TAST_STATUS=$?
fi

if [ "${AUTOTEST_STATUS}" -ne 0 ] || [ "${TAST_STATUS}" -ne 0 ]; then
  die "Autotest exited with ${AUTOTEST_STATUS}; Tast exited with ${TAST_STATUS}"
fi
