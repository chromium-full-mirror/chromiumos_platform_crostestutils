#!/bin/bash
# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

SCRIPT_DIR="$(dirname "$(realpath -e "${BASH_SOURCE[0]}")")"
function print_help {
  cat "${SCRIPT_DIR}/labtunnel_usage.txt"
  echo ''
  cat <<END
  For more details and examples, view the README at "${SCRIPT_DIR}/README.md".
END
}

if [ $# -lt 2 ]; then
  print_help
  exit 1
fi

# Parse args and options
START_PORT="2200"
HOST_PROXY="access@chromeos1-proxy"
HOST_DUT=""
HOST_PCAP=""
HOST_CALLBOX=""
HOST_ROUTER=""
NO_PCAP=0
TUNNEL_TYPE=""
HOST_PARAM=""
DO_NOT_OPEN_VNC=0
DO_LEASE=0
LEASE_OPTIONS=(
  "--reason=\"manual_testing\""
  "--minutes=100"
)
LEASE_RETAIN=0
SSH_OPTIONS=(
  "-o StrictHostKeyChecking=no"
  "-o ExitOnForwardFailure=yes"
  "-o UserKnownHostsFile=/dev/null"
  "-o LogLevel=ERROR"
)
BTPEER_COUNT=1
CHAMELEOND_PORT=9992
while [[ $# -gt 2 ]]; do
  case $1 in
    --help|help|-h)
      print_help
      exit
      ;;
    --port|-p)
      START_PORT="$2"
      shift 2
      ;;
    --dut)
      HOST_DUT="$2"
      HOST_PARAM="$2"
      shift 2
      ;;
    --pcap)
      HOST_PCAP="$2"
      shift 2
      ;;
    --no-pcap)
      NO_PCAP=1
      shift 1
      ;;
    --router)
      HOST_ROUTER="$2"
      shift 2
      ;;
    --callbox)
      HOST_CALLBOX="$2"
      shift 2
      ;;
    --proxy)
      HOST_PROXY="$2"
      shift 2
      ;;
    --do-not-open-vnc)
      DO_NOT_OPEN_VNC=1
      shift 1
      ;;
    --lease)
      DO_LEASE=1
      shift 1
      ;;
    --lease-retain)
      LEASE_RETAIN=1
      shift 1
      ;;
    --lease-option)
      LEASE_OPTIONS+=("$2")
      shift 2
      ;;
    --lease-options)
      IFS=' ' read -r -a LEASE_OPTIONS <<< "$2"
      shift 2
      ;;
    --ssh-option)
      SSH_OPTIONS+=("$2")
      shift 2
      ;;
    --ssh-options)
      IFS=' ' read -r -a SSH_OPTIONS <<< "$2"
      shift 2
      ;;
    --btpeer-count)
      BTPEER_COUNT="$2"
      shift 2
      ;;
    --chameleond-port)
      CHAMELEOND_PORT="$2"
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
if [ "${HOST_PARAM}" == "" ]; then
  if [ ! $# -eq 2 ]; then
    echo "Error: Invalid params"
    print_help
    exit 1
  fi
  TUNNEL_TYPE="$1"
  HOST_PARAM="$2"
else
  if [ ! $# -eq 1 ]; then
    echo "Error: Invalid params"
    print_help
    exit 1
  fi
  TUNNEL_TYPE="$1"
fi
if [ "${TUNNEL_TYPE}" == "dutvnc" ] && [ "${DO_NOT_OPEN_VNC}" -eq 0 ] \
&& ! command -v xtigervncviewer &> /dev/null; then
  cat <<END
Error: Required xtigervncviewer not found

You can install TigerVNC on gLinux with 'sudo apt install tigervnc-viewer'
END
  exit 1
fi

RE_POSITIVE_INT='^[0-9]+$'
if ! [[ "${CHAMELEOND_PORT}" =~ ${RE_POSITIVE_INT} ]] \
|| [ "${CHAMELEOND_PORT}" -le 0 ]; then
  echo "Error: --chameleond-port value must be a non-zero positive integer"
  print_help
  exit 1
fi

# Resolve undefined hosts where possible
function resolve_hostname {
  local RESOLVED_NAME="$1"
  local SUFFIX_TO_ADD="$2"

  # Convert crosfleet name to host name by removing prefix
  if [ "${RESOLVED_NAME:0:7}" = "crossk-" ]; then
    local RESOLVED_NAME=${RESOLVED_NAME:7}
  fi

  # Add suffix, keeping any existing '.cros' suffix
  if [ "${SUFFIX_TO_ADD}" !=  "" ]; then
    if [ "${RESOLVED_NAME: -5}" == ".cros" ]; then
      local RESOLVED_NAME="${RESOLVED_NAME:0:-5}${SUFFIX_TO_ADD}.cros"
    else
      local RESOLVED_NAME="${RESOLVED_NAME}${SUFFIX_TO_ADD}"
    fi
  fi

  echo -n "${RESOLVED_NAME}"
}

function resolve_host_params {
  if [ "${HOST_PARAM}" != "" ]; then
    if [ "${HOST_DUT}" == "" ]; then
      HOST_DUT=$(resolve_hostname "${HOST_PARAM}")
    fi
    if [ "${HOST_PCAP}" == "" ]; then
      HOST_PCAP=$(resolve_hostname "${HOST_DUT}" "-pcap")
    fi
    if [ "${HOST_ROUTER}" == "" ]; then
      HOST_ROUTER=$(resolve_hostname "${HOST_DUT}" "-router")
    fi
  fi
}
resolve_host_params

LEASED_DUT=""
function handle_dut_lease_start {
  if [ "${DO_LEASE}" -eq 1 ]; then
    LEASED_DUT="${HOST_PARAM}"
    echo "Leasing DUT '${LEASED_DUT}' with options '${LEASE_OPTIONS[*]}'..."
    local LEASE_OUTPUT
    LEASE_OUTPUT=$(crosfleet dut lease "${LEASE_OPTIONS[@]}" \
    --host="${LEASED_DUT}" 2>&1)
    echo "${LEASE_OUTPUT}"
    local MSG='Found 1 DUT(s) (0 busy) matching the provided DUT dimensions'
    if echo "${LEASE_OUTPUT}" | grep -q "${MSG}"; then
      echo "Successfully leased DUT '${LEASED_DUT}'"
    else
      echo "Failed to lease DUT '${LEASED_DUT}'"
      kill_children_and_exit
    fi
  fi
}
function handle_dut_lease_stop {
  if [ "${LEASED_DUT}" != "" ]; then
    if [ "${LEASE_RETAIN}" -eq 1 ]; then
      echo "Reminder: crosfleet dut '${LEASED_DUT}' is still leased"
    else
      echo "Abandoning leased bot '${LEASED_DUT}'..."
      crosfleet dut abandon "${LEASED_DUT}"
    fi
  fi
}

PIDS=()
TMUX_SESSIONS=()
function kill_children {
  echo -e "\nClosing labtunnel..."
  for SNAME in "${TMUX_SESSIONS[@]}"; do
    if tmux has-session -t "${SNAME}" 2>/dev/null; then
      echo "Closing tmux session '${SNAME}'..."
      tmux send-keys -t "${SNAME}" C-c "exit" ENTER
      sleep 1s
      tmux kill-session -t "${SNAME}" 2>/dev/null
    fi
  done
  echo -e "Killing child processes..."
  for PID in "${PIDS[@]}"; do
    if [ -d "/proc/${PID}" ]; then
      pkill --signal SIGQUIT -P "${PID}"
    fi
  done
  handle_dut_lease_stop
}
function kill_children_and_exit {
  trap - SIGINT SIGQUIT SIGHUP
  kill_children
  exit
}

TUNNEL_SUMMARY="Successfully created tunnels"
LAST_TUNNEL_ENDPOINT=""
function make_tunnel {
  PIDS+=("$$")
  local TUNNEL_NAME=$1
  local REMOTE_HOST=$2
  local LOCAL_PORT=$3
  local HOST=$4
  local REMOTE_PORT=$5
  local LOCAL_ENDPOINT="localhost:${LOCAL_PORT}"
  local REMOTE_ENDPOINT="${REMOTE_HOST}:${REMOTE_PORT}"
  local TUNNEL_DESC="${TUNNEL_NAME}: ${LOCAL_ENDPOINT} ->"
  TUNNEL_DESC="${TUNNEL_DESC} ${HOST} -> ${REMOTE_ENDPOINT}"
  echo "Creating SSH tunnel ${TUNNEL_DESC}..."
  local TUNNEL_PATH="${LOCAL_PORT}:${REMOTE_HOST}:${REMOTE_PORT}"
  ssh "${SSH_OPTIONS[@]}" -fNL "${TUNNEL_PATH}" "${HOST}"
  local ERROR_CODE=$?
  if [ ! "${ERROR_CODE}" -eq 0 ]; then
    echo "Failed to create SSH tunnel ${TUNNEL_DESC} (error=${ERROR_CODE})."
    echo "Please address the ssh error and try again."
    kill_children_and_exit
  fi
  TUNNEL_SUMMARY="${TUNNEL_SUMMARY}\n ${TUNNEL_DESC}"
  LAST_TUNNEL_ENDPOINT=${LOCAL_ENDPOINT}
}

TMUX_SESSION_NAME=""
function ssh_run_cmd {
  PIDS+=("$$")
  local HOST=$1
  local CMD=$2
  TMUX_SESSION_NAME="labtunnel_tmux_ssh_$(date +%s)"
  TMUX_SESSIONS+=("${TMUX_SESSION_NAME}")

  echo "Running '${CMD}' on '${HOST}' in local tmux session '" \
  "${TMUX_SESSION_NAME}'..."

  local SSH_CMD=("ssh" "${SSH_OPTIONS[@]}" "${HOST}")
  tmux new-session -d -s "${TMUX_SESSION_NAME}" "${SSH_CMD[@]}"
  tmux send-keys -t "${TMUX_SESSION_NAME}" "${CMD}" ENTER
  tmux send-keys -t "${TMUX_SESSION_NAME}" "exit" ENTER
}

trap kill_children_and_exit SIGINT SIGQUIT SIGHUP

case ${TUNNEL_TYPE} in
  wificell)
    handle_dut_lease_start
    make_tunnel "DUT" "localhost" "${START_PORT}" "${HOST_DUT}" 22
    DUT=${LAST_TUNNEL_ENDPOINT}
    make_tunnel "router" "localhost" $((START_PORT+1)) "${HOST_ROUTER}" 22
    ROUTER=${LAST_TUNNEL_ENDPOINT}
    if [ "${NO_PCAP}" -eq 0 ]; then
        make_tunnel "pcap" "localhost" $((START_PORT+2)) "${HOST_PCAP}" 22
        PCAP=${LAST_TUNNEL_ENDPOINT}
    fi
    echo -e "${TUNNEL_SUMMARY}"
    echo -e "\nExample tast call (in chroot):"
    if [ "${NO_PCAP}" -eq 0 ]; then
      echo "tast run -var=router=${ROUTER} -var=pcap=${PCAP} ${DUT} <test>"
    else
      echo "tast run -var=router=${ROUTER} ${DUT} <test>"
    fi
    ;;
  callbox)
    if [ "${HOST_CALLBOX}" = "" ]; then
      echo "Error: --callbox param required for callbox tunnels"
      print_help
      exit 1
    fi
    handle_dut_lease_start
    make_tunnel "DUT" "localhost" "${START_PORT}" "${HOST_DUT}" 22
    DUT=${LAST_TUNNEL_ENDPOINT}
    make_tunnel "callboxManager" "localhost" $((START_PORT+1)) \
    "${HOST_PROXY}" 5000
    CALLBOX_MANAGER=${LAST_TUNNEL_ENDPOINT}
    make_tunnel "callbox" "${HOST_CALLBOX}" 5025 "${HOST_PROXY}" 5025
    echo -e "${TUNNEL_SUMMARY}"
    echo -e "\nExample tast call (in chroot):"
    echo "tast run -var=callbox=${HOST_CALLBOX} " \
    "-var=callboxManager=${CALLBOX_MANAGER} ${DUT} <test>"
    ;;
  dut)
    handle_dut_lease_start
    make_tunnel "DUT" "localhost" "${START_PORT}" "${HOST_DUT}" 22
    DUT=${LAST_TUNNEL_ENDPOINT}
    echo -e "${TUNNEL_SUMMARY}"
    echo -e "\nExample tast call (in chroot):"
    echo "tast run ${DUT} <test>"
    ;;
  dutvnc)
    handle_dut_lease_start
    make_tunnel "DUT_VNC" "localhost" 5900 "${HOST_DUT}" 5900
    echo -e "${TUNNEL_SUMMARY}"
    echo "Starting kmsvnc on dut..."
    ssh_run_cmd "${HOST_DUT}" "kmsvnc"
    sleep 5s
    if ! tmux has-session -t "${TMUX_SESSION_NAME}" 2>/dev/null; then
      echo "Failed to start kmsvnc on dut"
      kill_children_and_exit
    fi
    if [ "${DO_NOT_OPEN_VNC}" -eq 0 ]; then
      echo "Launching TigerVNC..."
      xtigervncviewer localhost:5900 -Log "*:stderr:0" &
    else
      echo "DUT VNC available at localhost:5900"
    fi
    ;;
  btpeers)
    # Tunnel to each bluetooth peer.
    for ((i = 1; i <= "${BTPEER_COUNT}"; i++ )); do
      BT_HOST="${HOST_DUT}-btpeer${i}"
      LOCAL_BT_PORT=$(("${CHAMELEOND_PORT}" + "${i}" - 1))
      make_tunnel "BTPEER${i}-CHAMELEOND" "localhost" "${LOCAL_BT_PORT}" \
      "${BT_HOST}" "${CHAMELEOND_PORT}"
    done
    echo -e "${TUNNEL_SUMMARY}"
    ;;
  *)
    echo "Error: Invalid tunnel type '${TUNNEL_TYPE}'"
    print_help
    exit 1
    ;;
esac

echo -e "\nTo shut down tunnels and sub-processes, exit this process " \
"(pid=$$) with SIGHUP, SIGINT, or SIGQUIT"
sleep infinity
