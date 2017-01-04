#!/bin/bash
#
# Copyright 2015 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Manage ssh tunnels to local mobalabs used for
# firmware testing.

declare -A MOBLABS=(
["moblab1"]="100.107.195.210"
["moblab2"]="100.107.195.212"
["moblab3"]="100.107.195.209"
["moblab4"]="100.107.195.217"
["moblab5"]="100.107.195.218"
["moblab6"]="100.107.195.211"
["moblab7"]="100.107.195.216")

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
    for i in {1..7}; do
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
      check_tunnel "$BASE_PORT$index" 80 "${MOBLABS[$moblab]}"
      check_tunnel "$BASE_ADMIN_PORT$index" 9991 "${MOBLABS[$moblab]}"
    done
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
  -s Checks the status of each active tunnel."
}

OPTIND=1

while getopts "achos" opt; do
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
    esac
done

shift $((OPTIND-1))

[[ "$1" = "--" ]] && shift

start "$@"




