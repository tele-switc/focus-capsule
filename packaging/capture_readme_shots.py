"""生成 README 用的截图：主界面三页 + 接管弹层 + 严格模式解锁框。

用法（在仓库根目录）：
    QT_QPA_PLATFORM=offscreen python packaging/capture_readme_shots.py

依赖 visual_test 的演示数据注入，因此截图里是示例数据而不是你的真实记录。
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("FOCUS_CAPSULE_VISUAL_TEST", "1")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

OUT = ROOT / "docs" / "screenshots"
TMP = Path(os.environ.get("TEMP", "/tmp")) / "focus_capsule_readme_shots"
PAGES = {
    "today": "pa_today_1440x900.png",
    "timeline": "pa_trend_1440x900.png",
    "calendar": "pa_calendar_1440x900.png",
    "plan": "pa_shell_1440x900.png",
}


def capture_pages() -> None:
    import subprocess

    env = dict(os.environ)
    env["FOCUS_CAPSULE_SCREENSHOT"] = "1"
    env["FOCUS_CAPSULE_SCREENSHOT_DIR"] = str(TMP)
    result = subprocess.run(
        [sys.executable, "-m", "focus_capsule.visual_test"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout[-2000:])
        print(result.stderr[-2000:])
        raise SystemExit("visual_test 截图失败")


def capture_dialogs() -> list[tuple[str, object]]:
    """离屏渲染接管弹层与严格模式解锁框。"""

    from PyQt6.QtWidgets import QApplication

    from focus_capsule.exit_gate_dialog import ExitGateDialog
    from focus_capsule.overlay import OverlayWindow
    from focus_capsule.strict_lock import ExitGate, StrictPolicy

    app = QApplication.instance() or QApplication([])
    shots: list[tuple[str, object]] = []

    overlay = OverlayWindow(
        return_seconds=5,
        lock_until_switch=True,
        allowed_apps=["Code.exe"],
        strict=False,
        snooze_used=0,
        snooze_quota=2,
    )
    overlay.subtitle_for_capture("请切回 VS Code，继续刚才的目标")
    overlay.resize(1180, 760)
    overlay.show()
    app.processEvents()
    shots.append(("overlay", overlay.grab()))

    gate = ExitGate(StrictPolicy(level="phrase", phrase_length=6))
    gate.begin()
    gate.arm_phrase()
    dialog = ExitGateDialog(gate)
    dialog.show()
    app.processEvents()
    shots.append(("strict_exit", dialog.grab()))
    return shots


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    capture_pages()
    for name, source in PAGES.items():
        src = TMP / source
        if src.exists():
            shutil.copyfile(src, OUT / f"{name}.png")
            print(f"OK  {name}.png  <- {source}")
        else:
            print(f"MISS {source}")
    for name, pixmap in capture_dialogs():
        target = OUT / f"{name}.png"
        pixmap.save(str(target), "PNG")
        print(f"OK  {name}.png  ({target.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
