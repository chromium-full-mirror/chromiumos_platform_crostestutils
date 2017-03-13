#!/bin/bash
#
# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Usage: dut.sh DUT_IP
#
cat <<EOF | ssh root@$1
echo -n "Type of hardware  : "
dut_type=\$(grep '^CHROMEOS_RELEASE_BOARD=' /etc/lsb-release | cut -d= -f2)
echo \$dut_type
echo    'Device Stage      : {***Example: EVT, DVT, PVT...***}'

echo -n "Chrome OS Version : "
grep '^CHROMEOS_RELEASE_DESCRIPTION=' /etc/lsb-release | cut -d= -f2

echo -n "BIOS VERSION      : "
echo \$(crossystem ro_fwid) / \$(crossystem fwid)

mosys | grep -w ec > /dev/null 2>&1
if [ \$? -eq 0 ]; then
  echo -n "EC Version        : "
  echo \$(ectool version | awk '/^RO/{print \$3}') / \$(ectool version | awk '/^RW/{print \$3}')
fi

mosys | grep pd > /dev/null 2>&1
if [ \$? -eq 0 ]; then
  echo -n "PD Version        : "
  echo \$(ectool --dev=1 version | awk '/^RO/{print \$3}') / \$(ectool --dev=1 version | awk '/^RW/{print \$3}')
fi

# Other info
echo
echo 'CPU arch     :' \$(lscpu | awk '/^Architecture:/{print \$2}')
echo 'CPU model    :' \$(lscpu | grep '^Model name:' | cut -d: -f2-)
echo 'CPU speed    :' \$(lscpu | grep '^CPU max MHz:' | cut -d: -f2-)
echo 'Total Memory :' \$(grep '^MemTotal:' /proc/meminfo 2>/dev/null| cut -d: -f2-)
echo 'Memory Type  :' \$(mosys memory spd print id 2>/dev/null| cut -d'|' -f2- | sort -u)

# For device with eMMC should be mtdinfo -a (but currently don't work)
ls /sys/block/mmcblk0 > /dev/null 2>&1
if [ \$? -eq 0 ]; then
  echo 'MMC Model    :' \$(cat /sys/block/mmcblk0/device/name)
  echo 'MMC Firmware :' \$(cat /sys/block/mmcblk0/device/fwrev)
else
  hdparm -I /dev/sda \
    | awk '/Model Number:/     {print "SSD Model    :", substr(\$0, index(\$0,\$3))}
           /Firmware Revision:/{print "SSD Firmware :", substr(\$0, index(\$0, \$3))}'
fi

# VPD
echo
echo VPD info:
vpd -l \
  | sed 's/"//g
         /DO_NOT_SHARE/d
         s/^/  /g'

EOF
