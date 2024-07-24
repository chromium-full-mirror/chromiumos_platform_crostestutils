// Copyright 2019 The ChromiumOS Authors
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

// controlFileAuthorRegexp captures the AUTHOR line from a test control file.
var controlFileAuthorRegexp = regexp.MustCompile(`AUTHOR = "+([^"]+)"`)

// controlFilePurposeRegexp captures the PURPOSE line from a test control file.
var controlFilePurposeRegexp = regexp.MustCompile(`PURPOSE = "+([^"]+)"`)

// e2eTestClassFirmware and e2eTestClassCr50 contain the names of Autotest classes
// which indicate that a site_test is a firmware test.
const (
	e2eTestClassFirmware = "FirmwareTest"
	e2eTestClassCr50     = "Cr50Test"
)

// autotestDir is a filepath to the root directory of autotest.
var autotestDir string

// siteTestsDir is a filepath to autotestDir/server/site_tests/.
var siteTestsDir string

// contains determines whether an array of strings contains a given string.
func contains(arr []string, elem string) bool {
	for _, x := range arr {
		if x == elem {
			return true
		}
	}
	return false
}

// e2eTest contains metadata for a single end-to-end tests.
// End-to-end tests are typically found as directories within
// autotest/server/site_tests
type e2eTest struct {
	Name, TestClass, Purpose string
	Authors, RecentEditors   []string
}

// e2eTest.println displays the test struct's field names and values.
func (t *e2eTest) println() {
	log.Printf("%+v\n", *t)
}

// e2eTest.dir returns the test's folder within autotest/server/site_tests/
func (t *e2eTest) dir() string {
	return filepath.Join(siteTestsDir, t.Name)
}

// e2eTest.containsStr determines whether server/site_tests/$(t.Name)/*.py contains searchString.
func (t *e2eTest) containsStr(searchString string) (bool, error) {
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

// e2eTest.setClass searches the test's .py files for any strings that indicate
// that the test is a firmware class. If any matches are found, then t.TestClass
// is set to the matching string, and the function returns true (indicating that
// the test is a firmware test).
// Otherwise, the function returns false (indicating that the test is not a
// firmware test).
func (t *e2eTest) setClass() bool {
	for _, testClass := range [2]string{e2eTestClassFirmware, e2eTestClassCr50} {
		hasClass, err := t.containsStr(testClass)
		if err != nil {
			log.Fatalf("%v for test %s", err, t.Name)
		}
		if hasClass {
			t.TestClass = testClass
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

// newE2ETest creates a new e2eTest based on its name, and fills in its fields.
// If the test is not a firmware test, instead return a null pointer with no error.
func newE2ETest(name string) (*e2eTest, error) {
	t := &e2eTest{Name: name}
	if !t.setClass() {
		return nil, nil
	}
	for _, f := range []func() error{t.setRecentEditors, t.setAuthors, t.setPurpose} {
		err := f()
		if err != nil {
			return nil, fmt.Errorf("test %s: %v", t.Name, err)
		}
	}
	return t, nil
}

// captureGroupFromFileContents runs a Regexp on the contents of a file,
// and returns the first capture group (or "" if no match is found).
func captureGroupFromFileContents(fp string, re *regexp.Regexp) (string, error) {
	fileBytes, err := ioutil.ReadFile(fp)
	if err != nil {
		return "", fmt.Errorf("%v when reading file %s", err, fp)
	}
	match := re.FindStringSubmatch(string(fileBytes))
	if match != nil {
		return strings.TrimSpace(match[1]), nil
	}
	return "", nil
}

// e2eTest.setAuthors populates e2eTest.Authors based on the AUTHORS line of the control file
func (t *e2eTest) setAuthors() error {
	controlFile := t.findOneControlFile()
	authors, err := captureGroupFromFileContents(controlFile, controlFileAuthorRegexp)
	if err != nil {
		return fmt.Errorf("%v when setting Authors", err)
	}
	for _, author := range strings.Split(authors, ",") {
		t.Authors = append(t.Authors, strings.TrimSpace(author))
	}
	return nil
}

// e2eTest.setPurpose populates e2eTest.Purpose based on the PURPOSE line of the control file.
// If there is a file named "control", then its PURPOSE is assumed to be the source-of-truth.
// Otherwise, all unique PURPOSEs from control-files are concatenated and semicolon-deliminated.
func (t *e2eTest) setPurpose() error {
	allPurposes := []string{}
	for _, controlFile := range t.findAllControlFiles() {
		purpose, err := captureGroupFromFileContents(controlFile, controlFilePurposeRegexp)
		if err != nil {
			return fmt.Errorf("%v when setting Purpose", err)
		}
		if !contains(allPurposes, purpose) {
			allPurposes = append(allPurposes, purpose)
		}
		if filepath.Base(controlFile) == "control" {
			break
		}
	}
	t.Purpose = strings.Join(allPurposes, "; ")
	return nil
}

// e2eTest.findOneControlFile returns the path to the alphabetically first control file for t.
func (t *e2eTest) findOneControlFile() string {
	controlFiles := t.findAllControlFiles()
	return controlFiles[0]
}

// e2eTest.findAllControlFiles returns a slice of filepaths to the control files for t.
func (t *e2eTest) findAllControlFiles() []string {
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

// collectExistingE2ETests finds all e2e tests that are already written in Autotest,
// and collects information about them.
func collectExistingE2ETests() ([]*e2eTest, error) {
	siteTestFileObjs, err := ioutil.ReadDir(siteTestsDir)
	if err != nil {
		return nil, fmt.Errorf("reading site_tests dir (%s): %v", siteTestsDir, err)
	}
	var e2eTests []*e2eTest
	for _, fo := range siteTestFileObjs {
		if !fo.IsDir() {
			continue
		}
		if t, err := newE2ETest(fo.Name()); err != nil {
			return nil, err
		} else if t != nil {
			e2eTests = append(e2eTests, t)
		}
	}
	return e2eTests, nil
}

// Init parses command-line args to find autotest and site_tests.
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

// Main collects and reports info on all firmware end-to-end tests.
func main() {
	existingTests, err := collectExistingE2ETests()
	if err != nil {
		log.Fatalf("collecting existing tests: %v", err)
	}

	// Print results
	if len(existingTests) > 0 {
		log.Print("### Existing end-to-end FW tests ###")
		for _, t := range existingTests {
			t.println()
		}
		log.Printf("Total: %d", len(existingTests))
	} else {
		log.Print("No end-to-end FW tests found.")
	}
	log.Print()
	log.Print("### TOTALS ###")
	log.Printf("Existing e2e tests:          %d", len(existingTests))

	var unowned int
	broadGroups := []string{
		"Chrome OS Team",
		"Intel",
		"The Chromium OS Authors",
	}
	for _, t := range existingTests {
		if len(t.Authors) == 1 && contains(broadGroups, (t.Authors[0])) {
			unowned++
		}
	}
	log.Printf("Tests without maintainers:   %d", unowned)
}
