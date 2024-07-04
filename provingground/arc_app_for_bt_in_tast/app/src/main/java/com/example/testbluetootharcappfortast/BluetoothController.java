/*
 * Copyright 2024 The ChromiumOS Authors
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

package com.example.testbluetootharcappfortast;

import android.Manifest;
import android.bluetooth.BluetoothAdapter;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;

import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.ContextCompat;
import androidx.activity.result.ActivityResultLauncher;

import java.util.ArrayList;

public class BluetoothController {
    private Constant.AVAILABILITY m_availability_stat;
    private Constant.PERMISSION m_permission_stat;
    private Constant.ACTIVATION m_activation_stat;
    private final BluetoothAdapter m_adapter;
    private final Context m_context;
    private final ArrayList<String> m_bt_permissions = new ArrayList<>();

    public BluetoothController(AppCompatActivity activity) {
        m_adapter = BluetoothAdapter.getDefaultAdapter();
        m_context = activity.getApplicationContext();

        m_bt_permissions.add(Manifest.permission.BLUETOOTH);
        m_bt_permissions.add(Manifest.permission.BLUETOOTH_ADMIN);
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S) {
            m_bt_permissions.add(Manifest.permission.BLUETOOTH_CONNECT);
        }
    }

    private boolean assertStats(
            Constant.AVAILABILITY supported,
            Constant.PERMISSION granted,
            Constant.ACTIVATION enabled) {

        syncStats();
        if (supported != null && m_availability_stat != supported) {
            return true;
        }
        if (granted != null && m_permission_stat != granted) {
            return true;
        }
        if (enabled != null && m_activation_stat != enabled) {
            return true;
        }
        return false;
    }

    public Constant.AVAILABILITY getAvailabilityStatus() {
        return m_availability_stat;
    }

    public Constant.PERMISSION getPermissionStatus() {
        return m_permission_stat;
    }

    public Constant.ACTIVATION getActivationStatus() {
        return m_activation_stat;
    }

    public void syncStats() {
        if (m_adapter != null) {
            m_availability_stat = Constant.AVAILABILITY.SUPPORTED;
        } else {
            m_availability_stat = Constant.AVAILABILITY.NOT_SUPPORTED;
        }

        boolean allGranted = true;
        int expectedPermissionState = PackageManager.PERMISSION_GRANTED;
        for (String p : m_bt_permissions) {
            if (ContextCompat.checkSelfPermission(m_context, p) != expectedPermissionState) {
                allGranted = false;
                break;
            }
        }
        if (allGranted) {
            m_permission_stat = Constant.PERMISSION.ALL_GRANTED;
        } else {
            m_permission_stat = Constant.PERMISSION.NOT_READY;
        }

        if (m_adapter != null && m_adapter.isEnabled()) {
            m_activation_stat = Constant.ACTIVATION.ENABLED;
        } else {
            m_activation_stat = Constant.ACTIVATION.DISABLED;
        }
    }

    public void bluetoothControl(ActivityResultLauncher<Intent> launcher, boolean turnOn) {
        Constant.ACTIVATION wantedActivationStat = turnOn ? Constant.ACTIVATION.DISABLED : Constant.ACTIVATION.ENABLED;
        // BluetoothAdapter.ACTION_REQUEST_ENABLE is hidden and can only be hard-coded.
        String intentAction = turnOn ? BluetoothAdapter.ACTION_REQUEST_ENABLE : "android.bluetooth.adapter.action.REQUEST_DISABLE";

        if (assertStats(
                Constant.AVAILABILITY.SUPPORTED,
                Constant.PERMISSION.ALL_GRANTED,
                wantedActivationStat)
        ) {
            throw new RuntimeException("Skipped");
        }
        Intent enableBtIntent = new Intent(intentAction);
        launcher.launch(enableBtIntent);
    }

    public void requestPermissions(AppCompatActivity activity) {
        if (assertStats(
                Constant.AVAILABILITY.SUPPORTED,
                Constant.PERMISSION.NOT_READY,
                null)
        ) {
            throw new RuntimeException("Skipped");
        }
        activity.requestPermissions(m_bt_permissions.toArray(new String[0]), Constant.REQUEST_CODE_PERMISSION);
    }
}
