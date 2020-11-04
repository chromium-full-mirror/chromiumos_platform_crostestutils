#!/usr/bin/env python3
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Find unused functions within the Autotest repository.

The Autotest repository is normally found in the chroot at
~/trunk/src/third_party/autotest/files/. It is huge, and has lots of dead code:
functions that were previously necessary, but are no longer used.  This script
serves to find functions and methods that now appear to be unused in Autotest.

A few other repostories, enumerated in REPOS_CALLING_AUTOTEST, rely on
functions defined in the Autotest repository. This script also checks those
repositories when determining which functions are unused.

It's hard to tell whether a function is called. To avoid breaking things, we're
taking a conservative definition of what might be a function call. If all
occurrences of the function's name appear to be function definitions—that is,
lines starting with "def my_function("—then we say it's unused. Otherwise,
assume it's used. As a result, this script will surely miss some unused
functions. For example, if a function name is only used in a comment, we
interpret that as the function being called. We're optimizing for safety here.
"""

import argparse
import copy
import logging
import os
import re
import subprocess
import sys
import time

SRC_DIR = os.path.expanduser('~/trunk/src/')
THIRD_PARTY_DIR = os.path.join(SRC_DIR, 'third_party')
AUTOTEST_DIR = os.path.join(THIRD_PARTY_DIR, 'autotest', 'files')
REPOS_CALLING_AUTOTEST = [
    AUTOTEST_DIR,
    os.path.join(SRC_DIR, 'platform', 'moblab', 'third_party', 'autotest'),
    os.path.join(THIRD_PARTY_DIR, 'autotest-private'),
    os.path.join(THIRD_PARTY_DIR, 'autotest-private-utils'),
    os.path.join(THIRD_PARTY_DIR, 'autotest-tests-cheets'),
    os.path.join(THIRD_PARTY_DIR, 'autotest-tests-lakitu'),
    os.path.join(THIRD_PARTY_DIR, 'autotest-tests-kumo'),
]


# Unix-style globs to always ignore when grepping.
ALWAYS_IGNORE_GLOBS = [
    '**/server/cros/faft/fw-testing-configs/**',
    '**/site_utils/rpm_control_system/BeautifulSoup.py',
]

# Unix-style globs of unittest paths to sometimes ignore when grepping.
UNITTEST_GLOBS = [
    '**_unittest.py',
    '**_functional_test.py'
]


def require_chroot():
    """Exit with status 2 if not in the chroot."""
    if not os.path.isfile('/etc/cros_chroot_version'):
        logging.error('Must run script from inside chroot.')
        sys.exit(2)


def require_dirs():
    """Exit with status 2 if the expected directories are not found."""
    for path in [SRC_DIR, THIRD_PARTY_DIR] + REPOS_CALLING_AUTOTEST:
        if not os.path.isdir(path):
            logging.error('Path not found: %s', os.path.abspath(path))
            sys.exit(2)


def parse_args(argv):
    """Interpret command-line args.

    Args:
        argv: A list of args passed into the script in the command-line.
              Should exclude the script name itself.
              Normally, this should be set to sys.argv[1:].

    Returns:
        argparse.Namespace with the following attributes:
            def_dirs: A list of directories to search recursively for function
                      definitions, defined relative to AUTOTEST_DIR.
                      Defaults to all of Autotest.
            verbose: Bool representing whether STDOUT should see debug logs.

    Raises:
        FileNotFoundError: If any of def_dirs cannot be found in AUTOTEST_DIR
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-d',
                        '--def-dirs',
                        nargs='*',
                        default=[''],
                        help='Directory/ies to search recursively for function '
                             'definitions, defined relative to Autotest.')
    parser.add_argument('-v',
                        '--verbose',
                        action='store_true',
                        help='Include verbose (debugging) logs in stdout')
    args = parser.parse_args(argv)
    for def_dir in args.def_dirs:
        full_path = os.path.join(AUTOTEST_DIR, def_dir)
        if not os.path.isdir(full_path):
            raise FileNotFoundError('def-dir %s not found' % full_path)
    return args


