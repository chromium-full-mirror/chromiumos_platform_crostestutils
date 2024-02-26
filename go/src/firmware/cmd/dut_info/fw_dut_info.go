// Copyright 2020 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package main

import (
	"fmt"
	"log"
	"os"
	"regexp"
	"strings"

	"go.chromium.org/fw-engprod-tools/internal/pkg/dutio"
)

const crosDeviceInfoURL = "https://www.chromium.org/chromium-os/developer-information-for-chrome-os-devices/"

type dut struct {
	hostname            string
	board               string
	model               string
	oem                 string
	marketingName       string
	phase               string
	CROSVersion         string
	biosVersion         string
	ecROVersion         string
	ecRWVersion         string
	gscVersion          string
	cpuArch             string
	cpuModel            string
	cpuSpeed            string
	totalMemory         string
	memoryType          string
	memoryID            string
	memorySpeed         string
	mmcModel            string
	mmcFirmwareVersion  string
	nvmeModel           string
	nvmeFirmwareVersion string
	storageType         string
	vpd                 string
}

func (d *dut) printBugTemplate() {
	fmt.Println("Board             :", d.board)
	fmt.Println("Model             :", d.model)
	fmt.Println("OEM               :", d.oem)
	fmt.Println("Marketing Name    :", d.marketingName)
	fmt.Println("ChromeOS Version  :", d.CROSVersion)
	fmt.Println("BIOS Version      :", d.biosVersion)
	fmt.Println("EC Version        :", d.ecROVersion, "/", d.ecRWVersion)
	fmt.Println("cr50 Version      :", d.gscVersion)
	fmt.Println()
	fmt.Println("CPU Model         :", d.cpuModel)
	fmt.Println("CPU arch          :", d.cpuArch)
	fmt.Println("CPU speed         :", d.cpuSpeed)
	fmt.Println("Total Memory      :", d.totalMemory)
	fmt.Println("Memory Type       :", d.memoryType)
	fmt.Println("Memory ID         :", d.memoryID)
	fmt.Println("Memory Speed      :", d.memorySpeed)
	fmt.Println("Storage Type      :", d.storageType)
	if d.mmcModel != "" {
		fmt.Println("MMC Model         :", d.mmcModel)
		fmt.Println("MMC Firmware      :", d.mmcFirmwareVersion)
	} else if d.nvmeModel != "" {
		fmt.Println("NVMe Model        :", d.nvmeModel)
		fmt.Println("NVMe Firmware     :", d.nvmeFirmwareVersion)
	}
	fmt.Println()
	fmt.Println("VPD info:\n", d.vpd)
}

// setBoard fetches the board from the DUT and sets the board field
func (d *dut) setBoard() {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"grep '^CHROMEOS_RELEASE_BOARD=' /etc/lsb-release",
	)
	if stderr != "" {
		fmt.Println(stderr)
	}

	stdoutSplit := strings.Split(stdout, "=")
	if len(stdoutSplit) == 2 {
		d.board = strings.TrimSpace(stdoutSplit[1])
	} else {
		fmt.Printf("Unable to parse setBoard stdout: \"%s\"\n", stdout)
	}
}

// setModel interfaces with a DUT and sets the model field (the DUT's market
// identifier).
func (d *dut) setModel() {
	// TODO(seancarpenter): Here and elsewhere: use dbus instead of executing
	// commands directly on the DUT (by exposing such functionality in dutio).
	stdout, stderr := dutio.ExecuteRemoteCommand(d.hostname, "cros_config / name")
	if stderr != "" {
		fmt.Println(stderr)
	}
	d.model = strings.TrimSpace(stdout)
}

// setOEM uses the board and model to look up the OEM.
// TODO(seancarpenter) Implement this
func (d *dut) setOEM() {
	d.oem = fmt.Sprintf("Look up the board and model at: %s", crosDeviceInfoURL)
}

// setMarketingName uses the board and model to look up the Marketing Name
// TODO(seancarpenter) Implement this
func (d *dut) setMarketingName() {
	d.marketingName = fmt.Sprintf("Look up the board and model at: %s", crosDeviceInfoURL)
}

// setPhase interfaces with a DUT and sets the phase field (the DUT's hardware
// stage).
func (d *dut) setPhase() {
	// TODO(b:150699151): Implement this setter (interface with the HWID database).
	d.phase = ""
}

// setCROSVersion interfaces with a DUT and sets the CROSVersion field (the
// DUT's version of ChromeOS).
func (d *dut) setCROSVersion() {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"grep '^CHROMEOS_RELEASE_DESCRIPTION=' /etc/lsb-release | cut -d= -f2",
	)
	if stderr != "" {
		fmt.Println(stderr)
	}
	d.CROSVersion = strings.TrimSpace(stdout)
}

