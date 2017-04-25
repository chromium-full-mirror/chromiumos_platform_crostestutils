#!/bin/bash
#
# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Manage ssh tunnels to local mobalabs used for
# firmware testing.

MOBLAB1="${MOBLAB1:-100.107.195.217}"
MOBLAB2="${MOBLAB2:-100.107.195.212}"
MOBLAB3="${MOBLAB3:-100.107.195.220}"
MOBLAB4="${MOBLAB4:-100.107.195.213}"
MOBLAB5="${MOBLAB5:-100.107.195.219}"
MOBLAB6="${MOBLAB6:-100.107.195.211}"
MOBLAB7="${MOBLAB7:-100.107.195.215}"

declare -A MOBLABS=(
["moblab1"]=${MOBLAB1}
["moblab2"]=${MOBLAB2}
["moblab3"]=${MOBLAB3}
["moblab4"]=${MOBLAB4}
["moblab5"]=${MOBLAB5}
["moblab6"]=${MOBLAB6}
["moblab7"]=${MOBLAB7})

BASE_PORT=908
BASE_ADMIN_PORT=999
MONITOR_PORT=0
CLOSE=0
OPEN=0
STATUS=0

SOCKET_DIR="${HOME}/.ssh/connections"

function create_tunnel() {
  local local_port=$1
  local dest_port=$2
  local sock_name="moblab-sock-$local_port-$dest_port"
  local sock_path="$SOCKET_DIR/$sock_name"
  local tunnel_options="-M -S $sock_path -fNT -o ExitOnForwardFailure=yes -L"
  local user="moblab@$3"

  local cmd="ssh $tunnel_options $local_port:localhost:$dest_port $user"

  echo "Creating tunnel with: $cmd"
  eval "$cmd"
}

function close_tunnel() {
  local sock_name="moblab-sock-$1-$2"
  local user="moblab@$3"
  local cmd="ssh -S $SOCKET_DIR/$sock_name -O exit $user"

  echo "Closing tunnel with: $cmd"
  $cmd
}

function check_tunnel() {
  local sock_name="moblab-sock-$1-$2"
  local user="moblab@$3"
  local cmd="ssh -S $SOCKET_DIR/$sock_name -O check $user"

  echo "Checking tunnel with: $cmd"
  $cmd
}

function start() {
  local mobs=()

  mkdir -p "$SOCKET_DIR"

  if [[ -z "$1" ]] || [[ "$1" == "all" ]]; then
    for i in $(eval echo {1..${#MOBLABS[@]}}); do
      mobs+=("moblab$i")
    done
  else
    mobs+=("$@")
  fi

  if [[ "${OPEN}" -ne 0 ]]; then
    echo "Creating tunnels for ${mobs[*]}"
    for moblab in "${mobs[@]}"; do
      index=${moblab: -1}
      create_tunnel "$BASE_PORT$index" 80 "${MOBLABS[$moblab]}"
      if [[ "${MONITOR_PORT}" -ne 0 ]]; then
        create_tunnel "$BASE_ADMIN_PORT$index" 9991 "${MOBLABS[$moblab]}"
      fi
    done
  elif [[ "${CLOSE}" -ne 0 ]]; then
    echo "Closing tunnels for ${mobs[*]}"
    for moblab in "${mobs[@]}"; do
      index=${moblab: -1}
      close_tunnel "$BASE_PORT$index" 80 "${MOBLABS[$moblab]}"
      close_tunnel "$BASE_ADMIN_PORT$index" 9991 "${MOBLABS[$moblab]}"
    done
  elif [[ "${STATUS}" -ne 0 ]]; then
    echo "Checking tunnels for ${mobs[*]}"
    for moblab in "${mobs[@]}"; do
      index=${moblab: -1}
      echo "$moblab UI Tunnel http://localhost:$BASE_PORT$index to ${MOBLABS[$moblab]}"
      check_tunnel "$BASE_PORT$index" 80 "${MOBLABS[$moblab]}"
      echo "$moblab Admin Tunnel http://localhost:$BASE_ADMIN_PORT$index to ${MOBLABS[$moblab]}"
      check_tunnel "$BASE_ADMIN_PORT$index" 9991 "${MOBLABS[$moblab]}"
      echo
    done
    if [[ "${STATUS}" -eq 2 ]]; then
      # Pick only the first host in case user enter more then one.
      set -- $mobs
      m=$1
      echo Connecting to $m with IP ${MOBLABS[$m]}
      ssh root@${MOBLABS[$m]}
    fi
  else
    usage
  fi
}

function usage() {
  echo "$0 Usage:

  $0 [-a|-c|-h|-o|-s|] <host1> <host2> ...

  -a If port for Moblab Monitor should be used.
  -c Close active or specified tunnels.
  -h Print this.
  -o Open all tunnels or only those specified.
  -s Checks the status of each active tunnel.
  -u Connect to moblab via ssh.
  "
}

OPTIND=1

while getopts "achosu" opt; do
  case "$opt" in
    a)
      MONITOR_PORT=1
      ;;
    c)
      CLOSE=1
      ;;
    h)
      usage
      exit 0
      ;;
    o)
      OPEN=1
      ;;
    s)
      STATUS=1
      ;;
    u)
      STATUS=2
      ;;
    esac
done

shift $((OPTIND-1))

[[ "$1" = "--" ]] && shift

start "$@"
