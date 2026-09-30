# 专注神器 — 状态日志

## 2026-09-29 状态

### 已完成
- feat: add local LifeOS intervention bridge (opt-in file protocol) — e828667
- docs: rewrite README with download links for v3.2.1 — 6b41bc4
- bump flutter version to 3.2.1+1 — 1d503b1
- build: bump version to 3.0.0 for v3.0 UI release — 990d2cd
- feat: v3.0 polish — calendar light heatmap, dark focus mode QSS switching — faa2368
  - calendar_page.py cell colors dark greens → light teal/success palette
  - main_window.py _refresh_global_style() rebuilds QSS on theme toggle
  - overlay.py mask background → #0D0E11
  - all 26 .py files compile & launch verified (6 screenshots)
- feat: v3.0 UI — warm light theme, nav rail, top bar, open canvas — e6bac50
  - theme.py LIGHT/DARK dict + ThemeManager + __getattr__ compat
  - styles.py dynamic QSS from T.current()
  - main_window.py 76px nav rail + 44px top bar + QStackedWidget canvas
  - brand color #5B6FE8 replacing old #67cfbb/#4A6FA5
  - all 26 .py files compile, app launches at 1440x900
- build: add urllib/http hiddenimports for v2.1 AI report, gitignore scratch dirs — ef8f8e6
- feat: v2.1 全新 UI 重构 + 3 bug 修复 + 动态背景 + 趋势/日历/AI日报 — 4b62127
- fix: schedule panel intensity and escape settings now work per-rule — 7527ebc
- fix: use CardThemeData instead of CardTheme for Flutter compatibility — 81f73af
- fix: upgrade Android Gradle Plugin to 8.6.0 and Kotlin to 1.9.24 — 70b2f28
- ci: add Flutter APK build workflow and Flutter project files — 01f6d84

### 待拍板
- （无）