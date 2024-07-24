// Copyright 2020 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package main

import (
	"errors"
	"fmt"
	"log"
	"math"
	"os"
	"regexp"
	"strconv"
	"strings"

	"go.chromium.org/base-os-engprod-tools/internal/pkg/dutio"
)

const crosDeviceInfoURL = "https://www.chromium.org/chromium-os/developer-information-for-chrome-os-devices/"

type dut struct {
	hostname                string
	board                   string
	model                   string
	oem                     string
	marketingName           string
	phase                   string
	CROSVersion             string
	biosVersion             string
	ecROVersion             string
	ecRWVersion             string
	gscVersion              string
	cpuArch                 string
	cpuModel                string
	cpuSpeed                string
	totalMemory             string
	memoryType              string
	memoryID                string
	memorySpeed             string
	storageType             string
	storageSize             string
	mmcModel                string
	mmcFirmwareVersion      string
	nvmeModel               string
	nvmeFirmwareVersion     string
	displaySize             string
	displayResolution       string
	displayRefreshRate      string
	designedBatteryCapacity string
	vpd                     string
}

// convertBytesToGigabytes performs a simple conversion of bytes to Gigabytes
func convertBytesToGigabytes(bytes int) float64 {
	return float64(bytes) / 1000 / 1000 / 1000
}

// convertKilobytesToGigabytes performs a simple conversion of Kilobytes to
// Gigabytes
func convertKilobytesToGigabytes(kilobytes int) float64 {
	return float64(kilobytes) / 1000 / 1000
}

// convertCentimetersToInches performs a simple conversion of centimeters to
// inches
func convertCentimetersToInches(centimeters float64) float64 {
	return centimeters / 2.54
}

// printField prints the DUT field and value with padding.
func (d *dut) printField(field string, value string) {
	fmt.Printf("%-18s : %s\n", field, value)
}

// printFields prints to console all of the fields belonging to the dut.
func (d *dut) printFields() {
	fmt.Println()
	d.printField("Board", d.board)
	d.printField("Model", d.model)
	d.printField("OEM", d.oem)
	d.printField("Marketing Name", d.marketingName)
	d.printField("ChromeOS Version", d.CROSVersion)
	d.printField("BIOS Version", d.biosVersion)
	d.printField("EC-RO Version", d.ecROVersion)
	d.printField("EC-RW Version", d.ecRWVersion)
	d.printField("GSC Version", d.gscVersion)
	fmt.Println()
	d.printField("CPU Model", d.cpuModel)
	d.printField("CPU Arch", d.cpuArch)
	d.printField("CPU Speed", d.cpuSpeed)
	fmt.Println()
	d.printField("Total Memory", d.totalMemory)
	d.printField("Memory Type", d.memoryType)
	d.printField("Memory ID", d.memoryID)
	d.printField("Memory Speed", d.memorySpeed)
	fmt.Println()
	d.printField("Storage Type", d.storageType)
	d.printField("Storage Size", d.storageSize)
	if d.mmcModel != "" {
		d.printField("MMC Model", d.mmcModel)
		d.printField("MMC Firmware", d.mmcFirmwareVersion)
	} else if d.nvmeModel != "" {
		d.printField("NVMe Model", d.nvmeModel)
		d.printField("NVMe Firmware", d.nvmeFirmwareVersion)
	}
	fmt.Println()
	d.printField("Display Size", d.displaySize)
	d.printField("Display Resolution", d.displayResolution)
	d.printField("Display Refresh Rate", d.displayRefreshRate)
	fmt.Println()
	d.printField("Designed Battery Capacity", d.designedBatteryCapacity)
	fmt.Println()
	d.printField("VPD", d.vpd)
}

// setField is a wrapper around set<COMPONENT> style functions that adds
// additional logging.
func (d *dut) setField(name string, setter func() error) {
	log.Printf("Retrieving %s...\n", name)
	err := setter()
	if err != nil {
		log.Printf("[%s] %s\n", name, err)
	}
}

// buildErr creates and returns an error if stderr is not empty
func buildErr(stderr string) error {
	if stderr != "" {
		return errors.New(stderr)
	}
	return nil
}

