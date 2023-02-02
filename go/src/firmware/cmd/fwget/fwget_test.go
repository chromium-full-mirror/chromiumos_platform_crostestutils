// Copyright 2023 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package main

import (
	"flag"
	"fmt"
	"reflect"
	"testing"
)

// TestValidateFlagContents tests that validateFlagContents correctly throws
// an error when a flag with an unsupported or unrecognized value is passed.
func TestValidateFlagContents(t *testing.T) {
	testCases := []struct {
		img     image
		isValid bool
	}{
		{
			image{
				board:    "galtic",
				firmware: "ec",
				version:  "stable",
			},
			true,
		},
		{
			image{
				board:    "some unsupported board",
				firmware: "ec",
				version:  "stable",
			},
			false,
		},
		{
			image{
				board:    "galtic",
				firmware: "some unsupported firmware type",
				version:  "stable",
			},
			false,
		},
		{
			image{
				board:    "galtic",
				firmware: "ec",
				version:  "some unsupoorted version type.",
			},
			false,
		},
	}
	for _, tt := range testCases {
		tt := tt
		t.Run(fmt.Sprintf("%v", tt.img), func(t *testing.T) {
			err := validateFlagContents(tt.img)
			if err == nil && !tt.isValid {
				t.Errorf("Expected %+v to be invalid but returned no error", tt.img)
			}
			if err != nil && tt.isValid {
				t.Errorf("Expected %+v to be valid but returned an error: %s", tt.img, err)
			}
		})
	}
}

// TestValidateRequiredFlagsArePresent tests that validateRequiredFlagsArePresent
// correctly throws an error when a required flag is missing from the image struct.
func TestValidateRequiredFlagsArePresent(t *testing.T) {
	testCases := []struct {
		img     image
		isValid bool
	}{
		{
			image{
				board:    "galtic",
				firmware: "ec",
			},
			true,
		},
		{
			image{
				board: "galtic",
			},
			false,
		},
		{
			image{
				firmware: "ec",
			},
			false,
		},
		{
			image{},
			false,
		},
	}
	for _, tt := range testCases {
		tt := tt
		flagSet := flag.NewFlagSet("", flag.ExitOnError)
		if tt.img.board != "" {
			flagSet.String("board", "", "")
		}
		if tt.img.firmware != "" {
			flagSet.String("firmware", "", "")
		}
		flagSet.Set("board", tt.img.board)
		flagSet.Set("firmware", tt.img.firmware)
		flagSet.Parse([]string{})
		t.Run(fmt.Sprintf("%v", tt.img), func(t *testing.T) {
			err := validateRequiredFlagsArePresent(*flagSet)
			if err == nil && !tt.isValid {
				t.Errorf("Expected %+v to be invalid but returned no error", tt.img)
			}
			if err != nil && tt.isValid {
				t.Errorf("Expected %+v to be valid but returned an error: %s", tt.img, err)
			}
		})
	}
}

// TestParseReleaseString tests that a release string like R89-13606.459.0
// can be properly identified and marshalled into a release struct.
func TestParseReleaseString(t *testing.T) {
	testCases := []struct {
		releaseString string
		release       *release
	}{
		{
			"R89-13606.459.0",
			&release{
				milestone:    "R89",
				majorVersion: "13606",
				minorVersion: "459",
				patchNumber:  "0",
			},
		},
		{
			"someText/R12-123.569/before-the-string/R89-13606.459.0/someTextAfterwards",
			&release{
				milestone:    "R89",
				majorVersion: "13606",
				minorVersion: "459",
				patchNumber:  "0",
			},
		},
		{
			"X89-13606.459.0",
			nil,
		},
		{
			"R89-ABCD.459.0",
			nil,
		},

		{
			"R89-ABCD.459",
			nil,
		},
	}
	for _, tt := range testCases {
		tt := tt
		t.Run(tt.releaseString, func(t *testing.T) {
			t.Parallel()
			release, _ := parseReleaseString(tt.releaseString)
			if !reflect.DeepEqual(release, tt.release) {
				t.Errorf(
					"Expected release %+v\n but got %+v\n",
					tt.release,
					release)
			}
		})
	}
}
