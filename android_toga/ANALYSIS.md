# -*- mode: python ; coding: utf-8 -*-
"""BeeWare/Toga analysis for Focus Capsule Android port.

This document records the feasibility assessment and migration strategy
for building an Android APK of Focus Capsule using BeeWare Toga.

KEY FINDINGS
============

1. Android restrictions (cannot be worked around):
   - No arbitrary foreground app detection (privacy sandbox)
   - No fullscreen overlay on other apps (window management restriction)
   - No system tray (mobile UI paradigm)

2. Features that CAN carry over:
   - Focus timer (countdown + progress)
   - Break timer
   - Esc key / break allowance tracking
   - Schedule-based locking (within the app itself)
   - History recording and viewing
   - Whitelist management
   - Models, controller logic, DB persistence

3. Migration strategy:
   - Keep all existing PyQt code untouched
   - Create focus_capsule_android/ as a parallel Toga implementation
   - Reuse models.py, history_db.py, and pure-Python logic directly
   - Adapt controller.py to use asyncio instead of QTimer/pyqtSignal

4. Core UX changes for Android:
   - Foreground detection → manual "current app" selector + optional
     UsageStats API permission request (opt-in, graceful degradation)
   - Overlay → in-app modal dialog that blocks navigation away from
     the focus session (Android Activity can stay on top)
   - Tray → Android Notification with ongoing "focus session active"
     status bar notification

FILES TO CREATE
===============
- android_toga/beanpod.toml         (BeeWare project config)
- android_toga/requirements-toga.txt (Toga + Android build deps)
- android_toga/focus_capsule_android/__init__.py
- android_toga/focus_capsule_android/app.py       (Toga app entry point)
- android_toga/focus_capsule_android/screens/     (Toga screen implementations)
- android_toga/focus_capsule_android/widgets/     (custom Toga widgets)
- android_toga/build_android.sh                   (local build script)
- android_toga/.github/workflows/build-android.yml (CI for APK)

BUILD REQUIREMENTS
==================
- macOS or Linux for Android builds (beeware-tools + briefcase)
- Android SDK/NDK installed
- Java JDK 17+

SEE ALSO:
- https://docs.beeware.org/en/latest/
- https://docs.beeware.org/en/latest/deploying/android.html
"""