// setBoard fetches the board from the DUT and sets the board field
func (d *dut) setBoard() error {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"grep '^CHROMEOS_RELEASE_BOARD=' /etc/lsb-release",
	)
	stdoutSplit := strings.Split(stdout, "=")
	if len(stdoutSplit) == 2 {
		d.board = strings.TrimSpace(stdoutSplit[1])
	} else {
		stderr += fmt.Sprintf("\nUnable to parse setBoard stdout: \"%s\"\n", stdout)
	}
	return buildErr(stderr)
}

// setModel interfaces with a DUT and sets the model field (the DUT's market
// identifier).
func (d *dut) setModel() error {
	// TODO(seancarpenter): Here and elsewhere: use dbus instead of executing
	// commands directly on the DUT (by exposing such functionality in dutio).
	stdout, stderr := dutio.ExecuteRemoteCommand(d.hostname, "cros_config / name")
	d.model = strings.TrimSpace(stdout)
	return buildErr(stderr)
}

// setOEM uses the board and model to look up the OEM.
// TODO(seancarpenter) Implement this
func (d *dut) setOEM() error {
	d.oem = fmt.Sprintf("Look up the board and model at: %s", crosDeviceInfoURL)
	return nil
}

// setMarketingName uses the board and model to look up the Marketing Name
// TODO(seancarpenter) Implement this
func (d *dut) setMarketingName() error {
	d.marketingName = fmt.Sprintf("Look up the board and model at: %s", crosDeviceInfoURL)
	return nil
}

// setPhase interfaces with a DUT and sets the phase field (the DUT's hardware
// stage).
func (d *dut) setPhase() error {
	// TODO(b:150699151): Implement this setter (interface with the HWID database).
	d.phase = ""
	return nil
}

// setCROSVersion interfaces with a DUT and sets the CROSVersion field (the
// DUT's version of ChromeOS).
func (d *dut) setCROSVersion() error {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"grep '^CHROMEOS_RELEASE_DESCRIPTION=' /etc/lsb-release | cut -d= -f2",
	)
	d.CROSVersion = strings.TrimSpace(stdout)
	return buildErr(stderr)
}

// setBIOSVersion interfaces with a DUT and sets the biosVersion field (the
// DUT's application processor firmware version).
func (d *dut) setBIOSVersion() error {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"echo $(crossystem ro_fwid) / $(crossystem fwid)",
	)
	d.biosVersion = strings.TrimSpace(stdout)
	return buildErr(stderr)
}

// setECROVersion interfaces with a DUT and sets the ecROVersion field (the
// version of the DUT's read-only copy of the primary embedded controller's
// firmware version).
func (d *dut) setECROVersion() error {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"ectool version | awk '/^RO/{print $3}'",
	)
	d.ecROVersion = strings.TrimSpace(stdout)
	return buildErr(stderr)
}

// setECRWVersion interfaces with a DUT and sets the ecRWVersion field
// (the version of the DUT's read-write copy of the primary embedded
// controller's firmware version).
func (d *dut) setECRWVersion() error {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"ectool version | awk '/^RW/{print $3}'",
	)
	d.ecRWVersion = strings.TrimSpace(stdout)
	return buildErr(stderr)
}

// setGSCVersion interfaces with a DUT and sets the gscVersion field (the
// version of the DUT's Google Security Chip firmware).
func (d *dut) setGSCVersion() error {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"echo $(grep ^RO /var/cache/cr50-version) / $(grep ^RW /var/cache/cr50-version)",
	)
	d.gscVersion = strings.TrimSpace(stdout)
	return buildErr(stderr)
}

// setCPUArch interfaces with a DUT and sets the cpuArch field (the architecture
// of the central processing unit).
func (d *dut) setCPUArch() error {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"lscpu | awk '/^Architecture:/{print $2}'",
	)
	d.cpuArch = strings.TrimSpace(stdout)
	return buildErr(stderr)
}

// setCPUModel interfaces with a DUT and sets the cpuModel field (the market
// identifier of the central processing unit).
func (d *dut) setCPUModel() error {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"lscpu | grep '^Model name:' | cut -d: -f2-",
	)
	d.cpuModel = strings.TrimSpace(stdout)
	return buildErr(stderr)
}

