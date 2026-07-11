from __future__ import annotations

import argparse
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QBuffer, QIODevice, QRectF, Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtSvg import QSvgRenderer


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SVG_PATH = ASSETS / "focus-capsule.svg"
ICO_PATH = ASSETS / "focus-capsule.ico"
ICONSET_PATH = ASSETS / "FocusCapsule.iconset"
ICNS_PATH = ASSETS / "FocusCapsule.icns"


def render_png(renderer: QSvgRenderer, size: int) -> bytes:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()

    buffer = QBuffer()
    if not buffer.open(QIODevice.OpenModeFlag.WriteOnly):
        raise RuntimeError("Unable to allocate an in-memory PNG buffer")
    if not image.save(buffer, "PNG"):
        raise RuntimeError(f"Unable to encode the {size} px icon as PNG")
    return bytes(buffer.data())


def write_windows_icon(renderer: QSvgRenderer) -> None:
    sizes = (16, 24, 32, 48, 64, 128, 256)
    images = [(size, render_png(renderer, size)) for size in sizes]
    offset = 6 + (16 * len(images))

    entries: list[bytes] = []
    payloads: list[bytes] = []
    for size, payload in images:
        encoded_size = 0 if size == 256 else size
        entries.append(
            struct.pack(
                "<BBBBHHII",
                encoded_size,
                encoded_size,
                0,
                0,
                1,
                32,
                len(payload),
                offset,
            )
        )
        payloads.append(payload)
        offset += len(payload)

    ICO_PATH.write_bytes(
        struct.pack("<HHH", 0, 1, len(images)) + b"".join(entries) + b"".join(payloads)
    )
    print("Wrote assets/focus-capsule.ico")


def write_macos_icon(renderer: QSvgRenderer) -> None:
    if sys.platform != "darwin":
        raise SystemExit("macOS icons must be generated on macOS because iconutil is required")

    if ICONSET_PATH.exists():
        shutil.rmtree(ICONSET_PATH)
    ICONSET_PATH.mkdir(parents=True)

    files = {
        "icon_16x16.png": 16,
        "icon_16x16@2x.png": 32,
        "icon_32x32.png": 32,
        "icon_32x32@2x.png": 64,
        "icon_128x128.png": 128,
        "icon_128x128@2x.png": 256,
        "icon_256x256.png": 256,
        "icon_256x256@2x.png": 512,
        "icon_512x512.png": 512,
        "icon_512x512@2x.png": 1024,
    }
    for filename, size in files.items():
        (ICONSET_PATH / filename).write_bytes(render_png(renderer, size))

    iconutil = shutil.which("iconutil")
    if not iconutil:
        raise SystemExit("iconutil is required to create the macOS .icns file")
    subprocess.run(
        [iconutil, "-c", "icns", "-o", str(ICNS_PATH), str(ICONSET_PATH)],
        check=True,
    )
    print("Wrote assets/FocusCapsule.icns")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render native desktop icons from assets/focus-capsule.svg."
    )
    parser.add_argument(
        "--platform",
        choices=("windows", "macos", "all"),
        default="all",
        help="Select which native icon format to generate.",
    )
    args = parser.parse_args()

    renderer = QSvgRenderer(str(SVG_PATH))
    if not renderer.isValid():
        raise SystemExit(f"Invalid SVG source: {SVG_PATH}")

    if args.platform in {"windows", "all"}:
        write_windows_icon(renderer)
    if args.platform in {"macos", "all"}:
        write_macos_icon(renderer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
