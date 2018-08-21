#!flask/bin/python
# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import ap_spec
import logging
import ndb_json
from flask import Flask, jsonify, abort, request, make_response
from google.appengine.ext import ndb

app = Flask(__name__)

# Chaos AP Device Methods

class ApDevice(ndb.Model):
    """Models an individual AP object with specs."""
    hostname = ndb.StringProperty(indexed=True)
    lock_status = ndb.BooleanProperty(indexed=True)
    lock_status_updated = ndb.DateTimeProperty(auto_now=True)
    locked_by = ndb.StringProperty()
    router_name = ndb.StringProperty()
    lab_label = ndb.StringProperty()
    ap_label = ndb.StringProperty()

@app.route('/')
def greeting():
    return 'Welcome to Chaos AP Page.\n'

@app.route('/devices/new', methods=['POST'])
def post():
    """
    Create a new AP in the datastore.
    Requires a hostname, lab_label, ap_label, and router_name.

    curl -i -H "Content-Type: application/json" -X POST -d \
    '{"hostname":"<HOSTNAME>"}' http://localhost:8080/devices/new

    @returns string if success, error 400 if fails.
    """
    if not request.json:
        abort(400)
    hostname = request.json['hostname']
    new_device = ApDevice(
        id = hostname,
        hostname = hostname,
        lock_status = False)
    if 'router_name' in request.json and type(request.json['router_name']) != unicode:
        make_response(jsonify({'error': 'Router name not unicode.'}), 400)
    elif 'ap_label' in request.json and type(request.json['ap_label']) != unicode:
        make_response(jsonify({'error': 'AP label not unicode.'}), 400)
    elif 'lab_label' in request.json and type(request.json['lab_label']) != unicode:
        make_response(jsonify({'error': 'Lab label not unicode.'}), 400)
    else:
        new_device.router_name = request.json['router_name']
        new_device.ap_label = request.json['ap_label']
        new_device.lab_label = request.json['lab_label']
    new_device.put()
    return jsonify(result=True, id=hostname)


@app.route('/devices/<hostname>', methods=['PUT', 'GET'])
def edit_ap_device(hostname):
    """Get and/or edit an AP.

    curl -i -H "Content-Type: application/json" <URL>/devices/<HOSTNAME>

    curl -i -H "Content-Type: application/json" -X PUT -d '{"ap_label":"<AP_LABEL>"}' \
    <URL>/devices/<HOSTNAME>

    """
    if request.method == 'GET':
        device_key = ndb.Key(ApDevice, hostname)
        device = device_key.get()
        device_js = ndb_json.dumps(device, indent=0)
        return device_js

    if request.method == 'PUT':
        device_key = ndb.Key(ApDevice, hostname)
        device = device_key.get()
        if 'router_name' in request.json:
            device.router_name = request.json['router_name']
        if 'ap_label' in request.json:
            device.ap_label = request.json['ap_label']
        if 'lab_label' in request.json:
            device.lab_label = request.json['lab_label']
        device.put()
        return jsonify(result=True, id=hostname, ap_label=device.ap_label, \
               lab_label=device.lab_label, router_name=device.router_name)


@app.route('/devices/lock', methods=['PUT'])
def lock_devices():
    """
    Locks devices given either a list of hostnames or a hostname string.

    curl -i -H "Content-Type: application/json" -X PUT \
    -d '{"hostname":"<HOSTNAME>", "locked_by":"<LDAP>"}' \
    <URL>/devices/lock

    @returns Hosts locked message if success, error 400 if fails.
    """
    if not request.json:
        abort(400)
    if type(request.json['hostname']) is list:
        hostnames = request.json['hostname']
        device_keys = [ndb.Key(ApDevice, x) for x in hostnames]
        devices = ndb.get_multi(device_keys)
        for d in devices:
            d.lock_status = True
        ndb.put_multi(devices)
        return jsonify(result=True, id=hostnames)
    elif 'hostname' in request.json and type(request.json['hostname']) != unicode:
        return make_response(jsonify({'error': 'Hostname not unicode.'}), 400)
    elif 'locked_by' in request.json and type(request.json['locked_by']) != unicode:
        return make_response(jsonify({'error': 'Need locked_by name'}), 400)
    else:
        hostname = request.json['hostname']
        device_key = ndb.Key(ApDevice, hostname)
        device = device_key.get()
        device.lock_status = True
        device.locked_by = request.json['locked_by']
        device.put()
        return jsonify(result=True, id=hostname)

