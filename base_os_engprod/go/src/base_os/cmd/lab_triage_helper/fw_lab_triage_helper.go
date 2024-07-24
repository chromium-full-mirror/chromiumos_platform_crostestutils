// Copyright 2019 The ChromiumOS Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"os/exec"
	"strings"
	"text/tabwriter"
	"time"

	"go.chromium.org/base-os-engprod-tools/internal/pkg/dutio"
)

const labstationTelemetryCmds = "grep guado_labstation-release /etc/lsb-release; " +
	"printf \"\n\"; " +
	"uptime; " +
	"printf \"\n\"; " +
	"elogtool list --utc | tail -n 10; " +
	"printf \"\n\"; " +
	"pgrep --list-full update_engine; " +
	"printf \"\n\";"

const warningMessage = `This utility assumes many things, like that you have the skylab utility in the
environment in which it is run and that you have cros in your DNS search path.
This is a convenience utility for firmware qual test environment health triage.
Feel free and encouraged to extend and enhance it: it should generally
complement monitoring and alerting efforts and any other longer term efforts.`

const autotestGetBranchesGerritAPIEndpoint = "https://chromium-review.googlesource.com/a/projects/chromiumos%2Fthird_party%2Fautotest/branches/"
const autotestGetCommitGerritAPIEndpoint = "https://chromium-review.googlesource.com/a/projects/chromiumos%2Fthird_party%2Fautotest/commits/"

type branch struct {
	name                string
	lastCommit          string
	lastCommitTimestamp time.Time
}

type dut struct {
	Hostname, Port, Labstation, Board, Model string
}

func sanitizeGobCurlOutput(output *[]byte) {
	// Responses from gob-curl currently begin with ")]}'".  Stripping that out
	// makes the response marshalable.
	if string((*output)[:4]) == ")]}'" {
		*output = (*output)[4:]
	} else {
		log.Println("Sanitizing gob-curl output may no longer be necessary.")
	}
}

func queryGerrit(endpoint string, resource string) map[string]*json.RawMessage {
	// TODO(seancarpenter): Check that gob-curl exists in the user's environment.
	// "gob-curl" is used instead of net/http due to the complexities of authenticating.
	gerritCmd := exec.Command("gob-curl", endpoint+resource)
	gerritCmdOut, err := gerritCmd.Output()
	if err != nil {
		log.Fatalf("gob-curl encountered: %s", err)
	}
	sanitizeGobCurlOutput(&gerritCmdOut)
	var gerritResponse map[string]*json.RawMessage
	err = json.Unmarshal(gerritCmdOut, &gerritResponse)
	if err != nil {
		log.Fatalf("json.Unmarshal encountered: %s", err)
	}
	return gerritResponse
}

func newDut(hostname string) dut {
	d := dut{Hostname: hostname}

	cmd := exec.Command("skylab", "dut-info", "-json", hostname)
	cmdOut, _ := cmd.Output()

	type skylabResponse struct {
		Common struct {
			Attributes []struct {
				Key   string `json:"key"`
				Value string `json:"value"`
			} `json:"attributes"`
			Labels struct {
				Board string `json:"board"`
				Model string `json:"model"`
			} `json:"labels"`
		} `json:"common"`
	}
	var s skylabResponse
	err := json.Unmarshal(cmdOut, &s)
	if err != nil {
		log.Fatalf("json.Unmarshal encountered: %s", err)
	}

	for _, attribute := range s.Common.Attributes {
		if attribute.Key == "servo_port" {
			d.Port = attribute.Value
		}
		if attribute.Key == "servo_host" {
			d.Labstation = attribute.Value
		}
	}

	d.Board = s.Common.Labels.Board
	d.Model = s.Common.Labels.Model

	return d
}

