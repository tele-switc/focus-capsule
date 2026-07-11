"""双击启动 Focus Capsule（无控制台窗口）。

此文件扩展名为 .pyw，由 pythonw.exe 执行，不会弹出黑色控制台窗口。
等价于命令行运行 `python -m focus_capsule`。
"""
import subprocess
import sys


def main() -> int:
    return subprocess.call([sys.executable, "-m", "focus_capsule"])


if __name__ == "__main__":
    raise SystemExit(main())