def grep(pattern, paths, exclude_unittests=False):
    """Run rg (ripgrep). Return a list of lines matching the pattern."""
    if not isinstance(paths, list):
        raise ValueError('rg expects paths to be a list; got %s' % paths)
    flags = [
        '--no-heading',
        '--no-filename',
        '--no-line-number',
        # Require word-boundaries.
        '-w',
    ]
    ignore_globs = copy.copy(ALWAYS_IGNORE_GLOBS)
    if exclude_unittests:
        ignore_globs.extend(UNITTEST_GLOBS)
    for glob in ignore_globs:
        flags.extend(['--iglob', "'!%s'" % glob])
    cmd = "rg %s '%s' %s" % (' '.join(flags), pattern, ' '.join(paths))
    proc = subprocess.run(cmd,
                          stdout=subprocess.PIPE,
                          universal_newlines=True,
                          shell=True)
    if proc.returncode == 1:
        return ''
    proc.check_returncode()
    return proc.stdout.strip()


def find_function_defs(search_dirs):
    """Find a list of all functions (not methods) defined in certain files.

    Args:
        files: A list of Python files to search.

    Returns:
        A list of strings, each representing the name of a function defined in
        one of the .py files.
    """
    # Regex will search for:
    # 1. Start of line
    # 2. Any amount of whitespace (including none)
    # 3. The string literal 'def '
    # 4. Any amount of word characters
    # In short, it searches for function/method definitions.
    def_lines = grep(r'^\s*def \w+', search_dirs, exclude_unittests=True)
    funcs = set()
    for line in def_lines.split('\n'):
        if not line:
            continue
        # Regex will try to match, at the start of the line:
        # 1. Any amount of whitespace (including none)
        # 2. The string literal 'def'
        # 3. Any nonzero amount of whitespace
        # 4. Any nonzero amount of word characters -- and capture this group
        # 5. Optionally, any amount of whitespace
        # 6. An open parenthesis
        # In short, it searches for function/method definitions,
        # and captures the name of the function/method.
        match = re.match(r'\s*def\s+(\w+)\s*\(', line)
        if match is None:
            logging.warning('Failed to find function def in rg line "%s"', line)
            continue
        funcs.add(match.group(1))
    return funcs


def is_function_used_in_dir(func, search_dir):
    """Determine if a function is used in search_dir, besides defining it."""
    try:
        called_lines = grep(r'%s' % func, [search_dir]).split('\n')
    except UnicodeDecodeError:
        return False
    # If any line uses the function name but doesn't define it,
    # then count the function as used.
    for line in called_lines:
        if not line:
            continue
        if re.match(r'\s*def %s' % func, line) is None:
            return True
    return False


def is_function_used(func):
    """Determine if a function is used anywhere."""
    for search_dir in REPOS_CALLING_AUTOTEST:
        if is_function_used_in_dir(func, search_dir):
            return True
    return False


def time_since(start_time):
    """Calculate the amount of time since start_time."""
    return time.time() - start_time


def main(argv):
    """Find all unused functions in requested subdirs of Autotest."""
    require_chroot()
    require_dirs()
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    # Find which functions we're going to check.
    def_dirs = [os.path.join(AUTOTEST_DIR, d) for d in args.def_dirs]
    logging.debug('Searching for function definitions in these dirs:')
    for def_dir in def_dirs:
        logging.debug('\t%s', def_dir)
    funcs = find_function_defs(def_dirs)
    logging.debug('Found %d unique function names', len(funcs))

    # Search every function in all search directories.
    unused_funcs = set()
    start_time = time.time()
    for i, func in enumerate(funcs):
        if not is_function_used(func):
            unused_funcs.add(func)
            logging.debug('Unused function: %s', func)
        # Give some feedback to the user.
        if (i+1) % 100 == 0:
            time_per_func = time_since(start_time) / (i+1)
            time_remaining = time_per_func * (len(funcs) - i)
            logging.info('Searched %d/%d; %d unused. %.2f seconds remain.',
                         i+1,
                         len(funcs),
                         len(unused_funcs),
                         time_remaining)
    logging.debug('Finished in %.2f seconds.', time_since(start_time))
    if unused_funcs:
        logging.info('Unused functions: %s', str(unused_funcs))
        logging.info('Total: %d', len(unused_funcs))
    else:
        logging.info('No unused functions detected.')


if __name__ == '__main__':
    main(sys.argv[1:])
