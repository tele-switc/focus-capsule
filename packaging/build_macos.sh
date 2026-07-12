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

(
  cd "${DMG_DIR}"
  shasum -a 256 "$(basename "${DMG}")" > "$(basename "${DMG}").sha256"
)

echo "DMG: ${DMG}"
