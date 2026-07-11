#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "The macOS package must be built on macOS." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VERSION="$(tr -d '[:space:]' < "${SCRIPT_DIR}/version.txt")"
DIST_DIR="${ROOT}/dist"
BUILD_DIR="${ROOT}/build"
ARCH="${PYINSTALLER_ARCH:-$(uname -m)}"

if [[ -n "${BUILD_PYTHON:-}" ]]; then
  PYTHON="${BUILD_PYTHON}"
else
  VENV="${ROOT}/.venv-build"
  PYTHON="${VENV}/bin/python"
  if [[ ! -x "${PYTHON}" ]]; then
    "${PYTHON_BIN:-python3}" -m venv "${VENV}"
  fi
fi

if [[ "${SKIP_DEPENDENCY_INSTALL:-0}" != "1" ]]; then
  "${PYTHON}" -m pip install --upgrade pip
  "${PYTHON}" -m pip install -r "${ROOT}/requirements-build.txt"
fi

"${PYTHON}" "${SCRIPT_DIR}/generate_icons.py" --platform macos

export PYTHONHASHSEED=0
"${PYTHON}" -m PyInstaller \
  --clean \
  --noconfirm \
  --distpath "${DIST_DIR}" \
  --workpath "${BUILD_DIR}" \
  "${SCRIPT_DIR}/Focus Capsule.macos.spec"

APP="${DIST_DIR}/Focus Capsule.app"
if [[ ! -d "${APP}" ]]; then
  echo "Expected application was not produced: ${APP}" >&2
  exit 1
fi

if [[ -n "${MACOS_CODESIGN_IDENTITY:-}" ]]; then
  codesign --verify --deep --strict --verbose=2 "${APP}"
else
  echo "Warning: MACOS_CODESIGN_IDENTITY is not set; producing an unsigned development DMG." >&2
fi

DMG_DIR="${DIST_DIR}/dmg"
DMG="${DMG_DIR}/Focus-Capsule-${VERSION}-macOS-${ARCH}.dmg"
STAGING="$(mktemp -d "${TMPDIR:-/tmp}/focus-capsule-dmg.XXXXXX")"
trap 'rm -rf "${STAGING}"' EXIT

mkdir -p "${DMG_DIR}"
rm -f "${DMG}" "${DMG}.sha256"
ditto "${APP}" "${STAGING}/Focus Capsule.app"
ln -s /Applications "${STAGING}/Applications"

hdiutil create \
  -volname "Focus Capsule" \
  -srcfolder "${STAGING}" \
  -format UDZO \
  -ov \
  "${DMG}"

if [[ -n "${MACOS_CODESIGN_IDENTITY:-}" ]]; then
  codesign --force --timestamp --sign "${MACOS_CODESIGN_IDENTITY}" "${DMG}"
  codesign --verify --verbose=2 "${DMG}"
fi

if [[ -n "${APPLE_NOTARY_KEYCHAIN_PROFILE:-}" ]]; then
  xcrun notarytool submit "${DMG}" \
    --keychain-profile "${APPLE_NOTARY_KEYCHAIN_PROFILE}" \
    --wait
  xcrun stapler staple "${DMG}"
  xcrun stapler validate "${DMG}"
elif [[ -n "${APPLE_ID:-}" || -n "${APPLE_TEAM_ID:-}" || -n "${APPLE_APP_PASSWORD:-}" ]]; then
  if [[ -z "${APPLE_ID:-}" || -z "${APPLE_TEAM_ID:-}" || -z "${APPLE_APP_PASSWORD:-}" ]]; then
    echo "APPLE_ID, APPLE_TEAM_ID, and APPLE_APP_PASSWORD must all be set for notarization." >&2
    exit 1
  fi
  xcrun notarytool submit "${DMG}" \
    --apple-id "${APPLE_ID}" \
    --team-id "${APPLE_TEAM_ID}" \
    --password "${APPLE_APP_PASSWORD}" \
    --wait
  xcrun stapler staple "${DMG}"
  xcrun stapler validate "${DMG}"
else
  echo "Warning: notarization credentials are not set; notarization was skipped." >&2
fi

(
  cd "${DMG_DIR}"
  shasum -a 256 "$(basename "${DMG}")" > "$(basename "${DMG}").sha256"
)

echo "DMG: ${DMG}"
