// Copyright 2020 The Chromium OS Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package main

import (
	"firmware/internal/pkg/dutio"
	"fmt"
)

// TODO(kmshelton): Move the dut definition into the dutio package and make SendSSHCommand a method on dut.
type dut struct {
	hostname            string
	model               string
	phase               string
	crOSVersion         string
	biosVersion         string
	ecROVersion         string
	ecRWVersion         string
	gscVersion          string
	cpuArch             string
	cpuModel            string
	cpuSpeed            string
	totalMemory         string
	memoryType          string
	mmcModel            string
	mmcFirmwareVersion  string
	nvmeModel           string
	nvmeFirmwareVersion string
	vpd                 string
}

// setModel interfaces with a DUT and sets the model field (the DUT's market identifier).
func (d *dut) setModel() error {
	// TODO(kmshelton): Here and elsewhere: use dbus instead of executing commands directly
	// on the DUT (by exposing such functionality in dutio).
	out, err := dutio.SendSSHCommand(d.hostname, "cros_config / name")
	if err != nil {
		return err
	}
	// TODO(kmshelton): Add some validation on out (here and elsewhere).
	d.model = out
	return nil
}

// setPhase interfaces with a DUT and sets the phase field (the DUT's hardware stage).
func (d *dut) setPhase() error {
	// Phase is not implemented in dut.sh (which this utility replaces), likely because
	// getting phase involves interfacing with the HWID database.
	// TODO(b:150699151): Implement this setter (interface with the HWID database).
	d.phase = ""
	return nil
}

// setCrOSVersion interfaces with a DUT and sets the crOSVersion field (the DUT's version of ChromeOS).
func (d *dut) setCrOSVersion() error {
	out, err := dutio.SendSSHCommand(d.hostname, "grep '^CHROMEOS_RELEASE_DESCRIPTION=' /etc/lsb-release | cut -d= -f2")
	if err != nil {
		return err
	}
	d.crOSVersion = out
	return nil
}

// setBIOSVersion interfaces with a DUT and sets the biosVersion field (the DUT's application processor firmware version).
func (d *dut) setBIOSVersion() error {
	out, err := dutio.SendSSHCommand(d.hostname, "echo $(crossystem ro_fwid) / $(crossystem fwid)")
	if err != nil {
		return err
	}
	d.biosVersion = out
	return nil
}

// setECROVersion interfaces with a DUT and sets the ecROVersion field (the version of the DUT's read-only copy of the primary
// embedded controller's firmware version).
func (d *dut) setECROVersion() error {
	out, err := dutio.SendSSHCommand(d.hostname, "ectool version | awk '/^RO/{print $3}'")
	if err != nil {
		return err
	}
	d.ecROVersion = out
	return nil
}

// setECRWVersion interfaces with a DUT and sets the ecRWVersion field (the version of the DUT's read-write copy of the primary
// embedded controller's firmware version).
func (d *dut) setECRWVersion() error {
	out, err := dutio.SendSSHCommand(d.hostname, "ectool version | awk '/^RW/{print $3}'")
	if err != nil {
		return err
	}
	d.ecRWVersion = out
	return nil
}

// setGSCVersion interfaces with a DUT and sets the gscVersion field (the version of the DUT's Google Security Chip firmware).
func (d *dut) setGSCVersion() error {
	out, err := dutio.SendSSHCommand(d.hostname, "echo $(grep ^RO /var/cache/cr50-version) / $(grep ^RW /var/cache/cr50-version)")
	if err != nil {
		return err
	}
	d.gscVersion = out
	return nil
}

// setCPUArch interfaces with a DUT and sets the cpuArch field (the architecture of the central processing unit).
func (d *dut) setCPUArch() error {
	out, err := dutio.SendSSHCommand(d.hostname, "lscpu | awk '/^Architecture:/{print $2}'")
	if err != nil {
		return err
	}
	d.cpuArch = out
	return nil
}

// setCPUModel interfaces with a DUT and sets the cpuModel field (the market identifier of the central processing unit).
func (d *dut) setCPUModel() error {
	out, err := dutio.SendSSHCommand(d.hostname, "lscpu | grep '^Model name:' | cut -d: -f2-")
	if err != nil {
		return err
	}
	d.cpuModel = out
	return nil
}