// setCPUSpeed interfaces with a DUT and sets the cpuSpeed field (the clock
// frequency of the central processing unit).
func (d *dut) setCPUSpeed() error {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"lscpu | grep '^CPU max MHz:' | cut -d: -f2-",
	)
	d.cpuSpeed = fmt.Sprintf("%s MHz", strings.TrimSpace(stdout))
	return buildErr(stderr)
}

// setTotalMemory interfaces with a DUT and sets the totalMemory field (the
// size of the main memory).
func (d *dut) setTotalMemory() error {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"cat /proc/meminfo",
	)
	r := regexp.MustCompile(`MemTotal:\s+(?P<TotalMemory>\d+)`)
	res := r.FindStringSubmatch(stdout)
	if len(res) > 1 {
		totalMemoryInKilobytes, err := strconv.Atoi(res[1])
		// We should never fail to convert here since the regex capture group
		// should always contain an integer, but good to check anyways.
		if err != nil {
			stderr += fmt.Sprintf("Unable to parse setTotalMemory stdout: \"%s\"\n%s\n", stdout, err)
		} else {
			d.totalMemory = fmt.Sprintf("%.2f GB", convertKilobytesToGigabytes(totalMemoryInKilobytes))
		}
	} else {
		stderr += fmt.Sprintf("Unable to parse setTotalMemory stdout: \"%s\"\n", stdout)
	}
	return buildErr(stderr)
}

// setMemoryType interfaces with a DUT and sets the memoryType field (e.g. DDR4)
func (d *dut) setMemoryType() error {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"mosys memory spd print type 0",
	)
	stdoutSplit := strings.Split(stdout, "|")
	if len(stdoutSplit) == 2 {
		d.memoryType = strings.TrimSpace(stdoutSplit[1])
	} else {
		stderr += fmt.Sprintf("\nUnable to parse setMemoryType stdout: \"%s\"\n", stdout)
	}
	return buildErr(stderr)
}

// setMemoryID interfaces with a DUT and sets the memory ID (the unique ID
// that identifies the exact memory model)
func (d *dut) setMemoryID() error {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"mosys memory spd print id 0",
	)
	stdoutSplit := strings.Split(stdout, "|")
	if len(stdoutSplit) == 3 {
		d.memoryID = strings.TrimSpace(stdoutSplit[2])
	} else {
		stderr += fmt.Sprintf("Unable to parse setMemoryID stdout: \"%s\"\n", stdout)
	}
	return buildErr(stderr)
}

// setMemorySpeed interfaces with a DUT and sets the memory speed in MHz
func (d *dut) setMemorySpeed() error {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"dmidecode --type memory",
	)
	r := regexp.MustCompile(`Speed: (?P<Speed>\d+)`)
	res := r.FindStringSubmatch(stdout)
	if len(res) > 1 {
		d.memorySpeed = fmt.Sprintf("%s MHz", res[1])
	} else {
		stderr += fmt.Sprintf("Unable to parse setMemorySpeed stdout: \"%s\"\n", stdout)
	}
	return buildErr(stderr)
}

// setStorageType interfaces with a DUT and sets the storage type (NVME, UFS,
// etc)
func (d *dut) setStorageType() error {
	// NOTE: Determining storage type is surprisingly hard. This
	// is a relatively hacky way of doing it.
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		". /usr/share/misc/storage-info-common.sh; get_storage_info",
	)
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
	return buildErr(stderr)
}

// setStorageSize interfaces with the DUT to get the total storage size (in GB).
func (d *dut) setStorageSize() error {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"spaced_cli --get_root_device_size",
	)
	storageSizeInBytes, err := strconv.Atoi(stdout)
	if err != nil {
		stderr += fmt.Sprintf("Unable to parse setStorageSize stdout: \"%s\"\n%s\n", stdout, err)
	}
	d.storageSize = fmt.Sprintf("%.2f GB", convertBytesToGigabytes(storageSizeInBytes))
	return buildErr(stderr)
}

