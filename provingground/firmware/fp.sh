#!/bin/bash
#
# Copyright 2016 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Script to upload a single file to fireplace.
#

if [ $# -lt 2 ]; then
  cat <<EOF
Usage: $0 UPLOAD BUG [ BUGTYPE ]
UPLOAD can be one of:
  file - will upload unalter
  directory - will tar gz the directory before upload
  IP address - remote execute generate log and upload
BUG is the bug number associated with the content of UPLOAD.
BUGTYPE is optional upload to https://pantheon.corp.google.com/storage/browser/chromiumos-test-logs/bugfiles/BUGTYPE:
  crosp - default upload location crosp
  cros - upload to cros
EOF
  exit 1
fi
# will auto tar.gz if UPLOAD is a directory.
UPLOAD=$1
BUG=$2
# cros or crosp
TRACKER=$3
if [ "$TRACKER" = "" ]; then
  TRACKER=crosp
fi
if [[ "$UPLOAD" =~ ^[\.0-9]+$ ]]; then
  ISIP=1
fi

TMPDIR=${TMPDIR:-/tmp}
ZFILE=""

run()
{
  cmd="$@"
  echo
  echo Execute $cmd
  $cmd
}

GSUTIL=$(which gsutil)
if [ $? -ne 0 ]; then
  echo \"which gsutil\" return nothing.
  echo Please update PATH environment variable so that gsutil can be located.
  exit 1
fi
GSPATH="gs://chromiumos-test-logs/bugfiles/$TRACKER/$BUG"
PANTHEON="https://pantheon.corp.google.com"
MANUAL_PATH="$PANTHEON/storage/browser/chromiumos-test-logs/bugfiles/$TRACKER"

#echo "Check to see if gsutil needs updating (answwer y when prompt)."
#gsutil update

# remote generate log
if [ $ISIP ]; then
  genlog=$TMPDIR/genlog.out
  echo Generate logs from IP $UPLOAD
  ssh root@$UPLOAD generate_logs > $genlog 2>&1
  rmt_gz=$(awk '/^Log files are available/ {print $NF}' $genlog)
  rmt_file=$TMPDIR/$(basename $rmt_gz)
  scp root@$UPLOAD:$rmt_gz $rmt_file
  UPLOAD=$rmt_file
  echo Logs generated $UPLOAD
fi

# zip up directory before upload
if [ -d $UPLOAD ]; then
  ZFILE=$TMPDIR/$(basename $UPLOAD).tar.gz
  tar cfz $ZFILE $UPLOAD
  UPLOAD=$ZFILE
fi

# Create directory and upload $UPLOAD
cmd="$GSUTIL -m cp $UPLOAD $GSPATH/"
run "$cmd"
if [ $? -ne 0 ]; then
  echo Execute $cmd failed.
  echo You can manually upload via $MANUAL_PATH
  exit 1
fi

# Enable share publicly
ufilename=$(basename $UPLOAD)
cmd="$GSUTIL -m acl ch -u AllUsers:R $GSPATH/$ufilename"
run "$cmd"
if [ $? -ne 0 ]; then
  echo Execute $cmd failed.
  echo You can manually enable share publicly via $MANUAL_PATH/$BUG
  exit 1
fi

# Check perm is set correctly.
cmd="$GSUTIL acl get $GSPATH/$ufilename"
$cmd | grep allUsers > /dev/null
if [ $? -ne 0 ] ; then
  echo Execute $cmd failed.
  echo Failed to enable Shared Publicly.
  echo You should check perm is set correctly via $MANUAL_PATH/$BUG
  exit 1
fi

# Check share link and print.
publicURL="https://storage.googleapis.com/chromiumos-test-logs/bugfiles"
publiclink=$publicURL/$TRACKER/$BUG/$ufilename
wget -o /dev/null $publiclink
if [ $? -ne 0 ]; then
  echo Execute wget -o /dev/null $publiclink failed.
  echo Failed to retrive file from $publiclink.
  echo You can manually retrive public link from $MANUAL_PATH/$BUG
  exit 1
fi

echo
echo Upload $UPLOAD completed.
echo Check upload status:
echo $MANUAL_PATH/$BUG
echo
echo Public link:
echo $publiclink

# Cleanuup
if [ ! -z "$ZFILE" ]; then
  rm $ZFILE
fi
exit 0
