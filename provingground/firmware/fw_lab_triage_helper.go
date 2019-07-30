// Copyright 2019 The Chromium OS Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

package main

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"reflect"
	"regexp"
	"strings"
	"text/tabwriter"
)

const labstationTelemetryCmds = "grep guado_labstation-release /etc/lsb-release; " +
	"printf \"\n\"; " +
	"uptime; " +
	"printf \"\n\"; " +
	"mosys eventlog list | tail -n 10; " +
	"printf \"\n\"; " +
	"pgrep --list-full update_engine; " +
	"printf \"\n\";"

const warningMessage = "This utility asssumes many things, like that you have " +
	"atest in the environment in which it is run, that you have cros in " +
	"your DNS search path, and that you have configured your environment to " +
	"use the testing_rsa key on lab DUTs.  This is just a convenience " +
	"utility for firmware qual test environment health triage.  Feel free " +
	"and encouraged to extend and enhance it, but in the long term, it " +
	"should be mostly obviated by monitoring and alerting."

type dut struct {
	Hostname, Port, Labstation, Board, Model, Status, LockStatus, LockReason string
}

func newDut(hostname string) dut {
	d := dut{Hostname: hostname}

	regexMap := map[string]string{
		"Port":       `servo_port : (?P<Port>.*)`,
		"Labstation": `servo_host : (?P<Labstation>.*)`,
		"Board":      `board:(?P<Board>.*)`,
		"Model":      `model:(?P<Model>.*)`,
		"Status":     `Status: (?P<Status>.*)`,
		"LockStatus": `Locked: (?P<LockStatus>.*)`,
		"LockReason": `Lock Reason: (?P<LockReason>.*)`,
	}

	cmd := exec.Command("atest", "host", "stat", hostname)
	out, _ := cmd.Output()

	for field, re := range regexMap {
		match := regexp.MustCompile(re).FindStringSubmatch(string(out))
		// The LockReason field can be empty if the DUT is not locked.
		if len(match) != 2 && field != "LockReason" {
			log.Printf("Skipping %s on %s.  This could be ok if a DUT is only partially through the deployment checklist.", field, hostname)
			continue
		} else {
			reflect.ValueOf(&d).Elem().FieldByName(field).SetString(match[1])
		}
	}

	return d
}

func sendSSHCommand(host, remoteCmd string) (outs string, err error) {
	cmd := exec.Command("ssh", "-o", "StrictHostKeyChecking=no", "root@"+host, remoteCmd)
	out, err := cmd.Output()
	outs = string(out)
	return
}

func main() {
	duts := []dut{}

	fmt.Println(warningMessage)

	log.Print("Gathering DUT info via atest...")
	// TODO(kmshelton): Support arbitrary pools.  Remember to sanitize for chromeos1 (high
	// touch lab) when adding arbitrary pool support, as we would not want to do operations
	// like ssh'ing to labstations in the low touch lab.  The current hardcoded pool, it is
	// safe to assume no low touch lab devices are operated upon.
	cmd := exec.Command("atest", "host", "list", "--hostnames-only", "--label=pool:faft-cr50")
	out, err := cmd.Output()
	if err != nil {
		log.Fatalf("<atest host list> encountered: %s", err)
	}
	hostnames := strings.Fields(string(out))

	for _, hostname := range hostnames {
		duts = append(duts, newDut(hostname))
	}

	log.Print("Summarizing DUT info...")
	w := tabwriter.NewWriter(os.Stdout, 0, 0, 3, ' ', 0)
	fmt.Fprintln(w, "Hostname\tBoard\tModel\tStatus\tLabstation\tPort\tLockStatus\tLockReason")
	for _, dut := range duts {
		fmt.Fprintln(w, dut.Hostname+"\t"+dut.Board+"\t"+dut.Model+"\t"+dut.Status+"\t"+dut.Labstation+"\t"+
			dut.Port+"\t"+dut.LockStatus+"\t"+dut.LockReason+"\t")
	}
	w.Flush()

	log.Print("Gathering and displaying key telemetry for labstations.")
	// TODO(kmshelton): Do this without keeping two approximately-identical memos.
	labstations := []string{}
	labstationsSeen := make(map[string]bool)
	for _, dut := range duts {
		if _, ok := labstationsSeen[dut.Labstation]; !ok && dut.Labstation != "" {
			labstations = append(labstations, dut.Labstation)
			labstationsSeen[dut.Labstation] = true
		}
	}

	// TODO(kmshelton): Migrate to using x/crypto/ssh (here and eleswehere) and handle network errors.
	for _, labstation := range labstations {
		fmt.Println("Operating on ", labstation)
		out, err := sendSSHCommand(labstation, labstationTelemetryCmds)
		if err != nil {
			log.Fatalf("Gathering labstation telemetry encountered: %s when interfacing with %s.  Is the labstation pingable?  Do you have lab ssh credentials setup?", err, labstation)
		}
		fmt.Println("\n", out)
	}

	log.Print("Querying servos for their versions (note this depends on the servo consoles being in a functional state): ")
	for _, dut := range duts {
		if dut.Labstation == "" || dut.Port == "" {
			continue
		}
		out, err := sendSSHCommand(dut.Labstation, "dut-control -p "+dut.Port+" servo_micro_version; dut-control -p "+dut.Port+" servo_v4_version;")
		if err != nil {
			log.Fatalf("Querying servos encountered: %s when interfacing with %s.  Is the labstation pingable?  Do you have lab ssh credentials setup?", err, dut.Labstation)
		}
		fmt.Println(dut.Hostname, ": ", out)
	}
}