// setMMCModel interfaces with a DUT and sets the mmcModel field (the multimedia
// card market identifier).
func (d *dut) setMMCModel() error {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"MMCBLK=$(ls -d /sys/block/mmcblk? 2>/dev/null); if [ ! -z ${MMCBLK} ]; then cat $MMCBLK/device/name; else true; fi",
	)
	d.mmcModel = strings.TrimSpace(stdout)
	return buildErr(stderr)
}

// setMMCFirmwareVersion interfaces with a DUT and sets the version of the
// multimedia card's firmware.
func (d *dut) setMMCFirmwareVersion() error {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"MMCBLK=$(ls -d /sys/block/mmcblk? 2>/dev/null); if [ ! -z ${MMCBLK} ]; then cat $MMCBLK/device/fwrev; else true; fi",
	)
	d.mmcFirmwareVersion = strings.TrimSpace(stdout)
	return buildErr(stderr)
}

// setNVMEModel interfaces with a DUT and sets the nvmeModel (the market
// identifier of the non-volatile memory express solid state drive).
func (d *dut) setNVMEModel() error {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"if [ -e /dev/nvme0n1 ]; then smartctl -a /dev/nvme0n1 | grep \"Model Number\" | tr -s ' ' | cut -d ' ' -f 3,4; else true; fi",
	)
	d.nvmeModel = strings.TrimSpace(stdout)
	return buildErr(stderr)
}

// setNVMEFirmwareVersion interfaces with a DUT and sets the nvmeFirmwareVersion
// field (the firmware version of the non-volatile memory express solid state
// drive).
func (d *dut) setNVMEFirmwareVersion() error {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"if [ -e /dev/nvme0n1 ]; then smartctl -a /dev/nvme0n1 | grep \"Firmware Version\" | tr -s ' ' | cut -d ' ' -f 3; else true; fi",
	)
	d.nvmeFirmwareVersion = strings.TrimSpace(stdout)
	return buildErr(stderr)
}

// setDisplaySize gets the display size in inches.
func (d *dut) setDisplaySize() error {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"find /sys -name '*edid' -exec edid-decode {} \\;",
	)
	r := regexp.MustCompile(`Maximum image size: (?P<Width>\d+) cm x (?P<Height>\d+) cm`)
	res := r.FindStringSubmatch(stdout)
	if len(res) > 2 {
		width, widthErr := strconv.ParseFloat(res[1], 64)
		height, heightErr := strconv.ParseFloat(res[2], 64)
		if widthErr != nil || heightErr != nil {
			stderr += fmt.Sprintf("Unable to parse setDisplaySize stdout: \"%s\"\n%s%s\n", stdout, widthErr, heightErr)
		} else {
			width = convertCentimetersToInches(width)
			height = convertCentimetersToInches(height)
			diagonalLength := math.Sqrt(math.Pow(width, 2) + math.Pow(height, 2))
			d.displaySize = fmt.Sprintf("%.2f in x %.2f in (%.2f in diagonal)", width, height, diagonalLength)
		}
	} else {
		stderr += fmt.Sprintf("Unable to parse setDisplaySize stdout: \"%s\"\n", stdout)
	}
	return buildErr(stderr)
}

// setDisplayResolution gets the resolution of the display
func (d *dut) setDisplayResolution() error {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"find /sys -name '*edid' -exec edid-decode {} \\;",
	)
	r := regexp.MustCompile(`DTD \d:\s+(?P<Resolution>\d+x\d+)`)
	res := r.FindStringSubmatch(stdout)
	if len(res) > 1 {
		d.displayResolution = res[1]
	} else {
		stderr += fmt.Sprintf("Unable to parse setDisplayResolution stdout: \"%s\"\n", stdout)
	}
	return buildErr(stderr)
}

// setDisplayRefreshRate gets the refresh rate of the display in Hz
func (d *dut) setDisplayRefreshRate() error {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"find /sys -name '*edid' -exec edid-decode {} \\;",
	)
	r := regexp.MustCompile(`DTD.*\s(?P<RefreshRate>\d+\.\d+ Hz)`)
	res := r.FindStringSubmatch(stdout)
	if len(res) > 1 {
		d.displayRefreshRate = res[1]
	} else {
		stderr += fmt.Sprintf("Unable to parse setDisplayRefreshRate stdout: \"%s\"\n", stdout)
	}
	return buildErr(stderr)
}