func main() {
	main := branch{name: "main"}
	prod := branch{name: "prod"}
	branches := [2]*branch{&main, &prod}
	for _, branch := range branches {
		gerritBranchResponse := queryGerrit(autotestGetBranchesGerritAPIEndpoint, branch.name)
		lastCommitWithQuotes := string(*gerritBranchResponse["revision"])
		branch.lastCommit = lastCommitWithQuotes[1 : len(lastCommitWithQuotes)-1]

		gerritCommitResponse := queryGerrit(autotestGetCommitGerritAPIEndpoint, branch.lastCommit)
		var gerritCommitter map[string]interface{}
		err := json.Unmarshal(*gerritCommitResponse["committer"], &gerritCommitter)
		if err != nil {
			log.Fatalf("json.Unmarshal encountered: %s", err)
		}
		branch.lastCommitTimestamp, err = time.Parse("2006-01-02 15:04:05.000000000",
			fmt.Sprintf("%v", (gerritCommitter["date"])))
		if err != nil {
			log.Fatalf("time.Parse encountered: %s", err)
		}

		fmt.Printf("The last %s commit is from %s.\n",
			branch.name,
			branch.lastCommitTimestamp.Format("Jan 2 at 15:04"))
	}

	h := time.Now().Sub(branches[1].lastCommitTimestamp).Hours()
	fmt.Printf("The prod version of autotest is about %.0f hours old.\n\n", h)

	duts := []dut{}

	poolPtr := flag.String("pool", "faft-cr50", "A pool of DUTs to operate on.")
	flag.Parse()

	fmt.Println(warningMessage)

	log.Print("Gathering DUT info via the skylab utility...")

	cmd := exec.Command("skylab", "dut-list", "-pool", *poolPtr)
	out, err := cmd.Output()
	if err != nil {
		log.Fatalf("<skylab dut-list> encountered: %s", err)
	}

	// Only operating on hostnames that begin with "chromeos1-" ensures DUTs that are not in the firmware lab
	// are not operated on.
	for _, hostname := range strings.Fields(string(out)) {
		if strings.HasPrefix(hostname, "chromeos1-") {
			duts = append(duts, newDut(hostname))
		}
	}

	log.Print("Summarizing DUT info...")
	w := tabwriter.NewWriter(os.Stdout, 0, 0, 3, ' ', 0)
	fmt.Fprintln(w, "Hostname\tBoard\tModel\tLabstation\tPort")
	for _, dut := range duts {
		fmt.Fprintln(w, dut.Hostname+"\t"+dut.Board+"\t"+dut.Model+"\t"+dut.Labstation+"\t"+
			dut.Port+"\t")
	}
	w.Flush()

	log.Print("Gathering and displaying key telemetry for labstations.")
	containsElement := func(array []string, element string) bool {
		for _, x := range array {
			if x == element {
				return true
			}
		}
		return false
	}
	labstations := []string{}
	for _, dut := range duts {
		if !containsElement(labstations, dut.Labstation) && dut.Labstation != "" {
			labstations = append(labstations, dut.Labstation)
		}
	}

	for _, labstation := range labstations {
		fmt.Println("Operating on ", labstation)
		stdout, stderr := dutio.ExecuteRemoteCommand(labstation, labstationTelemetryCmds)
		if stderr != "" {
			log.Fatalf("%s appears unhealthy. Running the telemetry commands encountered: %s", labstation, stderr)
		}
		fmt.Println("\n", stdout)
	}

	log.Print("Querying servos for their versions (note this depends on the servo consoles being in a functional state): ")
	for _, dut := range duts {
		if dut.Labstation == "" || dut.Port == "" {
			continue
		}
		servoVersionsCommand := fmt.Sprintf("dut-control -p %s servo_micro_version; dut-control -p %s servo_v4_version;", dut.Port, dut.Port)
		stdout, stderr := dutio.ExecuteRemoteCommand(dut.Labstation, servoVersionsCommand)
		if stderr != "" {
			fmt.Printf("%s has a servo for %s that appears unhealthy.  Running the servo version commands encountered: %s\n\n",
				dut.Labstation, dut.Hostname, stderr)
		} else {
			fmt.Printf("%s\n%s\n", dut.Hostname, stdout)
		}
	}
}