// setCPUSpeed interfaces with a DUT and sets the cpuSpeed field (the clock frequency of the central processing unit).
func (d *dut) setCPUSpeed() error {
	out, err := dutio.SendSSHCommand(d.hostname, "lscpu | grep '^CPU max MHz:' | cut -d: -f2-")
	if err != nil {
		return err
	}
	d.cpuSpeed = out
	return nil
}

// setTotalMemory interfaces with a DUT and sets the totalMemory field (the size of the main memory).
func (d *dut) setTotalMemory() error {
	out, err := dutio.SendSSHCommand(d.hostname, "grep '^MemTotal:' /proc/meminfo 2>/dev/null | cut -d: -f2-")
	if err != nil {
		return err
	}
	d.totalMemory = out
	return nil
}

// setMemoryType interfaces with a DUT and sets the memoryType field (the technology class of the main memory).
func (d *dut) setMemoryType() error {
	out, err := dutio.SendSSHCommand(d.hostname, "mosys memory spd print id 2>/dev/null | cut -d'|' -f2- | sort -u")
	if err != nil {
		return err
	}
	d.memoryType = out
	return nil
}

// setMMCModel interfaces with a DUT and sets the mmcModel field (the multimedia card market identifier).
func (d *dut) setMMCModel() error {
	out, err := dutio.SendSSHCommand(d.hostname, "if [ -e /dev/mmcblk ]; then cat /dev/mmcblk/device/name; else true; fi")
	if err != nil {
		return err
	}
	d.mmcModel = out
	return nil
}

// setMMCFirmwareVersion interfaces with a DUT and sets the version of the multimedia card's firmware.
func (d *dut) setMMCFirmwareVersion() error {
	out, err := dutio.SendSSHCommand(d.hostname, "if [ -e /dev/mmcblk ]; then cat /dev/mmcblk/device/firmware; else true; fi")
	if err != nil {
		return err
	}
	d.mmcFirmwareVersion = out
	return nil
}

// setNVMEModel interfaces with a DUT and sets the nvmeModel (the market identifier of the non-volatile memory express solid state drive).
func (d *dut) setNVMEModel() error {
	out, err := dutio.SendSSHCommand(d.hostname, "if [ -e /dev/nvme0n1 ]; then cat /dev/nvme0n1/device/name; else true; fi")
	if err != nil {
		return err
	}
	d.nvmeModel = out
	return nil
}

// setNVMEFirmwareVersion interfaces with a DUT and sets the nvmeFirmwareVersion field (the firmware version of the non-volatile
//  memory express solid state drive).
func (d *dut) setNVMEFirmwareVersion() error {
	out, err := dutio.SendSSHCommand(d.hostname, "if [ -e /dev/nvme0n1 ]; then cat /dev/nvme0n1/device/fwrev; else true; fi")
	if err != nil {
		return err
	}
	d.nvmeFirmwareVersion = out
	return nil
}

// setVPD interfaces with a DUT and sets the vpd field (the "Vital Product Data").
func (d *dut) setVPD() error {
	out, err := dutio.SendSSHCommand(d.hostname, "vpd -l")
	if err != nil {
		return err
	}
	d.vpd = out
	return nil
}

// newDUT initializes all the fields in a dut struct.
func newDUT(hostname string) dut {
	d := dut{hostname: hostname}
	d.setModel()
	d.setPhase()
	d.setCrOSVersion()
	d.setBIOSVersion()
	d.setECROVersion()
	d.setECRWVersion()
	d.setGSCVersion()
	d.setCPUArch()
	d.setCPUModel()
	d.setCPUSpeed()
	d.setTotalMemory()
	d.setMemoryType()
	d.setMMCModel()
	d.setMMCFirmwareVersion()
	d.setNVMEModel()
	d.setNVMEFirmwareVersion()
	d.setVPD()
	return d
}

func main() {
	fmt.Println("This utility is undergoing incremental development.  Please use crostestutils/provingground/firmware/dut.sh for now.")
	// TODO(kmshelton): Unhardcode the hostname.
	d := newDUT("chromeos1-row1-rack8-host2.cros.corp.google.com")
	fmt.Printf("%+v\n", d)
}