// setDesignedBatteryCapacity gets the designed battery capacity of the dut in
// Wh (watt hours).
func (d *dut) setDesignedBatteryCapacity() error {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"ectool battery",
	)
	r := regexp.MustCompile(`Design capacity:\s+(\d+)`)
	res := r.FindStringSubmatch(stdout)
	designedCapacityInMAH := 0.0
	if len(res) > 1 {
		designedCapacityInMAH, _ = strconv.ParseFloat(res[1], 64)
	} else {
		stderr += fmt.Sprintf("Unable to parse setDesignedBatteryCapacity stdout: \"%s\"\n", stdout)
	}

	r = regexp.MustCompile(`Design output voltage\s+(\d+)`)
	res = r.FindStringSubmatch(stdout)
	designedVoltageInMV := 0.0
	if len(res) > 1 {
		designedVoltageInMV, _ = strconv.ParseFloat(res[1], 64)
	} else {
		stderr += fmt.Sprintf("Unable to parse setDesignedBatteryCapacity stdout: \"%s\"\n", stdout)
	}
	if designedCapacityInMAH > 0 && designedVoltageInMV > 0 {
		d.designedBatteryCapacity = fmt.Sprintf("%.2f Watt Hours", (designedCapacityInMAH/1000.0)*(designedVoltageInMV/1000.0))
	}
	return buildErr(stderr)
}

// setVPD interfaces with a DUT and sets the vpd field (the "Vital Product
// Data").
func (d *dut) setVPD() error {
	stdout, stderr := dutio.ExecuteRemoteCommand(
		d.hostname,
		"vpd -l | grep -v DO_NOT_SHARE | grep -v -i mac",
	)
	d.vpd = fmt.Sprintf("\n%s", strings.TrimSpace(stdout))
	return buildErr(stderr)
}

// newDUT initializes all the fields in a dut struct.
func newDUT(hostname string) dut {
	d := dut{hostname: hostname}
	d.setField("Board", d.setBoard)
	d.setField("Model", d.setModel)
	d.setField("OEM", d.setOEM)
	d.setField("Marketing Name", d.setMarketingName)
	d.setField("Phase", d.setPhase)
	d.setField("ChromeOS Version", d.setCROSVersion)
	d.setField("BIOS Version", d.setBIOSVersion)
	d.setField("EC-RO Version", d.setECROVersion)
	d.setField("EC-RW Version", d.setECRWVersion)
	d.setField("GSC Version", d.setGSCVersion)
	d.setField("CPU Model", d.setCPUModel)
	d.setField("CPU Arch", d.setCPUArch)
	d.setField("CPU Speed", d.setCPUSpeed)
	d.setField("Total Memory", d.setTotalMemory)
	d.setField("Memory Type", d.setMemoryType)
	d.setField("Memory ID", d.setMemoryID)
	d.setField("Memory Speed", d.setMemorySpeed)
	d.setField("Storage Type", d.setStorageType)
	d.setField("Storage Size", d.setStorageSize)
	d.setField("MMC Model", d.setMMCModel)
	d.setField("MMC Firmware", d.setMMCFirmwareVersion)
	d.setField("NVMe Model", d.setNVMEModel)
	d.setField("NVMe Firmware", d.setNVMEFirmwareVersion)
	d.setField("Display Size", d.setDisplaySize)
	d.setField("Display Resolution", d.setDisplayResolution)
	d.setField("Display Refresh Rate", d.setDisplayRefreshRate)
	d.setField("Desgined Battery Capacity", d.setDesignedBatteryCapacity)
	d.setField("VPD", d.setVPD)
	return d
}

func main() {
	if len(os.Args) != 2 {
		log.Panic("Please pass a DUT hostname and only a DUT hostname to this utility.")
	}
	d := newDUT(os.Args[1])
	d.printFields()
}