@app.route('/devices/unlock', methods=['PUT'])
def unlock_devices():
    """
    Unlocks devices given either a list of hostnames or a hostname string.

    curl -i -H "Content-Type: application/json" -X PUT \
    -d '{"hostname":"<HOSTNAME>"}' <URL>/devices/unlock

    @returns Hosts unlocked message if success, error 400 if fails.
    """
    if not request.json:
        return make_response(jsonify({'error': 'Need json dict.'}), 400)
    elif 'hostname' in request.json and type(request.json['hostname']) != unicode:
        return make_response(jsonify({'error': 'Hostname not unicode.'}), 400)
    elif type(request.json['hostname']) is list:
        hostnames = request.json['hostname']
        device_keys = [ndb.Key(ApDevice, x) for x in hostnames]
        devices = ndb.get_multi(device_keys)
        for d in devices:
            d.lock_status = False
        ndb.put_multi(devices)
        return jsonify(result=True, id=hostnames)
    else:
        hostname = request.json['hostname']
        device_key = ndb.Key(ApDevice, hostname)
        device = device_key.get()
        device.lock_status = False
        device.locked_by = None
        device.put()
        return jsonify(result=True, id=hostname)

@app.route('/devices/delete', methods=['PUT'])
def delete():
    """Deletes AP in datastore given a hostname.

    curl -i -H "Content-Type: application/json" -X PUT \
    -d '{"hostname":"<HOSTNAME>"}' <URL>/devices/delete

    @returns Hosts deleted message if success.
    """
    hostname = request.json['hostname']
    device_key = ndb.Key(ApDevice, hostname)
    device_key.delete()
    return "%s deleted.\n" % hostname

# Querying devices.

@app.route('/devices/', methods=['GET'])
def get_devices():
    """Get list of devices in datastore.

    curl -i -H "Content-Type: application/json" <URL>/devices/

    @returns list of devices
    """
    devices_query = ApDevice.query()
    devices_entity = ndb_json.dumps(devices_query, indent=0, sort_keys=True)
    return devices_entity

@app.route('/devices/<hostname>', methods=['GET'])
def show_device(hostname):
    """Show one device with all fields.

    curl -i -H "Content-Type: application/json" <URL>/devices/<HOSTNAME>

    @returns python dict of device
    """
    device_key = ndb.Key(ApDevice, hostname)
    device = device_key.get()
    device_js = ndb_json.dumps(device, indent=0)
    return device_js

@app.route('/unlocked_devices/', methods=['GET'])
def get_unlocked_devices():
    """Get list of unlocked devices in datastore.

    curl -i -H "Content-Type: application/json" <URL>/unlocked_devices/

    @returns list of devices
    """
    devices_query = ApDevice.query(ApDevice.lock_status==False)
    devices_entity = ndb_json.dumps(devices_query, indent=0, sort_keys=True)
    return devices_entity

@app.route('/devices/location', methods=['PUT'])
def filter_by_location():
    """Get list of unlocked devices according to filter.

    curl -i -H "Content-Type: application/json" -X PUT \
    -d '{"ap_label":<AP_LABEL>, "lab_label":<LAB_LABEL>}' <URL>/location

    @returns list of devices
    """
    if not request.json:
        return make_response(jsonify({'error': 'Need json dict.'}), 400)

    devices_query = ApDevice.query(ApDevice.ap_label==request.json["ap_label"],
                                   ApDevice.lab_label==request.json["lab_label"],
                                   ApDevice.lock_status==False)
    devices_entity = ndb_json.dumps(devices_query, indent=0, sort_keys=True)
    return devices_entity

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
