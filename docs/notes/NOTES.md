# 专注神器 持久化笔记

## 参考实现

- 2026-09-30 轮（状态盘点，刷新 STATE.md）：无需调研：该轮为纯状态盘点任务，不产生任何新代码。

- 2026-09-30 轮（测试真实性核验）调研 headless 跑 PyQt6 测试的成熟做法：

- napari 官方测试指南：无显示器跑 Qt 测试首选 `QT_QPA_PLATFORM=offscreen`（也给出 `xvfb-run` 作为 Linux/WSL 备选）。
  来源: https://github.com/napari/docs/blob/main/docs/developers/contributing/testing.md
  文件路径:行号 → docs/developers/contributing/testing.md:240-244（`QT_QPA_PLATFORM=offscreen pytest napari`）、:253-257（xvfb-run 方案）。原始核实: https://raw.githubusercontent.com/napari/docs/main/docs/developers/contributing/testing.md
- PyInstaller 社区讨论：提出用 monkeypatch 设置 `QT_QPA_PLATFORM=offscreen` 的 fixture，让 Qt 离屏渲染从而避免测试弹窗、可在 CI 跑。
  来源: https://github.com/pyinstaller/pyinstaller/issues/5120
  文件路径:行号 → issue #5120 正文 body:2（"Qt can be told to render offscreen"）、body:6-7（`def Qt_render_offscreen(monkeypatch): monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")`）。
- pytest-qt（Qt 测试事实标准插件）：QApplication 必须以 session 级 fixture 全局唯一创建，因为进程内销毁/重建 QApplication 不安全。
  来源: https://github.com/pytest-dev/pytest-qt
  文件路径:行号 → src/pytestqt/plugin.py:66-67（`@pytest.fixture(scope="session")` / `def qapp(qapp_args, qapp_cls, pytestconfig)`）；注释说明 "It is not possible to override this per unit test since a QApplication..." 位于同文件 qapp_cls fixture 段（约 :75）。原始核实: https://raw.githubusercontent.com/pytest-dev/pytest-qt/master/src/pytestqt/plugin.py

结构选择：沿用本仓库既有模式——tests/*.py 顶部 `os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")`（与 napari/PyInstaller 建议一致），并继续用 stdlib `unittest.TestCase` + `python -m unittest discover` 作为零额外依赖的跑法（pyproject 已配 pytest testpaths，两条路都通）；不引入 pytest-qt，因现有测试已自建单例 QApplication，符合 plugin.py:66 的 session 级唯一原则。

### 本仓库测试真实性核验（2026-09-30）

结论：测试是真实存在的，非空壳。`tests/` 下 10 个文件、80 个用例，均为带实质断言的 unittest 用例（覆盖 schedule_manager 规则判定、process_matching 进程匹配、icon_catalog、daily_targets 持久化、UI 可靠性等核心逻辑），无需补测试框架。

真实输出（Windows, .venv, PyQt6 6.11.1 为本轮新装入 .venv）：

```
$ QT_QPA_PLATFORM=offscreen .venv/Scripts/python.exe -m unittest discover -s tests
................................................................................
----------------------------------------------------------------------
Ran 80 tests in 5.027s

OK

$ QT_QPA_PLATFORM=offscreen .venv/Scripts/python.exe -m pytest -q
80 passed in 5.24s
```

