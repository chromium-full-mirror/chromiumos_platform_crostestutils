# cr50 education plan

This doucment is intended to provide enough background for ChromeOS release testers to equip themselves to ensure that they are running the expected Google Security Chip (GSC) firmware during their testing. After reading this document, you will know how to check the GSC firmware version, and whether that version is expected at a particular ChromeOS milestone.

## Overview

Starting from the reef (electro) family, all the chromeOS devices come with a security chip that runs the cr50 firmware, the version of which, you must be cognizant of during milestone release testing, to ensure a meaningful system-under-test. Irrespective of the board family, every branch (Ex- R70, R71..) has a particular version of cr50 associated with it (note: this has not always been true, and may change, in which case, we intend to update this documentation in lock-step with any such change). While running the tests by any member of chromeos-test team, need to make sure the correct version of cr50 version as per the branch before testing.

> How to Check the cr50 version from DEV mode (enable VT-2), type the follwing commands in VT-2

* gsctool --any --fwver

> How to Check cr50 version with chrome://system

* look for cr50_version
* click expand and look for RW version string

> Find the Information related to cr50 version release [http://go/cr50-release-notes]

Important Note: It is expected that you cannot rollback to an older version, once you've installed a newer version.

#### Additional Reading

>* cr50 qualilication, setup of the DUT, cr50 DUTs at high touch lab overview: [http://go/fwcr50qual]
>* How to open CCD: [http://go/ccd-setup]

