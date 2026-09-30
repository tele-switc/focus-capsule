# 专注神器 持久化笔记

## 参考实现

- 2026-09-30 轮（补最小端到端自检 `tests/e2e_session_flow.py`）调研「跑完整流程→断言最终落盘结果→输出可机检 PASS/FAIL」的成熟做法：

- yt-dlp 下载端到端测试：下载完成后一律回到磁盘取证——先 `os.path.exists(tc_filename)`、再校验体积下界、再比对 `_file_md5` 摘要，最后连旁车 `*.info.json` 也要单独断言存在，绝不拿内存里的回调结果代替文件实况。
  来源: https://github.com/yt-dlp/yt-dlp/blob/master/test/test_download.py#L233-L254
  文件路径:行号 → test/test_download.py:235（`self.assertTrue(os.path.exists(tc_filename), ...)`）、:241-246（体积下界）、:247-248（`md5_for_file` 严格相等）、:251-253（info.json 存在性）。原始核实: https://raw.githubusercontent.com/yt-dlp/yt-dlp/master/test/test_download.py
- sqlite-utils 持久化测试：所有写盘用例都把 store 指到 `tmpdir` 下的显式路径（`Database(path)`），写完立即从该路径重新读取计数断言，使每个用例互不污染、也不依赖用户真实数据目录。
  来源: https://github.com/simonw/sqlite-utils/blob/main/tests/test_create.py#L1177-L1182
  文件路径:行号 → tests/test_create.py:1177-1182（`def test_works_with_pathlib_path(tmpdir)` → `path = pathlib.Path(tmpdir / "test.db")` → `db = Database(path)` → `assert db.table("demo").count == 1`）。原始核实: https://raw.githubusercontent.com/simonw/sqlite-utils/main/tests/test_create.py
- CPython 官方回归跑测器：整场测试只维护一个 `exitcode`，末尾 `sys.exit(exitcode)`，把「是否通过」压成进程退出码供 CI/脚本机检，人类可读摘要与机检信号分离。
  来源: https://github.com/python/cpython/blob/main/Lib/test/libregrtest/main.py#L786-L815
  文件路径:行号 → Lib/test/libregrtest/main.py:786（`def main(self, tests: TestList | None = None) -> NoReturn`）、:805（`exitcode = 0`）、:813（`exitcode = self.run_tests(selected, tests)`）、:815（`sys.exit(exitcode)`）。原始核实: https://raw.githubusercontent.com/python/cpython/main/Lib/test/libregrtest/main.py
- pytest-qt（Qt 测试事实标准插件）`waitUntil`：驱动 Qt 事件循环直到条件成立、带总超时上限，而不是写死 `sleep` 秒数；超时即失败。
  来源: https://github.com/pytest-dev/pytest-qt/blob/master/src/pytestqt/qtbot.py#L530-L560
  文件路径:行号 → src/pytestqt/qtbot.py:530-532（`def waitUntil(self, callback, *, timeout: int = 5000)`）、:536-540（"Wait in a busy loop, calling the given callback periodically until timeout is reached"）。原始核实: https://raw.githubusercontent.com/pytest-dev/pytest-qt/master/src/pytestqt/qtbot.py

结构选择：e2e 沿用「真实服务 + 临时目录 + 磁盘取证 + 退出码」四条——① `HistoryService(history_path=...)` / `DataStore(data_path=...)` 本就支持注入路径，照 sqlite-utils 那样把全部写盘引到 `TemporaryDirectory`，绝不碰真实 AppData/QSettings；② 断言阶段新开一个 `HistoryService`/`DataStore` 实例并重读原始 JSON（等价于进程重启），学 yt-dlp 只信磁盘实况；③ 事件等待用自写的 `_wait_until` 轮询 `QApplication.processEvents()`（同 qtbot.waitUntil 语义，零新依赖，与 NOTES 上一轮「不引入 pytest-qt」的结论一致）；④ 输出 `PASS`/`FAIL: <原因>` 单行 + `sys.exit(0/1)`，学 CPython regrtest 把结论压进退出码。会话计时按「显式驱动 QTimer 的同一个 tick 槽」来取得确定性秒数，不放宽任何相等断言。

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

