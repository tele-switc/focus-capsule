#!/usr/bin/env bash
# Build script for Android Toga implementation of Focus Capsule.
# This script assumes macOS or Linux host with Briefcase installed.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANDROID_DIR="${SCRIPT_DIR}/focus_capsule_android"

if [[ ! -d "${ANDROID_DIR}" ]]; then
  echo "Focus Capsule Android source not found: ${ANDROID_DIR}" >&2
  exit 1
fi

# Install Toga build tools if not present
if ! command -v briefcase &> /dev/null; then
  echo "Installing BeeWare tools..."
  python -m pip install --user --upgrade pip
  python -m pip install --user briefcase
  export PATH="${HOME}/.local/bin:${PATH}"
fi

# Generate native icons for Android (not needed on Android, but Toga uses it)
if [[ -f "${SCRIPT_DIR}/packaging/generate_icons.py" ]]; then
  echo "Generating native icons..."
  python "${SCRIPT_DIR}/packaging/generate_icons.py" --platform macos
fi

# Create and build the Toga app

# Copy core modules that Toga can reference
# The goal is to keep pure logic (models, controller, services) accessible
# by the Toga app without HTML/Qt dependencies

cd "${ANDROID_DIR}"

echo "Creating Toga app distribution..."
briefcase create \
  --template=toga \
  --platform=android \
  --force \
  ${ANDROID_DIR}

if [[ $? -ne 0 ]]; then
  echo "Failed to create Toga app distribution." >&2
  exit 1
fi

echo "Building Android APK..."
briefcase build-android

if [[ $? -ne 0 ]]; then
  echo "Failed to build Android APK." >&2
  exit 1
fi

echo "Android APK built successfully."
echo "Find the APK in: ${ANDROID_DIR}/dist/android.apk"
