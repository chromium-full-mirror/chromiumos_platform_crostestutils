import os
import subprocess

from flask import Flask, request, jsonify
import google.cloud
from google.cloud import storage

app = Flask(__name__)


def record(filename, duration):
    """Record screen to |filename| and return error message if ffmpeg fails."""
    # TODO(vsuley): This is hacky: fix the underlying problem.
    # crbug.com/970936
    r1 = subprocess.call(['modprobe', '-vr', 'uvcvideo'])
    r2 = subprocess.call(['modprobe', '-v', 'uvcvideo'])
    if r1 != 0 or r2 != 0:
        return 'error reinstalling uvcvideo module'

    ffmpeg_path = '/root/bin/ffmpeg'
    ffmpeg = [ffmpeg_path, '-f', 'video4linux2', '-s', '1920x1080', '-r', '60',
              '-i', '/dev/video0', '-f', 'alsa', '-i', 'hw:1', '-qscale', '2',
              '-t', duration, '-strict', 'experimental', '-acodec', 'aac',
              '-vcodec', 'libx264', '-pix_fmt', 'yuv420p', '-loglevel',
              'error', '-y', filename]

    # TODO(vsuley): Is 10s too much? Figure out how small you can make
    # this number without breaking stuff. crbug.com/970938
    wait_time = int(duration) + 10
    try:
        subprocess.check_output(ffmpeg, stderr=subprocess.STDOUT,
                                timeout=wait_time)
        return None
    except subprocess.CalledProcessError as e:
        return e.output.decode('utf-8')
    except subprocess.TimeoutExpired as e:
        return 'ffmpeg command timed out after %s seconds' % wait_time


def upload(filename):
    """Upload the recorded video file to Storage."""
    BUCKET_NAME = 'cros-av-analysis'
    try:
        client = storage.Client()
        bucket = client.get_bucket(BUCKET_NAME)
        blob = bucket.blob(filename)

        blob.upload_from_filename(filename)
        blob.make_public()
    except google.cloud.exceptions as e:
        return 'Storage error: %s' % e

    return None


def outcome(status, filename):
    """Clean up generated video and return status as JSON."""
    try:
        os.remove(filename)
    except OSError as e:
        app.logger.info(e)

    if status['error'] is None:
        del status['error']

    return jsonify(status)


@app.route('/record_and_upload', methods=['POST'])
def record_and_upload():
    """
    Call ffmpeg to record screen then upload results to Storage.

    @params filename (required): Filename to give recording.
    @params duration (required): Length in seconds to record.

    @returns: JSON containing error status.

    """
    filename = request.args.get('filename')
    duration = request.args.get('duration')
    status = {}

    if not filename or not duration:
        status['error'] = 'filename and duration are required'
        return jsonify(status), 400

    app.logger.info('Starting recording')
    status['error'] = record(filename, duration)

    # Short circuit if ffmpeg failed.
    if status.get('error'):
        return outcome(status, filename)

    app.logger.info('Starting upload')
    status['error'] = upload(filename)
    return outcome(status, filename)