// setBIOSVersion interfaces with a DUT and sets the biosVersion field (the
// DUT's application processor firmware version).
func (d *dut) setBIOSVersion() {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"echo $(crossystem ro_fwid) / $(crossystem fwid)",
	)
	if stderr != "" {
		fmt.Println(stderr)
	}
	d.biosVersion = strings.TrimSpace(stdout)
}

// setECROVersion interfaces with a DUT and sets the ecROVersion field (the
// version of the DUT's read-only copy of the primary embedded controller's
// firmware version).
func (d *dut) setECROVersion() {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"ectool version | awk '/^RO/{print $3}'",
	)
	if stderr != "" {
		fmt.Println(stderr)
	}
	d.ecROVersion = strings.TrimSpace(stdout)
}

// setECRWVersion interfaces with a DUT and sets the ecRWVersion field
// (the version of the DUT's read-write copy of the primary embedded
// controller's firmware version).
func (d *dut) setECRWVersion() {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"ectool version | awk '/^RW/{print $3}'",
	)
	if stderr != "" {
		fmt.Println(stderr)
	}
	d.ecRWVersion = strings.TrimSpace(stdout)
}

// setGSCVersion interfaces with a DUT and sets the gscVersion field (the
// version of the DUT's Google Security Chip firmware).
func (d *dut) setGSCVersion() {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"echo $(grep ^RO /var/cache/cr50-version) / $(grep ^RW /var/cache/cr50-version)",
	)
	if stderr != "" {
		fmt.Println(stderr)
	}
	d.gscVersion = strings.TrimSpace(stdout)
}

// setCPUArch interfaces with a DUT and sets the cpuArch field (the architecture
// of the central processing unit).
func (d *dut) setCPUArch() {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"lscpu | awk '/^Architecture:/{print $2}'",
	)
	if stderr != "" {
		fmt.Println(stderr)
	}
	d.cpuArch = strings.TrimSpace(stdout)
}

// setCPUModel interfaces with a DUT and sets the cpuModel field (the market
// identifier of the central processing unit).
func (d *dut) setCPUModel() {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"lscpu | grep '^Model name:' | cut -d: -f2-",
	)
	if stderr != "" {
		fmt.Println(stderr)
	}
	d.cpuModel = strings.TrimSpace(stdout)
}

// setCPUSpeed interfaces with a DUT and sets the cpuSpeed field (the clock
// frequency of the central processing unit).
func (d *dut) setCPUSpeed() {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"lscpu | grep '^CPU max MHz:' | cut -d: -f2-",
	)
	if stderr != "" {
		fmt.Println(stderr)
	}
	d.cpuSpeed = fmt.Sprintf("%s MHz", strings.TrimSpace(stdout))
}

// setTotalMemory interfaces with a DUT and sets the totalMemory field (the
// size of the main memory).
func (d *dut) setTotalMemory() {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"grep '^MemTotal:' /proc/meminfo 2>/dev/null | cut -d: -f2-",
	)
	if stderr != "" {
		fmt.Println(stderr)
	}
	d.totalMemory = strings.TrimSpace(stdout)
}

// setMemoryType interfaces with a DUT and sets the memoryType field (e.g. DDR4)
func (d *dut) setMemoryType() {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"mosys memory spd print type 0",
	)
	if stderr != "" {
		fmt.Println(stderr)
	}
	stdoutSplit := strings.Split(stdout, "|")
	if len(stdoutSplit) == 2 {
		d.memoryType = strings.TrimSpace(stdoutSplit[1])
	} else {
		fmt.Printf("Unable to parse setMemoryType stdout: \"%s\"\n", stdout)
	}
}

// setMemoryID interfaces with a DUT and sets the memory ID (the unique ID
// that identifies the exact memory model)
func (d *dut) setMemoryID() {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"mosys memory spd print id 0",
	)
	if stderr != "" {
		fmt.Println(stderr)
	}
	stdoutSplit := strings.Split(stdout, "|")
	if len(stdoutSplit) == 3 {
		d.memoryID = strings.TrimSpace(stdoutSplit[2])
	} else {
		fmt.Printf("Unable to parse setMemoryID stdout: \"%s\"\n", stdout)
	}

}

// setMemorySpeed interfaces with a DUT and sets the memory speed in MHz
func (d *dut) setMemorySpeed() {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"dmidecode --type memory",
	)
	if stderr != "" {
		fmt.Println(stderr)
	}

	r := regexp.MustCompile(`Speed: (?P<Speed>\d+)`)
	res := r.FindStringSubmatch(stdout)
	if len(res) >= 1 {
		d.memorySpeed = fmt.Sprintf("%s MHz", res[1])
	} else {
		fmt.Printf("Unable to parse setMemorySpeed stdout: \"%s\"\n", stdout)
	}

}

