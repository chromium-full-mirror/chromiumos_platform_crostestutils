/*
 * Copyright 2024 The ChromiumOS Authors
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

package com.example.testbluetootharcappfortast;

public final class Constant {
    public enum AVAILABILITY {
        NOT_SUPPORTED,
        SUPPORTED,
    }

    public enum PERMISSION {
        NOT_READY,
        ALL_GRANTED,
    }

    public enum ACTIVATION {
        DISABLED,
        ENABLED,
    }

    public static final int REQUEST_CODE_PERMISSION = 1000;
}
