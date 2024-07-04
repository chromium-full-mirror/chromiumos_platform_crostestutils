/*
 * Copyright 2024 The ChromiumOS Authors
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

package com.example.testbluetootharcappfortast;

import android.os.Bundle;

import androidx.appcompat.app.ActionBarDrawerToggle;
import androidx.appcompat.app.AppCompatActivity;
import androidx.appcompat.widget.Toolbar;
import androidx.core.view.GravityCompat;
import androidx.drawerlayout.widget.DrawerLayout;
import androidx.fragment.app.FragmentTransaction;

import com.example.testbluetootharcappfortast.ui.About;
import com.example.testbluetootharcappfortast.ui.Home;
import com.google.android.material.navigation.NavigationView;


public class MainActivity extends AppCompatActivity {
    private int m_sub_content_id = -1;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        reLoadSubContent(R.id.nav_item_home);

        // Initiate the side menu.
        Toolbar m_toolbar = findViewById(R.id.toolbar);
        setSupportActionBar(m_toolbar);
        DrawerLayout drawerLayout = findViewById(R.id.main);
        ActionBarDrawerToggle actionBarDrawerToggle = new ActionBarDrawerToggle(this, drawerLayout, m_toolbar, 0,0);
        drawerLayout.addDrawerListener(actionBarDrawerToggle);
        actionBarDrawerToggle.syncState();

        NavigationView navi_view = findViewById(R.id.nav_view);
        navi_view.setNavigationItemSelectedListener(item -> {
            // Dismiss the side menu.
            drawerLayout.closeDrawer(GravityCompat.START);

            reLoadSubContent(item.getItemId());
            return true;
        });
    }

    private void reLoadSubContent(int id) {
        FragmentTransaction transaction = getSupportFragmentManager().beginTransaction();
        if (id == m_sub_content_id) {
            // Avoid redundant transaction.
            return;
        } else if (id == R.id.nav_item_home) {
            transaction.replace(R.id.sub_content_view, Home.class, null);
        } else if (id == R.id.nav_item_about) {
            transaction.replace(R.id.sub_content_view, About.class, null);
        } else {
            return;
        }
        m_sub_content_id = id;
        transaction.commit();
    }
}




