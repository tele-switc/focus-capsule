# 专注神器 · 状态日志

## 2026-09-30 状态

### 当前阶段
v3.2.1 已发布（Windows/macOS/Android 安装包均已挂到 Release）。当前处于**大规模未提交改动期**：工作区有大量修改与新增文件，且旧 `android_toga/`（Toga/BeeWare 方案）已被整目录删除，技术栈收敛到 PySide6（`focus_capsule/`）+ Flutter（`focus_capsule_flutter/`）。

### 本地与远端差异（tele-switc/focus-capsule）
- 分支 `main` 领先 `origin/main` **1 个提交**（`8499ed1 docs: state 2026-09-29`，未推送）。
- 本次盘点时 `git fetch` 因网络中断失败（schannel: server closed abruptly），远端实际状态未能核对；以上为本地缓存的跟踪信息。
- 工作区脏文件概况：
  - 修改（M）：`focus_capsule/` 全部核心模块（app/controller/models/monitor/overlay/theme/styles/各页面等约 30 个文件）、`focus_capsule_flutter/`（main.dart、session_controller、timer/history 屏、Android 清单与 gradle 配置、pubspec）、`packaging/`（spec/iss/version）、`pyproject.toml`、4 个既有测试文件、`.gitignore`。
  - 删除（D）：整个 `android_toga/` 目录（Toga 实现废弃）。
  - 新增（??）：`focus_app/`、`packages/`、`focus_capsule/ui/` 包、`focus_capsule/activity_tracker.py`、`app_categories.py`、`category_dialog.py`、`daily_progress.py`、`daily_targets_dialog.py`、`process_matching.py`、`visual_test.py`、Flutter 端 `OverlayWindow.kt`、`foreground_monitor.dart`、Android layout 资源、`run_build.bat`、4 个新测试文件、`code_review_report.md`。

### 最近变更（git log -10）
- 8499ed1 docs: state 2026-09-29
- e828667 feat: add local LifeOS intervention bridge (opt-in file protocol)
- 6b41bc4 docs: rewrite README with download links for v3.2.1
- 1d503b1 bump flutter version to 3.2.1+1
- 990d2cd build: bump version to 3.0.0 for v3.0 UI release
- faa2368 feat: v3.0 polish — calendar light heatmap, dark focus mode QSS switching
- e6bac50 feat: v3.0 UI — warm light theme, nav rail, top bar, open canvas
- ef8f8e6 build: add urllib/http hiddenimports for v2.1 AI report, gitignore scratch dirs
- 4b62127 feat: v2.1 全新 UI 重构 + 3 bug 修复 + 动态背景 + 趋势/日历/AI日报
- 7527ebc fix: schedule panel intensity and escape settings now work per-rule
