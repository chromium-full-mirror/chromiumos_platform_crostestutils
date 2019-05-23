#!/bin/bash
# Install the dependencies for the server.
set -e

# Setup virtualenv
apt install python-pip
pip install virtualenv
python3 -m virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
