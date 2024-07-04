/*
 * Copyright 2024 The ChromiumOS Authors
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

package com.example.testbluetootharcappfortast.ui;

import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import androidx.activity.result.ActivityResult;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import androidx.fragment.app.Fragment;
import com.example.testbluetootharcappfortast.BluetoothController;
import com.example.testbluetootharcappfortast.R;

public class Home extends Fragment {
    private TextView m_txt_bt_availability, m_txt_bt_permission, m_txt_bt_activation;
    private TextView m_txt_bt_permission_op_stat, m_txt_bt_activation_op_stat;
    private BluetoothController m_bt_controller;
    private final String OPERATING = "Operating";

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        View root = inflater.inflate(R.layout.fragment_home, container, false);
        AppCompatActivity activity = (AppCompatActivity)getActivity();
        if (activity == null) {
            return root;
        }

        m_bt_controller = new BluetoothController(activity);
        ActivityResultLauncher<Intent> enableBtLauncher = registerForActivityResult(
                new ActivityResultContracts.StartActivityForResult(), result -> {
                    String resultString = ActivityResult.resultCodeToString(result.getResultCode());
                    if (m_txt_bt_permission_op_stat.getText() == OPERATING) {
                        m_txt_bt_permission_op_stat.setText(resultString);
                    }
                    if (m_txt_bt_activation_op_stat.getText() == OPERATING) {
                        m_txt_bt_activation_op_stat.setText(resultString);
                    }
                }
        );

        root.findViewById(R.id.btn_request_bt).setOnClickListener(v -> {
            m_txt_bt_permission_op_stat.setText(OPERATING);
            try {
                m_bt_controller.requestPermissions(activity);
            } catch (Exception e) {
                m_txt_bt_permission_op_stat.setText(e.getMessage());
            }
        });

        root.findViewById(R.id.btn_turn_on_bt).setOnClickListener(v -> {
            m_txt_bt_activation_op_stat.setText(OPERATING);
            try {
                m_bt_controller.bluetoothControl(enableBtLauncher, true);
            } catch (Exception e) {
                m_txt_bt_activation_op_stat.setText(e.getMessage());
            }
        });

        root.findViewById(R.id.btn_turn_off_bt).setOnClickListener(v -> {
                m_txt_bt_activation_op_stat.setText(OPERATING);
            try {
                m_bt_controller.bluetoothControl(enableBtLauncher, false);
            } catch (Exception e) {
                m_txt_bt_activation_op_stat.setText(e.getMessage());
            }
        });

        m_txt_bt_availability = root.findViewById(R.id.txt_bt_availability);
        m_txt_bt_permission = root.findViewById(R.id.txt_bt_permission);
        m_txt_bt_activation = root.findViewById(R.id.txt_bt_activation);
        m_txt_bt_permission_op_stat = root.findViewById(R.id.txt_bt_permission_op_stat);
        m_txt_bt_activation_op_stat = root.findViewById(R.id.txt_bt_activation_op_stat);

        Handler handler = new Handler();
        handler.postDelayed(new Runnable() {
            @Override
            public void run() {
                m_bt_controller.syncStats();
                doUpdateUI();
                handler.postDelayed(this, 1500);
            }
        }, 1000);

        return root;
    }

    private void doUpdateUI() {
        m_bt_controller.syncStats();
        switch (m_bt_controller.getAvailabilityStatus()) {
            case NOT_SUPPORTED:
                m_txt_bt_availability.setText("Unavailable");
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
