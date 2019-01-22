#!/bin/bash
#
# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# TODO(someone): Obviate in favor of monitoring and alerting.

SERVO_PORTS="9901 9902 9903 9904"

# Labstations outside of the high touch lab (chromeos1) are excluded.
find_labstations() {
  atest host list --label=pool:${POOL} --parse \
  | grep chromeos1- \
  | cut -f 1 -d \| \
  | sed 's/host.*/labstation/g' \
  | sed 's/Host=//g' \
  | sort \
  | uniq \
  | xargs
}

POOL=faft-cr50
while getopts 'p:' OPTION
do
  case $OPTION in
    p) POOL="$OPTARG"
       ;;
    ?) printf "Usage: %s [-p value]\n" ${0##*/} >&2
       exit 2
       ;;
    esac
done

echo "This script asssumes many things, like that you have atest in the \
  environment that you run it, that you have cros in your DNS search path, and \
  that you have added the testing_rsa key to your ssh agent.  This is just a \
  conveience script to get lab daily analysis off the ground, feel free and \
  encouraged to extend and enhance it, but longer term it should be mostly \
  obviated by monitoring and alerting."

echo -e "\nChecking that the labstations respond to ping first, because if a \
  labstation is down: you are hosed."
LABSTATIONS="$(find_labstations)"
echo $LABSTATIONS
fping $LABSTATIONS

echo -e "\n\nLogging labstation's version, uptime, the last 10 eventlog lines, \
  and servod process state"
for STATION in $LABSTATIONS;
    do echo -e "\n\nsshing to $STATION\n"
    ssh -o StrictHostKeyChecking=no root@$STATION "grep \
      guado_labstation-release /etc/lsb-release; echo -e \"\"; uptime; \
      echo -e \"\"; mosys eventlog list | tail -n 10; echo -e \"\";"
done

echo -e "\n\nChecking for lines with ERROR in the most recent servod log (the \
  last 4 will be on the labstation, only the most recent one is checked here)."
for STATION in $GSC_LABSTATIONS;
    do echo -e "\nchecking $STATION"
    ssh -o StrictHostKeyChecking=no root@$STATION \
      "grep ERROR /var/log/servod_990*.log";
done


echo -e "\n\nLogging servo versions (there's 4 per labsation even if there \
  aren't 4 DUTs). This should excercise the servo consoles.  If you get \
  connection refused, servod has likely stopped.  If you get a timeout waiting \
  for response, the servo has likely crashed (no console response)."
for STATION in $LABSTATIONS;
    do echo -e "\nchecking $STATION"
    for PORT in $SERVO_PORTS;
        do ssh -o StrictHostKeyChecking=no root@$STATION "dut-control -p $PORT \
          servo_micro_version; dut-control -p $PORT servo_v4_version;"
    done;
done

# TODO(kmshelton): Figure out how to check if the latest build was successful
# for all models in the environment, since this is the cause of missing
# nightlies sometimes.

echo -e "\nGathering kernel and servod logs."
LOGS_DIR="$(mktemp -d)"
cd $LOGS_DIR
echo -e "\nLogs will be stored in $LOGS_DIR"
for STATION in $LABSTATIONS;
    do mkdir $LOGS_DIR/$STATION
    echo "checking $STATION"
    scp -o StrictHostKeyChecking=no root@$STATION:/var/log/messages \
      $LOGS_DIR/$STATION;
    scp -o StrictHostKeyChecking=no root@$STATION:/var/log/servo* \
      $LOGS_DIR/$STATION;
done

echo -e "\n\nChecking for the failure signature ("did not claim interface") of \
  b/110045723:"
for STATION in $LABSTATIONS;
    do grep -r "did not claim interface" $LOGS_DIR/$STATION;
done


echo -e "\n\nTarring kernel and servo logs."
TARBALL="$(mktemp)"
tar -cvf $TARBALL .
echo -e "\n\n There will be a tarball at $TARBALL.  Attach the tarball to any \
  bugs filed."

echo -e "\n\nReturning to original directory"
cd -

echo -e "\n\nLogging high level host overview. DUTs should have a status of \
  "Ready", unless there is a KI.  If a DUT is stuck in a repair state, try to \
  figure out why.  If you find yourself repeatedly checking something, extend \
  this script with what you are checking.\n"

atest host list --label=pool:${POOL} --parse \
| grep chromeos1- | cut -f 1,2,4,5,6 -d \|
