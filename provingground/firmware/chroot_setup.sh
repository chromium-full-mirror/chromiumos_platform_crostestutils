#!/bin/bash
#
# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Wrapper script to create a new chroot
#

usage()
{
cat <<EOF
  Usage: branch_setup.sh -d {DIR} -b {BRANCH_NAME} [ -s {BOARD_NAME} ]

  Example:
  To setup branch firmware-tidus-6301.109.B on /disk2 and build board tidus :
    ./chroot_setup.sh -d /disk2/firmware-tidus-6301.109.B -b firmware-tidus-6301.109.B -s tidus

  To setup at head on /disk2 and build board tidus :
    ./chroot_setup.sh -d /disk2/chromiumos -s tidus

  To cleanup branch created in /disk2/chromiumos:
    cd /disk2/chromiumos
    cros_sdk --delete
    sudo rm -rf /disk2/chromiumos
EOF
}

DIR=""
BRANCH=""
BOARD=""
while getopts d:b:s: opt
do
  case "$opt" in
    d) DIR=$2; shift 2;;
    b) BRANCH=$2; shift 2;;
    s) BOARD=$2; shift 2;;
    *) usage; exit 1;;
  esac
done
if [ -z "$DIR" ]; then
  echo Missing -d option
  usage
  exit 1
fi

# Print each command as they executed
set -x
# Script exit on any command exit with non zero status
set -e

BRANCH_OPT=""
if [ "$BRANCH" != "" ]; then
  BRANCH_OPT="-b $BRANCH"
fi

mkdir $DIR
cd $DIR

date
repo init \
  -u https://chrome-internal.googlesource.com/chromeos/manifest-internal.git \
  $BRANCH_OPT \
  --repo-url=https://chromium.googlesource.com/external/repo.git \
  > repo_init.out 2>&1

date
repo sync > repo_sync.out 2>&1

date
cros_sdk -- exit > cros_sdk.out 2>&1

# personalize shell
cat <<EOF >> $DIR/chroot/home/$USER/.bash_profile
export PS1='${DIR}:\W\$(__git_ps1 "(%s)") \u \$ '
# use the right editor
export EDITOR=vi
# do not clear screen on exit
export LESS=”-XF”
# useful aliases
alias ls='ls -CF'
alias ll='ls -l'
alias l.='ls -dl .??*'
alias h='history'
alias rm='rm -i'
alias is='ps axuwwww | grep'
EOF

if [ -z "$BOARD" ]; then
  exit 0
fi

date
cros_sdk -- ./setup_board --board=$BOARD > setu_board.out 2>&1

## date
# cros_sdk -- emerge-${board_name} libchrome > emerge_libchrome.out 2>&1

date
cros_sdk -- ./build_packages --board=$BOARD > build_packages.out 2>&1

date
exit 0
