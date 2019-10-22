// Copyright 2019 The Chromium OS Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package main

import (
	"flag"
	"fmt"
	"io/ioutil"
	"log"
	"os"
	"path/filepath"
	"strings"
)

// e2eTest contains metadata for a single end-to-end tests.
// End-to-end tests are typically found as directories within
// autotest/server/site_tests
type e2eTest struct {
	Name, TestClass, Description string
	Owners, RecentEditors        []string
}

func (t e2eTest) println() {
	fmt.Printf("%+v\n", t)
}

const (
	e2eTestClassFirmware = "FirmwareTest"
	e2eTestClassCr50     = "Cr50Test"
)

var autotestDir string
var siteTestsDir string

// getDefaultAutotestDir attempts to find Autotest if the -autotest_dir flag is
// not provided.
func getDefaultAutotestDir() string {
	defaultAutotestDir := "/"
	thisDir, err := os.Getwd()
	if err != nil {
		log.Fatal(err, " when getting current working directory")
	}
	thisDir, err = filepath.Abs(thisDir)
	if err != nil {
		log.Fatal(err, " when parsing cwd as an absolute path")
	}
	thisDir = filepath.ToSlash(thisDir)
	for _, dir := range strings.Split(thisDir, "/") {
		defaultAutotestDir = filepath.Join(defaultAutotestDir, dir)
		if dir == "src" {
			break
		}
	}
	defaultAutotestDir = filepath.Join(defaultAutotestDir, "third_party", "autotest", "files")
	return defaultAutotestDir
}

// Init parses command-line args to find autotest and site_tests
func init() {
	flag.StringVar(&autotestDir, "autotest_dir", getDefaultAutotestDir(), "The path to your autotest files")
	flag.Parse()
	if _, err := os.Stat(autotestDir); os.IsNotExist(err) {
		log.Fatalf("Could not find autotest directory: <%s>. Try supplying -autotest_dir", autotestDir)
	}
	siteTestsDir = filepath.Join(autotestDir, "server", "site_tests")
	if _, err := os.Stat(siteTestsDir); os.IsNotExist(err) {
		log.Fatalf("Could not find site_tests directory: <%s>", siteTestsDir)
	}
}

// Determine whether server/site_tests/$(testName)/*.py contains a certain string.
func testContains(testName, searchString string) bool {
	testDir := filepath.Join(siteTestsDir, testName)
	testDirContents, err := ioutil.ReadDir(testDir)
	if err != nil {
		log.Fatal(err, " when reading test directory ", testDir)
	}
	for _, fo := range testDirContents {
		testFile := filepath.Join(testDir, fo.Name())
		if filepath.Ext(testFile) != ".py" {
			continue
		}
		testFileContents, err := ioutil.ReadFile(testFile)
		if err != nil {
			log.Fatal(err, " when reading test file ", testFile)
		}
		if strings.Contains(string(testFileContents), searchString) {
			return true
		}
	}
	return false
}

// Collect and report info on all firmware end-to-end tests.
func main() {
	siteTestFileObjs, err := ioutil.ReadDir(siteTestsDir)
	if err != nil {
		log.Fatal(err, " when reading site_tests dir: ", siteTestsDir)
	}

	var e2eTests []e2eTest
	var t e2eTest
	for _, fo := range siteTestFileObjs {
		if !fo.IsDir() {
			continue
		}
		t = e2eTest{Name: fo.Name()}
		for _, testClass := range []string{e2eTestClassFirmware, e2eTestClassCr50} {
			if testContains(t.Name, testClass) {
				t.TestClass = testClass
				break
			}
		}
		if t.TestClass == "" {
			continue
		}
		// TODO: Add description
		// TODO: Add owners
		// TODO: Add recent editors
		e2eTests = append(e2eTests, t)
	}

	for _, t := range e2eTests {
		t.println()
	}
}
