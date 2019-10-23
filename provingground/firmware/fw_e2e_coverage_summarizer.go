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
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"
)

// daysSinceRecentCommit specifies how far to look back when determining
// who recently committed changes to a test.
const daysSinceRecentCommit = 60

// gitLogAuthorEmailRegexp captures an author's email address from git log.
var gitLogAuthorEmailRegexp = regexp.MustCompile(`Author:[^<]+<([^>]+)>`)

// controlFileOwnersRegexp captures the AUTHOR line from a test control file.
var controlFileOwnersRegexp = regexp.MustCompile(`AUTHOR = "([^"]+)"`)

// e2eTest contains metadata for a single end-to-end tests.
// End-to-end tests are typically found as directories within
// autotest/server/site_tests
type e2eTest struct {
	Name, TestClass, Description string
	Owners, RecentEditors        []string
}

// e2eTest.println displays the test struct's field names and values.
func (t e2eTest) println() {
	fmt.Printf("%+v\n", t)
}

// e2eTest.dir returns the test's folder within autotest/server/site_tests/
func (t e2eTest) dir() string {
	return filepath.Join(siteTestsDir, t.Name)
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

// e2eTest.containsStr determines whether server/site_tests/$(t.Name)/*.py contains searchString.
func (t e2eTest) containsStr(searchString string) (bool, error) {
	testDir := filepath.Join(siteTestsDir, t.Name)
	testDirContents, err := ioutil.ReadDir(testDir)
	if err != nil {
		return false, fmt.Errorf("%v when reading test directory %s", err, testDir)
	}
	for _, fo := range testDirContents {
		testFile := filepath.Join(testDir, fo.Name())
		if filepath.Ext(testFile) != ".py" {
			continue
		}
		testFileContents, err := ioutil.ReadFile(testFile)
		if err != nil {
			return false, fmt.Errorf("%v when reading test file %s", err, testFile)
		}
		if strings.Contains(string(testFileContents), searchString) {
			return true, nil
		}
	}
	return false, nil
}

// contains determines whether an array of strings contains a given string.
func contains(arr []string, elem string) bool {
	for _, x := range arr {
		if x == elem {
			return true
		}
	}
	return false
}

// e2e.setRecentEditors finds all authors who have committed changes to the test
// within the past $(daysSinceRecentCommit) days.
func (t *e2eTest) setRecentEditors() error {
	sinceDate := time.Now().AddDate(0, 0, -1*daysSinceRecentCommit)
	gitLogCmd := exec.Command(
		"git",
		"--no-pager",
		"log",
		"--since",
		sinceDate.Format(time.RFC3339), ".")
	gitLogCmd.Dir = t.dir()
	gitLogOutput, err := gitLogCmd.Output()
	if err != nil {
		return fmt.Errorf("%v when running %s", err, gitLogCmd)
	}
	authorMatches := gitLogAuthorEmailRegexp.FindAllSubmatch(gitLogOutput, -1)
	authors := []string{}
	for _, authorMatch := range authorMatches {
		author := strings.TrimSpace(string(authorMatch[1]))
		if !contains(authors, author) {
			authors = append(authors, author)
		}
	}
	t.RecentEditors = authors
	return nil
}

// e2eTest.setOwners populates e2eTest.Owners based on the AUTHORS line of the control file
func (t *e2eTest) setOwners() error {
	controlFile := t.findOneControlFile()
	controlFileBytes, err := ioutil.ReadFile(controlFile)
	if err != nil {
		return fmt.Errorf("%v when reading control file %s", err, controlFile)
	}
	ownerMatch := controlFileOwnersRegexp.FindStringSubmatch(string(controlFileBytes))
	for _, owner := range strings.Split(ownerMatch[1], ",") {
		t.Owners = append(t.Owners, strings.TrimSpace(owner))
	}
	return nil
}

// e2eTest.findOneControlFile returns the path to the alphabetically first control file for t.
func (t e2eTest) findOneControlFile() string {
	controlFiles := t.findAllControlFiles()
	return controlFiles[0]
}

// e2eTest.findAllControlFiles returns a slice of filepaths to the control files for t.
func (t e2eTest) findAllControlFiles() []string {
	controlFiles := []string{}
	fileObjs, _ := ioutil.ReadDir(t.dir())
	for _, fo := range fileObjs {
		if strings.HasPrefix(fo.Name(), "control") {
			controlFiles = append(controlFiles, filepath.Join(t.dir(), fo.Name()))
		}
	}
	sort.Strings(controlFiles)
	return controlFiles
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
			hasClass, err := t.containsStr(testClass)
			if err != nil {
				log.Fatalf("%v for test %s", err, t.Name)
			}
			if hasClass {
				t.TestClass = testClass
				break
			}
		}
		if t.TestClass == "" {
			continue
		}
		// TODO: Add description
		for _, f := range []func() error{t.setRecentEditors, t.setOwners} {
			err := f()
			if err != nil {
				log.Fatalf("%v for test %s", err, t.Name)
			}
		}
		e2eTests = append(e2eTests, t)
	}

	for _, t := range e2eTests {
		t.println()
	}
}
