#!/bin/bash
#
# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# script to get the DUT configureation
#


DUT_IP=$1

cat <<EOF | ssh -T root@$DUT_IP
echo -n "Type of hardware  : "
dut_type=\$(grep '^CHROMEOS_RELEASE_BOARD=' /etc/lsb-release | cut -d= -f2)
echo \$dut_type '{DEVICE STAGE: EVT, DVT, PVT...}'

echo -n "Chrome OS Version : "
grep '^CHROMEOS_RELEASE_DESCRIPTION=' /etc/lsb-release | cut -d= -f2

echo -n "BIOS Version      : "
echo \$(crossystem ro_fwid) / \$(crossystem fwid)

mosys | grep -w ec > /dev/null 2>&1
if [ \$? -eq 0 ]; then
  echo -n "EC Version        : "
  echo \$(ectool version | awk '/^RO/{print \$3}') / \
       \$(ectool version | awk '/^RW/{print \$3}')
fi

ectool --dev=1 version > /dev/null 2>&1
if [ \$? -eq 0 ]; then
  echo -n "PD Version        : "
  echo \$(ectool --dev=1 version | awk '/^RO/{print \$3}') / \
       \$(ectool --dev=1 version | awk '/^RW/{print \$3}')
fi

ls /var/cache/cr50-version > /dev/null 2>&1
if [ \$? -eq 0 ]; then
  echo -n "cr50 Version      : "
  stop trunksd >/dev/null 2>&1
  echo \$(usb_updater -fs | awk '/^RO/{print \$2}') / \
       \$(usb_updater -fs | awk '/^RW/{print \$2}')
  start trunksd >/dev/null 2>&1
fi

# Other info
echo
echo 'CPU arch     :' \$(lscpu | awk '/^Architecture:/{print \$2}')
echo 'CPU model    :' \$(lscpu | grep '^Model name:' | cut -d: -f2-)
echo 'CPU speed    :' \$(lscpu | grep '^CPU max MHz:' | cut -d: -f2-)
echo 'Total Memory :' \$(grep '^MemTotal:' /proc/meminfo 2>/dev/null \
                      | cut -d: -f2-)
echo 'Memory Type  :' \$(mosys memory spd print id 2>/dev/null \
                      | cut -d'|' -f2- | sort -u)

# For device with eMMC should be mtdinfo -a (but currently don't work)
mmcblk="\$(ls -d /sys/block/mmcblk? 2>/dev/null)"
NVME_FILE="/dev/nvme0n1"
if [ ! -z "\$mmcblk" ]; then
  echo 'MMC Model    :' \$(cat \$mmcblk/device/name)
  echo 'MMC Firmware :' \$(cat \$mmcblk/device/fwrev)
elif [ -b "\$NVME_FILE" ]; then
  echo 'NVMe Model   :' \$(smartctl -a \$NVME_FILE \
                        |grep "Model Number" | awk '{print \$3,\$4}')
  echo 'NVMe Firmware:' \$(smartctl -a \$NVME_FILE \
                        |grep "Firmware Version" | awk '{print \$3}')
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
