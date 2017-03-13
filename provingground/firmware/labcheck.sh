#!/bin/bash
#
# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Usage Example:
# cd ~/chromiumos; labcheck.sh chromeos1-row2-rack11-host1 buddy pool:stress3

if [ ! -d chroot ]; then
  echo "ERROR: You must run this script from your chromiumos directory."
  exit 1
fi
if [ $# != 3 ]; then
  echo "ERROR: Missing arguments"
  echo "$0 hostname board_name stress_pool_label"
  echo "Example: labcheck.sh chromeos1-row2-rack11-host1 buddy pool:stress3"
  exit 1
fi
CHROOT=$(pwd)
HOST=$1
BOARD=$2
STRESS_POOL=$3
TMPFILE=/tmp/stresslab.out

log()
{
  echo "$HOST:$BOARD:$STRESS_POOL  $*"
}

check_label()
{
  label_pat=$1

  label=$(awk '/^'"$label_pat"'/{print $1}' $TMPFILE)
  label_cnt=$(grep -c "^$label_pat" $TMPFILE)
  if [ $label_cnt -gt 1 ]; then
    log "ERROR: you have $label_cnt label ($label), expected one."
    return
  fi
  if [ $label_cnt = 0 ]; then
    log "ERROR: label $label_pat setup FAIL."
    return 
  fi
  log "INFO: label $label_pat setup OK"
}


check_labels()
{
  ./src/third_party/autotest/files/cli/atest label list -m $HOST > $TMPFILE 2>/dev//null

  check_label "$STRESS_POOL "
  check_label "board:$BOARD "
  check_label "servo "
  log "INFO: atest label list -m $HOST:"
  sed 's/^/    /g' $TMPFILE
}


check_ssh()
{
  RSA=~/.ssh/testing_rsa
  sum_value=$(sum $RSA | awk '{print $1}')
  if [ "$sum_value" -ne "30218" ]; then
    log "WARNING: your $RSA file checksum mismatch."
    log "WARNING: Please check that it is the same as $CHROOT/chromite/ssh_keys/testing_rsa"
    return
  fi
  ssh -oBatchMode=yes root@$HOST pwd > /dev/null 2>&1
  if [ $? -ne 0 ]; then
    log "ERROR: ssh setup FAILED"
    return 
  fi
  log "INFO: ssh setup OK"
}

check_rpm()
{
  cros_sdk ../third_party/autotest/files/contrib/manage_powerunit_info.py list -m $HOST > $TMPFILE
  rpm_cnt=$(grep -c . $TMPFILE)
  if [ $rpm_cnt -ne 1 ]; then
    log "ERROR: RPM setup FAIL"
    cat $TMPFILE
    return
  fi
  log "INFO: RPM setup OK"
}


check_servo()
{
  sshcmd="ssh -oBatchMode=yes"
  board=$($sshcmd root@${HOST}-servo ps -ef | grep servod  | sed 's/^.*--board //g' | awk '{print $1}' | sort -u)
  if [ "$board" != "$BOARD" ]; then
    log "ERROR: servo ${HOST}-servo setup FAIL (expects $BOARD, got $board)"
    return
  fi
  log "INFO: servo ${HOST}-servo setup OK"
}
 

check_host()
{
  ssh -oBatchMode=yes root@$HOST pwd > /dev/null 2>&1
  if [ $? -ne 0 ]; then
    log "ERROR: $HOST connection setup FAIL"
    return
  fi
  log "INFO: $HOST connection setup OK"

}


if [ ! -z "$STRESS_POOL" ]; then
  check_labels
fi
check_ssh
check_rpm
check_servo
check_host

log "INFO: Auto check done"
log "INFO: Press the reverify button in http://cautotest to verify your setup."
log "INFO: Follow the 'Monitoriing your Setup' section in http://go/cassandra-lab doc."
