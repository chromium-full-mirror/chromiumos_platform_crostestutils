// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// A simple command line tool that downloads individual EC and AP images
// from Google Storage. This application does not handle the flashing of
// said images. Please use flashrom, futlity, or cros ap flash for that.
package main

import (
	"errors"
	"flag"
	"fmt"
	"io/ioutil"
	"os"
	"regexp"
	"strings"

	"golang.org/x/exp/slices"
)

const (
	helpHeader = "Downloads an EC or AP firmware image from Google Storage"
	// TODO(seancarpenter) Implement support for getting flags in any order.
	helpUsage               = "Usage: fwget [--board <board> --firmware <ec|ap> --version <latest|stable|release number] path"
	exampleUsage            = "fwget --board=galtic --firmware=ec --version=stable /tmp/your_image.bin "
	exampleUsageDescription = "Example usage: download the latest stable EC image for galtic boards to /tmp/your_image.bin"
	exampleReleaseString    = "R89-13606.459.0"

	firmwareTarName = "firmware_from_source.tar.bz2"

	// Example: R89-13606.459.0
	releaseStringRegexPattern = `(R\d+)-(\d+)\.(\d+)\.(\d+)`
)

// A mapping of boards to their respective baseboards. Necessary to determine
// the appropriate GS file path of some boards.
// TODO(seancarpenter): Find a way to programmatically generate this map.
var boardMap = map[string]string{
	"galtic": "dedede",
}

var requiredFlags = []string{"board", "firmware"}
var supportedFirmwareTypes = []string{"ec", "ap"}
var versionAliases = []string{"latest", "stable"}

var releaseStringRegex = regexp.MustCompile(releaseStringRegexPattern)

type image struct {
	board    string
	firmware string
	version  string
}

type release struct {
	milestone    string
	majorVersion string
	minorVersion string
	patchNumber  string
}

func (r release) String() string {
	return fmt.Sprintf("%s-%s.%s.%s",
		r.milestone,
		r.majorVersion,
		r.minorVersion,
		r.patchNumber,
	)
}

func main() {
	flags := flag.NewFlagSet(os.Args[0], flag.ExitOnError)

	// Override the Usage function of our flagSet so we can
	// control the formatting.
	flags.Usage = func() { printHelp(*flags) }

	// help := flags.Bool("help", false, "display the help message")
	board := flags.String("board", "", "the board to fetch the firmware image for")
	firmware := flags.String("firmware", "", "the firmware type: \"ec\" or \"ap\"")
	version := flags.String("version", "stable", fmt.Sprintf("the firmware image version: \"latest\", \"stable\" or a specific release like %s", exampleReleaseString))

	flags.Parse(os.Args[1:])

	img := image{
		*board,
		*firmware,
		*version,
	}

	if len(flags.Args()) == 0 {
		printHelp(*flags)
		os.Exit(0)
	}

	if err := validateInputs(img, *flags); err != nil {
		fmt.Println(err.Error())
		os.Exit(1)
	}

	//TODO(seancarpenter) Implement AP and EC image fetching. For now just exit.
	os.Exit(0)
}

func printHelp(flags flag.FlagSet) {
	fmt.Fprintf(os.Stderr, helpHeader+"\n\n")
	fmt.Fprintln(os.Stderr, exampleUsageDescription)
	fmt.Fprintf(os.Stderr, "\t"+exampleUsage+"\n\n")
	fmt.Fprintln(os.Stderr, helpUsage)
	flags.PrintDefaults()
}

func validateInputs(img image, flags flag.FlagSet) error {
	if len(flags.Args()) > 1 {
		return errors.New("error: too many arguments - please supply a single file path")
	}
	if err := validatePath(flags.Args()[0]); err != nil {
		return err
	}
	if err := validateRequiredFlagsArePresent(flags); err != nil {
		return err
	}
	if err := validateFlagContents(img); err != nil {
		return err
	}
	return nil
}

func validatePath(path string) error {
	if _, err := os.Stat(path); err == nil {
		return fmt.Errorf("path: %s already exists", path)
	}

	// Check if we have permissions to write to the given file path.
	if err := ioutil.WriteFile(path, []byte{}, 0644); err == nil {
		os.Remove(path)
	} else {
		return fmt.Errorf("unable to write to path: %s", path)
	}

	return nil
}

func validateFlagContents(img image) error {
	if _, exists := boardMap[img.board]; !exists {
		return fmt.Errorf("unrecognized or currently unsupported board: \"%s\"", img.board)
	}

	if !slices.Contains(supportedFirmwareTypes, strings.ToLower(img.firmware)) {
		return fmt.Errorf("unrecognized or currently unsupported firmware type: \"%s\" please specify one of %v", img.firmware, supportedFirmwareTypes)
	}

	// TODO(seancarpenter): Add support for arbitrary versions.
	if !slices.Contains(versionAliases, strings.ToLower(img.version)) {
		return fmt.Errorf("unrecognized or currently unsupported version: \"%s\" please specify one of %v. specific releases are not supported at this time", img.firmware, versionAliases)
	}

	return nil
}

func validateRequiredFlagsArePresent(flags flag.FlagSet) error {
	presentFlags := make(map[string]bool)
	flags.Visit(func(f *flag.Flag) { presentFlags[f.Name] = true })
	missingFlags := []string{}
	for _, flag := range requiredFlags {
		if !presentFlags[flag] {
			missingFlags = append(missingFlags, flag)
		}

	}
	if len(missingFlags) > 0 {
		return fmt.Errorf("missing the following required flags: %v", missingFlags)
	}
	return nil
}

// parseReleaseString builds a release struct from a string containing a
// release string.
func parseReleaseString(releaseString string) (*release, error) {
	match := releaseStringRegex.FindStringSubmatch(releaseString)
	if len(match) != 5 {
		return nil, fmt.Errorf("unable to parse release string \"%s\". Expected something like the following example: \"%s\"", releaseString, exampleReleaseString)
	}
	return &release{
		milestone:    match[1],
		majorVersion: match[2],
		minorVersion: match[3],
		patchNumber:  match[4],
	}, nil
}
