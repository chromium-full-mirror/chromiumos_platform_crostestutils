# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Functions which return "actions" that modify a given ControlFile object."""

# Each action should take in a single ControlFile and return a boolean value
# of whether the control file was modified or not.

def remove_contacts(emails):
    """Return an action which removes the given list of emails from 'contacts'.

    Args:
        emails: a list of strings, e.g. ['foo@google.com']

    Returns:
        An action function that acts on a ControlFile and returns a boolean.
    """
    def output(cf):
        if 'contacts' not in cf.metadata:
            return False
        modified = False
        for email in emails:
            if email in cf.metadata['contacts']:
                cf.metadata['contacts'].remove(email)
                modified = True
        return modified
    return output
