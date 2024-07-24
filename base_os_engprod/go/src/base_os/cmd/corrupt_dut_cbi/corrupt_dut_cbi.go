// Copyright 2022 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// Does what it says on the tin. Overwrites the CBI contents on a DUT with
// "0xff" values. To run, make sure you have ssh access setup for lab DUTs
// go/chromeos-lab-duts-ssh and then `go run corrupt_dut_cbi.go <hostname>`.
package main

import (
	"fmt"
	"log"
	"os"
	"regexp"
	"strings"

	"errors"

	"go.chromium.org/base-os-engprod-tools/internal/pkg/dutio"
)

// CBILocation stores the port and address needed to reference CBI contents in
// EEPROM.
type CBILocation struct {
	port    string
	address string
}

const (
	cbiMagic           = "0x43 0x42 0x49" // Magic bytes used to indicate the contents of the CBI chip.
	locateCBICommand   = "ectool locatechip 0 0"
	transferCBICommand = "ectool i2cxfer"

	cbiSize = 256 // How many bytes of memory are stored in CBI.

	// How many bytes to read during our write operation. This is a quirk of the
	// ectool i2cxfer API, and is always zero when writing.
	numBytesToReadDuringWrite = "0"

	// How many bytes can be read from and written to in a single ectool i2cxfer
	// command. These should be treated as hard limits. Exceeding these limits
	// can result in undefined writes to CBI, leaving the DUT in an obviously
	// corrupted, but unpredictable state.
	readIncrement  = 64
	writeIncrement = 8
)

var readCBIRegex = regexp.MustCompile(`0x[[:xdigit:]]{1,2}|00`) // Match bytes printed in hex format (e.g. 00, 0x12, 0x3)
var locateCBIRegex = regexp.MustCompile(`Port:\s(\d+).*Address:\s(0x\w+)`)
var corruptCBILine = strings.Repeat("0xff ", writeIncrement)

func main() {
	if len(os.Args) != 2 {
		fmt.Println("usage: corrupt_dut_cbi <hostname>")
		return
	}
	hostname := os.Args[1]
	_, stderr := dutio.ExecuteRemoteCommand(hostname, "")
	if stderr != "" {
		log.Panicf("unable to establish connection to the DUT: %s", stderr)
	}

	cbi, err := getCBILocation(hostname)
	if err != nil {
		log.Panicf("unable to determine if CBI is present on the DUT: %s", err)
	}
	fmt.Printf("CBI chip found at: Port %s, Address: %s\n\n", cbi.port, cbi.address)

	cbiContents, err := cbi.readCBIContents(hostname)
	if err != nil {
		log.Panicf("unable to read initial CBI contents: %s", err)
	}
	if !strings.Contains(cbiContents, cbiMagic) {
		log.Printf("CBI contents are already corrupt. Exiting early.")
		return
	}
	printCBIContents(cbiContents)

	err = cbi.corruptCBIContents(hostname)
	if err != nil {
		log.Panicf("unable to corrupt CBI contents: %s", err)
	}

	cbiContents, err = cbi.readCBIContents(hostname)
	if err != nil {
		log.Panicf("unable to read corrupted CBI contents: %s", err)
	}

	if strings.Contains(cbiContents, cbiMagic) {
		printCBIContents(cbiContents)
		log.Panic("Failed to corrupt CBI contents on DUT. CBI Magic is still present.")
	}

}

// readCBIContents returns the CBI contents of the DUT as a hex string.
func (cbi CBILocation) readCBIContents(hostname string) (string, error) {
	var hexContents []string
	for _, readCommand := range cbi.generateReadCommands() {
		stdout, stderr := dutio.ExecuteRemoteCommand(hostname, readCommand)
		if stderr != "" || stdout == "" {
			return "", errors.New("unable to read CBI contents: " + stderr)
		}

		hexBytes, err := parseBytesFromCBIContents(stdout)
		if err != nil {
			return "", err
		}

		hexContents = append(hexContents, hexBytes...)
	}
	return strings.Join(hexContents, " "), nil
}

// corruptCBIContents generates and executes the write commands to corrupt the DUT
func (cbi CBILocation) corruptCBIContents(hostname string) error {
	for _, corruptionCommand := range cbi.generateCorruptionCommand() {
		stdout, stderr := dutio.ExecuteRemoteCommand(hostname, corruptionCommand)
		if stderr != "" || stdout == "" {
			return errors.New("unable to write CBI contents: " + stderr)
		}
	}

	return nil
}

// parseBytesFromCBIContents reads readIncrement number of bytes from the
// raw output from a call to `ectool i2cxfer` and returns a slice of bytes
// in hex format (the same format returned from `ectool i2cxfer`).
// e.g.
// cbiContents = "Read bytes: 0x43, 0x42, 0x49"
// numBytesToRead = 2
// hexBytes = ["0x43", "0x42"]
func parseBytesFromCBIContents(cbiContents string) ([]string, error) {
	hexBytes := readCBIRegex.FindAllString(cbiContents, readIncrement)
	if len(hexBytes) != readIncrement {
		return nil, fmt.Errorf("read the incorrect amount of bytes from CBI. Intended to read %d bytes but read %d bytes instead. CBI Contents found: %s", readIncrement, len(hexBytes), cbiContents)
	}
	return hexBytes, nil
}

// generateCorruptionCommand returns a list of sequential write commands that when
// executed corrupt the contents of the dut <writeIncrement> bytes at a time.
func (cbi *CBILocation) generateCorruptionCommand() []string {
	var corruptionCommands []string
	for offset := 0; offset < cbiSize; offset += writeIncrement {
		corruptionCommands = append(corruptionCommands, fmt.Sprintf("%s %s %s %s %d %s",
			transferCBICommand,
			cbi.port,
			cbi.address,
			numBytesToReadDuringWrite,
			offset,
			corruptCBILine,
		))
	}
	return corruptionCommands
}

// generateReadCommands returns a list of sequential read commands that when
// executed read the contents of the dut <readIncrement> bytes at a time.
func (cbi CBILocation) generateReadCommands() []string {
	var readCommands []string
	for offset := 0; offset < cbiSize; offset += readIncrement {
		readCommands = append(readCommands, fmt.Sprintf("%s %s %s %d %d",
			transferCBICommand,
			cbi.port,
			cbi.address,
			readIncrement,
			offset,
		))
	}
	return readCommands
}

// getCBILocation uses the `ectool locatechip` utility to get the CBILocation
// from the DUT. Will return an error if the DUT doesn't support CBI or if it
// wasn't able to reach the DUT.
func getCBILocation(hostname string) (*CBILocation, error) {
	stdout, stderr := dutio.ExecuteRemoteCommand(hostname, locateCBICommand)
	if stderr != "" {
		return nil, errors.New("unable to determine if CBI is present on the DUT")
	}

	match := locateCBIRegex.FindStringSubmatch(stdout)
	if match == nil {
		return nil, errors.New("no CBI contents were found on the DUT")
	}
	return &CBILocation{
		port:    match[1],
		address: match[2],
	}, nil

}

func printCBIContents(cbiContents string) {
	fmt.Println("\n=======================================")
	fmt.Println("CBI Contents")
	fmt.Println("=======================================")
	hexBytes := strings.Fields(cbiContents)
	for offset := 0; offset < cbiSize; offset += writeIncrement {
		fmt.Println(strings.Join(hexBytes[offset:offset+writeIncrement], " "))
	}
	fmt.Print("=======================================\n\n")
}
