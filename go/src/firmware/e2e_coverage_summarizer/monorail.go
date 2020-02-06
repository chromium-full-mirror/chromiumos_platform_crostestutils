// Copyright 2020 The Chromium OS Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

// monorail.go provides an interface to the Monorail API.

package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"

	"golang.org/x/oauth2"
	"golang.org/x/oauth2/google"
	"golang.org/x/oauth2/jwt"
	"google.golang.org/api/discovery/v1"
	"google.golang.org/api/option"
)

// timeout is the amount of time we give our context before we call it a timeout error.
const timeout time.Duration = 60 * time.Second

// discoveryURL is the starting point for using the discovery API.
// Found on https://chromium.googlesource.com/infra/infra/+/master/appengine/monorail/doc/example.py
const discoveryURL string = "https://bugs.chromium.org/_ah/api/discovery/v1/"

// requestParam contains the name of a parameter used in some URL querystring.
type requestParam string

// Below are all of the requestParams accepted by the monorail.issues.list API.
const (
	ProjectID         requestParam = "projectId"
	AdditionalProject requestParam = "additionalProject"
	Can               requestParam = "can"
	Label             requestParam = "label"
	MaxResults        requestParam = "maxResults"
	Owner             requestParam = "owner"
	PublishedMax      requestParam = "publishedMax"
	PublishedMin      requestParam = "publishedMin"
	Q                 requestParam = "q"
	Sort              requestParam = "sort"
	StartIndex        requestParam = "startIndex"
	Status            requestParam = "status"
	UpdatedMax        requestParam = "updatedMax"
	UpdatedMin        requestParam = "updatedMin"
)

// UnwrittenFwTestReqParams contains the canonical parameters to query Monorail for unwritten FW tests.
var UnwrittenFwTestReqParams = map[requestParam]string{
	Q:     "Component:OS>Firmware Component:Test>ChromeOS", // Space-separated means AND
	Label: "Test-Missing,Test-Flaky,Test-Escape",           // Comma-separated means OR
	Can:   "open"}                                          // Canned query filters down to open issues

// User contains all the data about an author/cc/owner returned by the monorail.issues.list API.
type User struct {
	Kind          string
	HTMLLink      string
	EmailBouncing bool // Actual field in API response: email_bouncing
	name          string
}

// Issue contains all the data about an issue returned by the monorail.issues.list API.
type Issue struct {
	Status            string
	Updated           string
	OwnerModified     string // Actual field in API response: owner_modified
	CanEdit           bool
	ComponentModified string // Actual field in API response: component_modified
	Author            User
	CC                []User
	ProjectID         string
	Labels            []string
	Kind              string
	CanComment        bool
	State             string
	StatusModified    string // Actual field in API response: status_modified
	Title             string
	Stars             int
	Published         string
	Owner             User
	Components        []string
	Starred           bool
	Summary           string
	ID                int
}

// IssuesListResponse contains all the data returned by the monorail.issues.list API.
type IssuesListResponse struct {
	Items        []Issue
	Kind         string
	TotalResults int
}

// credentialsFile finds the file containing the service account's credentials.
func credentialsFile() (string, error) {
	const credentialsBasename = "fw_monorail_credentials.json"
	const credentialsDir = "/usr/local/bin/"
	const credentialsURL = "https://gredelston.users.x20web.corp.google.com/fw_monorail_credentials.json"
	credentialsFile := credentialsDir + credentialsBasename
	if _, err := os.Stat(credentialsFile); os.IsNotExist(err) {
		log.Printf("Could not find credentials file. Please download from %s and move to %s.", credentialsURL, credentialsDir)
		return "", fmt.Errorf("file not found %s", credentialsFile)
	}
	return credentialsFile, nil
}

