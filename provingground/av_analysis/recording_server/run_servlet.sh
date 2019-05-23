#!/bin/bash
# Run the ffmpeg record and upload servlet.
source env/bin/activate
export GOOGLE_APPLICATION_CREDENTIALS=crosvideo-6c2cd30e9802.json
export FLASK_APP=servlet.py

flask run --host=0.0.0.0
