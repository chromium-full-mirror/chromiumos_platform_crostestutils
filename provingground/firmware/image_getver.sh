#!/bin/bash
#
# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Given a chrome OS bin file, extract and display the firmware version.
# Usage: $0 chromiumos_image.bin
#

CHROOT=~/chromiumos
IMG=$1

cd $CHROOT
if [ -z "$IMG" ]; then
  cros_sdk -- sudo dd if=/dev/sdd of=/tmp/chromiumos_image.bin bs=1M
  cat <<EOF | cros_sdk
  /home/$USER/trunk/src/scripts/mount_gpt_image.sh -f /tmp -i chromiumos_image.bin
  /tmp/m/usr/sbin/chromeos-firmwareupdate -V
  cat /tmp/m/etc/lsb-release
  /home/$USER/trunk/src/scripts/mount_gpt_image.sh -u --image /tmp/chromiumos_image.bin
  rm /tmp/chromiumos_image.bin
EOF
else
  cp $IMG $CHROOT/chroot/tmp
  filename=$(basename $IMG)
  cat <<EOF | cros_sdk
  /home/$USER/trunk/src/scripts/mount_gpt_image.sh -f /tmp -i $filename
  /tmp/m/usr/sbin/chromeos-firmwareupdate -V
  cat /tmp/m/etc/lsb-release
  /home/$USER/trunk/src/scripts/mount_gpt_image.sh -u --image /tmp/$filename
  rm /tmp/$filename
EOF
fi
