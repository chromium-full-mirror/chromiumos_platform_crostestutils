# -*- coding: utf-8 -*-

import unittest
import requests
import json

class TestChaosApiUsingRequests(unittest.TestCase):
    def test_create_new_AP(self):
        response = requests.post('http://localhost:8080/devices/new', \
                   json={"hostname":"test0", "lab_label":"lab", \
                         "ap_label":"ap", "router_name":"router"})
        self.assertEqual(response.json(), {'id':'test0', 'result': True})

    def test_create_another_AP(self):
        response = requests.post('http://localhost:8080/devices/new', \
                   json={"hostname":"test1", "lab_label":"lab", \
                         "ap_label":"ap", "router_name":"router"})
        self.assertEqual(response.json(), {'id':'test1', 'result': True})

    def test_lock_AP(self):
        response = requests.put('http://localhost:8080/devices/lock', \
                   json={"hostname":"test0", "locked_by":"admin"})
        self.assertEqual(response.json(), {'id':'test0', 'result': True})

    def test_unlock_AP(self):
        response = requests.put('http://localhost:8080/devices/unlock', \
                   json={"hostname":"test0"})
        self.assertEqual(response.json(), {'id':'test0', 'result': True})

    def test_lock_list_AP(self):
        response = requests.put('http://localhost:8080/devices/lock', \
                   json={"hostname":["test0", "test1"], "locked_by":"admin"})
        self.assertEqual(response.json(), {'id':['test0', 'test1'], \
                         "result": True})

    def test_unlock_list_AP(self):
        response = requests.put('http://localhost:8080/devices/unlock', \
                   json={"hostname":["test0", "test1"]})
        self.assertEqual(response.json(), {'id':['test0', 'test1'], \
                         'result': True})

    def test_edit_ap(self):
        response = requests.put('http://localhost:8080/devices/test0', \
                   json={"lab_label":"newlablabel"})
        self.assertEqual(response.json(), {"id":"test0", \
                         'lab_label':'newlablabel', \
                         "ap_label":"ap", "router_name":"router", \
                         'result': True})

        response = requests.put('http://localhost:8080/devices/test0', \
                   json={"ap_label":"newaplabel"})
        self.assertEqual(response.json(), {'id':'test0', \
                         'lab_label':'newlablabel', "ap_label":"newaplabel", \
                          "router_name":"router", 'result': True})

        response = requests.put('http://localhost:8080/devices/test0', \
                   json={"router_name":"newroutername"})
        self.assertEqual(response.json(), {'id':'test0', \
                         'lab_label':'newlablabel', "ap_label":"newaplabel", \
                         "router_name":"newroutername", 'result': True})

if __name__ == "__main__":
    unittest.main()