// oauthConfig creates a JWT oAuth config containing the service account's credentials.
func oauthConfig() (*jwt.Config, error) {
	f, err := credentialsFile()
	if err != nil {
		return nil, fmt.Errorf("finding credentials file: %v", err)
	}
	j, err := ioutil.ReadFile(f)
	if err != nil {
		return nil, fmt.Errorf("reading credentials file %s: %v", f, err)
	}
	cfg, err := google.JWTConfigFromJSON(j, "https://www.googleapis.com/auth/userinfo.email")
	if err != nil {
		return nil, fmt.Errorf("generating JWT config: %v", err)
	}
	return cfg, nil
}

// querystring constructs the Query portion of a URL based on key-value pairs.
// Special characters are escaped. The "?" preceding the querystring is not included.
// Example: {"foo": "bar", "baz": "4 5"} --> "foo=bar&baz=4%205"
func querystring(params map[requestParam]string) string {
	var paramQueries []string
	for k, v := range params {
		paramQueries = append(paramQueries, fmt.Sprintf("%s=%s", k, url.QueryEscape(v)))
	}
	return strings.Join(paramQueries, "&")
}

// issuesListURL constructs a GET URL to query the monorail.issues.list API.
func issuesListURL(ctx context.Context, httpClient *http.Client, params map[requestParam]string) (string, error) {
	svc, err := discovery.NewService(ctx, option.WithHTTPClient(httpClient), option.WithEndpoint(discoveryURL))
	if err != nil {
		return "", fmt.Errorf("connecting to Discovery: %v", err)
	}
	rest, err := svc.Apis.GetRest("monorail", "v1").Do()
	if err != nil {
		return "", fmt.Errorf("getting Monorail REST description: %v", err)
	}
	method := rest.Resources["issues"].Methods["list"]
	u := strings.Join([]string{rest.RootUrl, rest.ServicePath, method.Path}, "")
	u = strings.ReplaceAll(u, "{projectId}", "chromium")
	if len(params) > 0 {
		u = fmt.Sprintf("%s?%s", u, querystring(params))
	}
	return u, nil
}

// IssuesList polls the monorail.issues.list API for all issues matching certain parameters.
func IssuesList(params map[requestParam]string) ([]Issue, error) {
	log.Print("Going to query Monorail for issues matching params:")
	if len(params) > 0 {
		for k, v := range params {
			log.Printf("\t%s: %s", k, v)
		}
	} else {
		log.Print("\nnil")
	}

	// Set a timeout for all our requests
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	// Create an authenticated HTTP client
	cfg, err := oauthConfig()
	if err != nil {
		return nil, fmt.Errorf("creating OAuth config: %v", err)
	}
	httpClient := oauth2.NewClient(ctx, cfg.TokenSource(ctx))

	// Send a request to the API
	u, err := issuesListURL(ctx, httpClient, params)
	if err != nil {
		return nil, fmt.Errorf("constructing API URL: %v", err)
	}
	log.Printf("Sending GET request to %s\n", u)
	hResponse, err := httpClient.Get(u)
	if err != nil {
		return nil, fmt.Errorf("sending API call to \"%s\": %v", u, err)
	}
	log.Print("Response received.")

	// Parse response
	// Note: A few fields will not successfully unmarshal from the blob.
	// json.Unmarshal attempts to match field names from the response blob to attributes of IssuesListResponse (and its children) in a case-insensitive way.
	// Four fields of the response contain underscores in their names.
	// Golint forbids us to use underscores in Go names.
	// Therefore, for those four fields, we are unable to create struct fields which will be matched by json.Unmarshal.
	// Luckily, we aren't using any of those fields (for now), so we can just let them not get populated.
	blob, err := ioutil.ReadAll(hResponse.Body)
	if err != nil {
		return nil, fmt.Errorf("reading response body: %v", err)
	}
	var issuesListResponse IssuesListResponse
	if err = json.Unmarshal(blob, &issuesListResponse); err != nil {
		return nil, fmt.Errorf("unmarhsalling API response body: %v", err)
	}
	return issuesListResponse.Items, nil
}
