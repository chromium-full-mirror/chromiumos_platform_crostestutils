// Copyright 2020 The Chromium OS Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package main

import (
	"firmware/internal/pkg/dutio"
	"fmt"
	"log"
)

// TODO(kmshelton): Move the dut definition into the dutio package and make SendSSHCommand a method on dut.
type dut struct {
	hostname     string
	phase        string
	crosVersion  string
	biosVersion  string
	ecROVersion  string
	ecRWVersion  string
	gscVersion   string
	cpuArch      string
	cpuModel     string
	cpuSpeed     string
	totalMemory  string
	memoryType   string
	mmcModel     string
	mmcFirmware  string
	nvmeModel    string
	nvmeFirmware string
	vpd          string
}

// setCPUSpeed interfaces with a DUT and sets the cpuSpeed field (the clock frequency of the central processing unit).
func (d *dut) setCPUSpeed() error {
	// TODO(kmshelton): Use dbus instead of executing commands directly on the DUT.
	// This is only a temporary command to support incremental development.
	out, err := dutio.SendSSHCommand(d.hostname, "lscpu | grep '^Model name:' | cut -d: -f2-")
	if err != nil {
		return err
	}
	// TODO(kmshelton): Add some validation on out.
	d.cpuModel = out
	return err
}

func main() {
	fmt.Println("This utility is undergoing incremental development.  Please use crostestutils/provingground/firmware/dut.sh for now.")
	// TODO(kmshelton): Expose the same functionality as crostestutils/provingground/firmware/dut.sh.
	// The functionality in dut.sh is determining properties of the DUT like various firmware versions,
	// which will be added to this utility.
	// TODO(kmshelton): Unhardcode the hostname.
	d := dut{hostname: "chromeos1-row1-rack8-host2.cros.corp.google.com"}
	err := d.setCPUSpeed()
	if err != nil {
		log.Panic(err)
	}
	fmt.Println(d)
}