// setStorageType interfaces with a DUT and sets the storage type (NVME, UFS,
// etc)
func (d *dut) setStorageType() {
	// NOTE: Determining storage type is surprisingly hard. This
	// is a relatively hacky way of doing it.
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		". /usr/share/misc/storage-info-common.sh; get_storage_info",
	)
	if stderr != "" {
		fmt.Println(stderr)
	}

	d.storageType = "UNKNOWN"
	ssdRegex := regexp.MustCompile(`SATA Version is:`)
	ufsRegex := regexp.MustCompile(`ufs-utils`)
	nvmeRegex := regexp.MustCompile("NVME")
	mmcRegex := regexp.MustCompile("MMC")
	if ssdRegex.MatchString(stdout) {
		d.storageType = "SSD"
	} else if ufsRegex.MatchString(stdout) {
		d.storageType = "UFS"
	} else if nvmeRegex.MatchString(stdout) {
		d.storageType = "NVME"
	} else if mmcRegex.MatchString(stdout) {
		d.storageType = "MMC"
	}
}

// setMMCModel interfaces with a DUT and sets the mmcModel field (the multimedia
// card market identifier).
func (d *dut) setMMCModel() {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"MMCBLK=$(ls -d /sys/block/mmcblk? 2>/dev/null); if [ ! -z ${MMCBLK} ]; then cat $MMCBLK/device/name; else true; fi",
	)
	if stderr != "" {
		fmt.Println(stderr)
	}
	d.mmcModel = strings.TrimSpace(stdout)
}

// setMMCFirmwareVersion interfaces with a DUT and sets the version of the
// multimedia card's firmware.
func (d *dut) setMMCFirmwareVersion() {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"MMCBLK=$(ls -d /sys/block/mmcblk? 2>/dev/null); if [ ! -z ${MMCBLK} ]; then cat $MMCBLK/device/fwrev; else true; fi",
	)
	if stderr != "" {
		fmt.Println(stderr)
	}
	d.mmcFirmwareVersion = strings.TrimSpace(stdout)
}

// setNVMEModel interfaces with a DUT and sets the nvmeModel (the market
// identifier of the non-volatile memory express solid state drive).
func (d *dut) setNVMEModel() {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"if [ -e /dev/nvme0n1 ]; then smartctl -a /dev/nvme0n1 | grep \"Model Number\" | tr -s ' ' | cut -d ' ' -f 3,4; else true; fi",
	)
	if stderr != "" {
		fmt.Println(stderr)
	}
	d.nvmeModel = strings.TrimSpace(stdout)
}

// setNVMEFirmwareVersion interfaces with a DUT and sets the nvmeFirmwareVersion
// field (the firmware version of the non-volatile memory express solid state
// drive).
func (d *dut) setNVMEFirmwareVersion() {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"if [ -e /dev/nvme0n1 ]; then smartctl -a /dev/nvme0n1 | grep \"Firmware Version\" | tr -s ' ' | cut -d ' ' -f 3; else true; fi",
	)
	if stderr != "" {
		fmt.Println(stderr)
	}
	d.nvmeFirmwareVersion = strings.TrimSpace(stdout)
}

// setVPD interfaces with a DUT and sets the vpd field (the "Vital Product
// Data").
func (d *dut) setVPD() {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"vpd -l | grep -v DO_NOT_SHARE | grep -v -i mac",
	)
	if stderr != "" {
		fmt.Println(stderr)
	}
	d.vpd = strings.TrimSpace(stdout)
}

// newDUT initializes all the fields in a dut struct.
func newDUT(hostname string) dut {
	d := dut{hostname: hostname}
	d.setModel()
	d.setBoard()
	d.setOEM()
	d.setMarketingName()
	d.setPhase()
	d.setCROSVersion()
	d.setBIOSVersion()
	d.setECROVersion()
	d.setECRWVersion()
	d.setGSCVersion()
	d.setCPUArch()
	d.setCPUModel()
	d.setCPUSpeed()
	d.setTotalMemory()
	d.setMemoryType()
	d.setMemoryID()
	d.setMemorySpeed()
	d.setStorageType()
	d.setMMCModel()
	d.setMMCFirmwareVersion()
	d.setNVMEModel()
	d.setNVMEFirmwareVersion()
	d.setVPD()
	return d
}

func main() {
	if len(os.Args) != 2 {
		log.Panic("Please pass a DUT hostname and only a DUT hostname to this utility.")
	}
	d := newDUT(os.Args[1])
	d.printBugTemplate()
}
