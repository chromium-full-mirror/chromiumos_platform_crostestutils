/*
 * Copyright 2024 The ChromiumOS Authors
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

package com.example.testbluetootharcappfortast;

import android.os.Bundle;
import android.os.Handler;
import android.widget.TextView;
import android.content.Intent;

import androidx.activity.result.contract.ActivityResultContracts;
import androidx.appcompat.app.AppCompatActivity;
import androidx.activity.result.ActivityResultLauncher;

public class MainActivity extends AppCompatActivity {
    private TextView m_txt_bt_availability;
    private TextView m_txt_bt_permission;
    private TextView m_txt_bt_activation;
    private BluetoothController m_bt_controller;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        m_bt_controller = new BluetoothController(this);
        ActivityResultLauncher<Intent> enableBtLauncher = registerForActivityResult(
                new ActivityResultContracts.StartActivityForResult(), result -> {
                }
        );

        findViewById(R.id.btn_request_bt).setOnClickListener(v -> {
            m_bt_controller.requestPermissions(this);
        });

        findViewById(R.id.btn_turn_on_bt).setOnClickListener(v -> {
            m_bt_controller.enableBluetooth(enableBtLauncher);
        });

        m_txt_bt_availability = findViewById(R.id.txt_bt_availability);
        m_txt_bt_permission = findViewById(R.id.txt_bt_permission);
        m_txt_bt_activation = findViewById(R.id.txt_bt_activation);

        Handler handler = new Handler();
        handler.postDelayed(new Runnable() {
            @Override
            public void run() {
                m_bt_controller.syncStats();
                doUpdateUI();
                handler.postDelayed(this, 1000);
            }
        }, 500);
    }

    private void doUpdateUI() {
        m_bt_controller.syncStats();
        switch (m_bt_controller.getAvailabilityStatus()) {
            case NOT_SUPPORTED:
                m_txt_bt_availability.setText("Bluetooth unavailable");
                break;
            case SUPPORTED:
                m_txt_bt_availability.setText("OK");
                break;
            default:
                m_txt_bt_availability.setText("Unknown status");
                break;
        }

        switch (m_bt_controller.getPermissionStatus()) {
            case NOT_READY:
                m_txt_bt_permission.setText("NOT ready");
                break;
            case ALL_GRANTED:
                m_txt_bt_permission.setText("OK");
                break;
            default:
                m_txt_bt_permission.setText("Unknown status");
                break;
        }

        switch (m_bt_controller.getActivationStatus()) {
            case DISABLED:
                m_txt_bt_activation.setText("Bluetooth: Off");
                break;
            case ENABLED:
                m_txt_bt_activation.setText("Bluetooth: On");
                break;
            default:
                m_txt_bt_activation.setText("Unknown status");
                break;
        }
    }
}