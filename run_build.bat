@echo off
setlocal

:: Set up environment
set JAVA_HOME=E:\jdk\jdk-17.0.13+11
set PATH=%JAVA_HOME%\bin;E:\flutter\bin;%PATH%
set JAVA_TOOL_OPTIONS=-Dhttps.protocols=TLSv1.2

echo ========================================
echo Building Focus Capsule Flutter APK
echo ========================================

:: Step 1: Copy project to English path (avoids symlink issue with Chinese chars)
set SRC_DIR="E:\专注神器\focus_capsule_flutter"
set DST_DIR="E:\focus_app"

if not exist "%DST_DIR%" (
    echo [1/5] Copying project to %DST_DIR% ...
    xcopy /E /I /Y /Q %SRC_DIR% %DST_DIR%
    if errorlevel 1 (
        echo ERROR: Copy failed!
        pause
        exit /b 1
    )
    echo OK: Project copied
) else (
    echo SKIP: %DST_DIR% already exists
)

cd /d %DST_DIR%

:: Step 2: Enable Developer Mode for symlinks
echo [2/5] Enabling Developer Mode...
reg add HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock /v AllowDevelopmentWithoutDevLicense /t REG_DWORD /d 1 /f >nul 2>&1
echo OK: Dev mode set

:: Step 3: Get dependencies
echo [3/5] Resolving dependencies...
call flutter pub get
if errorlevel 1 (
    echo ERROR: pub get failed
    pause
    exit /b 1
)
echo OK: Dependencies resolved

:: Step 4: Clean build
echo [4/5] Cleaning previous build...
call flutter clean
echo OK: Clean done

:: Step 5: Build APK
echo [5/5] Building APK (this may take several minutes)...
call flutter build apk --release
if errorlevel 1 (
    echo ERROR: Build failed!
    echo Check the log above for details.
    pause
    exit /b 1
)

echo.
echo ========================================
echo BUILD SUCCESSFUL!
echo ========================================
echo.
echo APK location:
dir /b %DST_DIR%\build\app\outputs\apk\release\*.apk 2>nul
if errorlevel 1 (
    dir /b %DST_DIR%\android\app\build\outputs\apk\release\*.apk 2>nul
)
echo.
echo Done! Press any key to close...
pause >nul
