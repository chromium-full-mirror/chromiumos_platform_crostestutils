#!/bin/bash
# Copyright 2022 The ChromiumOS Authors.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

declare -A platPaths
declare -A plat2Paths
boards=(
"brya")

###########################################################
# Get the build number of the latest relevant build.
# GLOBALS:
#  board: Board to get the build number for.
# ARGS: None
###########################################################
build_number() {
    local ps="chromeos/postsubmit/${board}-postsubmit"
    local tag="relevance:relevant"
    echo "Querying ${ps} for last relevant successful build"
    bNum=$(bb ls "${ps}" -1 -status success -t "${tag}" -json | jq '.number')
    echo "Found build number: ${bNum}"

    if [ -z "${bNum}" ]
    then
        echo "No build number found."
        exit
    fi
}

###########################################################
# Get all the files under platform and platform2 dirs.
# GLOBALS:
#   platPaths: Dictionary containing different file paths.
# ARGS:
#   path: The file path to check for.
###########################################################
plat_files() {
    path=$1
    d=$(echo "${path}" | cut -d '/' -f 3)
    if [[ ${path} == src/platform/* ]]
    then
        platPaths["${d}"]=1
    elif [[ ${path} == src/platform2/* ]]
    then
        plat2Paths["${d}"]=1
    fi
}

###########################################################
# Gets all the CPP files installed on the board.
# GLOBALS:
#   board: Board to check the installed files for.
#   bNum: Build number of board to check for.
# ARGS: None
###########################################################
cpp_files() {
    local bn="chromeos/postsubmit/${board}-postsubmit/${bNum}"
    local api="chromite.api.DependencyService/GetBuildDependencyGraph"
    local query="dependency graph calculation|call ${api}"
    resp=$(bb log "${bn}" "${query}" response | jq '.')

    echo "Dep graph section start"
    local qp=".depGraph.packageDeps[].dependencySourcePaths[].path"
    for path in $(echo "${resp}" | jq "${qp}")
    do
        # The path is of the form "src/platform2/f1.cc"
        # Edit path to remove end quotes.
        path=$(echo "${path}" | sed 's/.$//' | sed 's/^.//')
        plat_files "${path}"
    done
    echo "Dep graph section done"

    echo "SDK Dep graph section start"
    qp=".sdkDepGraph.packageDeps[].dependencySourcePaths[].path"
    for path in $(echo "${resp}" | jq "${qp}")
    do
        # The path is of the form "src/platform2/f1.cc"
        # Edit path to remove end quotes.
        path=$(echo "${path}" | sed 's/.$//' | sed 's/^.//')
        plat_files "${path}"
    done
    echo "SDK Dep graph section done"
}

for board in "${boards[@]}"
do
    echo "Getting build number for ${board}"
    build_number

    echo "Finding CPP files for ${board}"
    cpp_files

    echo "All dirs in src/platform for ${board}"
    for dir in "${!platPaths[@]}"
    do
        echo "src/platform/${dir}/"
    done

    echo "*************************************"
    echo "All dirs in src/platform2 for ${board}"
    for dir in "${!plat2Paths[@]}"
    do
        echo "src/platform2/${dir}"
    done
    echo "*************************************"
done
