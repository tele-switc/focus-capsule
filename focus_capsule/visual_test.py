"""Visual-test entry point for Focus Capsule.

Launches a stripped-down MainWindow with no background services,
injects deterministic demo data, and captures screenshots.

Usage:
    # Interactive preview:
    FOCUS_CAPSULE_VISUAL_TEST=1 python -m focus_capsule.visual_test

    # Screenshot all pages at all resolutions:
    FOCUS_CAPSULE_VISUAL_TEST=1 SCREENSHOT=1 python -m focus_capsule.visual_test

    # Show a specific page:
    FOCUS_CAPSULE_VISUAL_TEST=1 PAGE=trend python -m focus_capsule.visual_test
"""

from __future__ import annotations

import os
import random
import sys
import time
from datetime import date, datetime, timedelta

# Must be set before importing focus_capsule modules
os.environ["FOCUS_CAPSULE_VISUAL_TEST"] = "1"

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

# Allow importlib-loaded modules to be found by sub-imports
# When loaded via _load_module() in capture.py, modules are registered in sys.modules
if "focus_capsule.styles" not in sys.modules:
    from focus_capsule.styles import _build_stylesheet
else:
    _build_stylesheet = sys.modules["focus_capsule.styles"]._build_stylesheet

if "focus_capsule.data_models" not in sys.modules:
    from focus_capsule.data_models import china_today
else:
    china_today = sys.modules["focus_capsule.data_models"].china_today

if "focus_capsule.data_store" not in sys.modules:
    from focus_capsule.data_store import DataStore
else:
    DataStore = sys.modules["focus_capsule.data_store"].DataStore

if "focus_capsule.history_db" not in sys.modules:
    from focus_capsule.history_db import HistoryService
else:
    HistoryService = sys.modules["focus_capsule.history_db"].HistoryService

if "focus_capsule.models" not in sys.modules:
    from focus_capsule.models import SessionRecord
else:
    SessionRecord = sys.modules["focus_capsule.models"].SessionRecord

if "focus_capsule.trend_service" not in sys.modules:
    from focus_capsule.trend_service import TrendService
else:
    TrendService = sys.modules["focus_capsule.trend_service"].TrendService

if "focus_capsule.theme" not in sys.modules:
    from focus_capsule import theme as T
else:
    T = sys.modules["focus_capsule.theme"]


# ------------------------------------------------------------------
# 应用级字体：与 app.py 保持一致，显式设置可用字体链，避免中文豆腐块
# ------------------------------------------------------------------

def _apply_app_font(app: QApplication) -> None:
    font = QFont()
    font.setFamilies([
        "Microsoft YaHei UI",
        "Segoe UI",
        "PingFang SC",
        "Noto Sans CJK SC",
    ])
    font.setPointSize(13 if sys.platform == "darwin" else (10 if sys.platform == "win32" else 11))
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)


# ------------------------------------------------------------------
# Deterministic demo data generator
# ------------------------------------------------------------------

def _create_demo_records():
    """Generate 30 days of realistic SessionRecord data.

    Pattern:
      days 0-9:   strong focus (80-150 min/day)
      days 10-18: decline (20-60 min/day)
      days 19-29: recovery (60-130 min/day) with 2 peak days
    """
    random.seed(42)
    today = date.today()
    records = []

    for i in range(30):
        d = today - timedelta(days=29 - i)
        if i < 10:
            focus_sec = random.randint(4800, 9000)  # 80-150 min
        elif i < 18:
            focus_sec = random.randint(1200, 3600)  # 20-60 min
        else:
            focus_sec = random.randint(3600, 7800)  # 60-130 min
            if i in (22, 27):
                focus_sec = random.randint(9600, 12600)  # 160-210 min

        # Create 2-6 sessions per day
        num_sessions = random.randint(2, 6)
        base_hour = random.randint(7, 9)
        base_min = random.randint(0, 30)

        remaining = focus_sec
        for s in range(num_sessions):
            if s == num_sessions - 1:
                dur = remaining
            else:
                dur = remaining // (num_sessions - s)
                remaining -= dur

            sec = min(dur, random.randint(600, 2400))
            actual = sec - random.randint(0, sec // 10)

            started = datetime.combine(d, datetime.min.time()) + timedelta(
                hours=base_hour, minutes=base_min
            )
            ended = started + timedelta(seconds=sec)

            base_min += random.randint(30, 90)
            if base_min >= 60:
                base_hour += base_min // 60
                base_min %= 60

            distractions = random.randint(0, 5) if i < 18 else random.randint(0, 2)

            records.append(SessionRecord(
                started_at=started.isoformat(),
                ended_at=ended.isoformat(),
                duration_minutes=sec // 60,
                actual_focus_seconds=max(0, actual),
                distraction_count=distractions,
                esc_used=random.randint(0, 2),
                mode=random.choice(["Standard", "Deep"]),
                whitelisted_apps=["chrome.exe", "code.exe", "wechat.exe"][:random.randint(1, 3)],
                distractions=[],
                outcome=random.choice(["completed", "completed", "completed", "terminated"]),
            ))

    return records


def _inject_demo_events():
    """写入今天的演示前台区间事件 + daily_activity 秒数，供时间线/占比/排行展示。"""
    from focus_capsule.activity_events import ActivityEventLog, AFK_PROCESS

    store = DataStore()
    log = ActivityEventLog(store.base_dir)
    today = date.today()
    base = datetime.combine(today, datetime.min.time()).astimezone()

    # (进程, 标题, 起始小时, 时长分钟)——含午休/晚间长空隙（AFK 底纹来源）
    segments = [
        ("chrome.exe", "Gmail - Inbox", 7.5, 35),
        ("code.exe", "trend_service.py — focus_capsule", 8.2, 95),
        ("wechat.exe", "微信", 9.8, 12),
        ("code.exe", "activity_tracker.py — focus_capsule", 10.0, 80),
        ("excel.exe", "季度报表.xlsx", 11.5, 55),
        ("chrome.exe", "MDN Web Docs", 13.6, 40),
        ("code.exe", "timeline_view.py — focus_capsule", 14.4, 110),
        ("obsidian.exe", "工作笔记", 17.2, 30),
        ("potplayer64.exe", "纪录片.mp4", 20.1, 65),
    ]
    totals: dict[str, int] = {}
    display: dict[str, str] = {}
    for process, title, hour, minutes in segments:
        start = base + timedelta(hours=hour)
        end = start + timedelta(minutes=minutes)
        log.append_event(process, title, start, end)
        totals[process] = totals.get(process, 0) + minutes * 60
        display[process] = title.split(" — ")[0] if " — " in title else process
    # 显式一段午休 AFK 事件（验证灰色底纹的两种来源）
    log.append_event(AFK_PROCESS, "离开", base + timedelta(hours=12.2),
                     base + timedelta(hours=13.3))

    for day_off in range(6):
        d = (today - timedelta(days=day_off)).isoformat()
        entry = store.get_activity(d)
        factor = 1.0 if day_off == 0 else random.Random(day_off).uniform(0.4, 1.2)
        for process, secs in totals.items():
            entry.app_usage_seconds[process] = int(secs * factor * 0.8)
            entry.app_display_names.setdefault(process, display[process])
        store.save_activity(entry)


def _inject_demo_data():
    """Insert demo records into the history DB."""
    history = HistoryService()
    records = _create_demo_records()
    for rec in records:
        history.save_record(rec)
    try:
        _inject_demo_events()
    except Exception as e:  # 演示数据失败不阻塞截图
        print(f"demo events skipped: {e}", flush=True)


# ------------------------------------------------------------------
# Visual-test MainWindow — no background services
# ------------------------------------------------------------------

class VisualTestMainWindow(QWidget):
    """Standalone visual-test window with no background services.

    Contains only the nav rail + top bar + content canvas.
    No WindowMonitorThread, no tray, no ambient animation, no schedule manager.
    """

    def __init__(self, page_idx: int = 0):
        print("VTM __init__ start", flush=True)
        super().__init__()
        print("VTM super done", flush=True)
        self.setWindowTitle("Focus Capsule [VISUAL TEST]")
        self.setObjectName("appWindow")
        self.resize(1440, 900)
        self.setMinimumSize(1024, 700)
        print("VTM resize done", flush=True)

        self._data_store = DataStore()
        print("VTM data_store done", flush=True)
        self._app_config = self._data_store.load_app_config()
        print("VTM app_config done", flush=True)
        self._history_service = HistoryService()
        print("VTM history done", flush=True)
        self._trend_service = TrendService(self._history_service, self._app_config)
        print("VTM trend done", flush=True)

        # Inject demo data
        _inject_demo_data()
        print("VTM demo data done", flush=True)

        print("VTM calling _setup_ui...", flush=True)
        self._setup_ui(page_idx)
        print("VTM _setup_ui done", flush=True)

    def _setup_ui(self, page_idx: int):
        # Central layout
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Nav rail
        nav_rail = self._build_nav_rail()
        root.addWidget(nav_rail, 0)

        # Right side
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)

        # Top bar
        top_bar = self._build_top_bar()
        right.addWidget(top_bar, 0)

        # Content stack
        self._content_stack = QStackedWidget()
        self._content_stack.setObjectName("canvas")

        if "focus_capsule.ai_report_service" not in sys.modules:
            from focus_capsule.ai_report_service import AIReportService
        else:
            AIReportService = sys.modules["focus_capsule.ai_report_service"].AIReportService

        if "focus_capsule.calendar_page" not in sys.modules:
            from focus_capsule.calendar_page import CalendarPage
        else:
            CalendarPage = sys.modules["focus_capsule.calendar_page"].CalendarPage

        if "focus_capsule.trend_page" not in sys.modules:
            from focus_capsule.trend_page import TrendPage
        else:
            TrendPage = sys.modules["focus_capsule.trend_page"].TrendPage

        self._ai_service = AIReportService(
            self._history_service, self._data_store, self._app_config
        )

        # Today page
        print("Creating DailyGoalWidget...", flush=True)
        try:
            self._daily_goal_widget = DailyGoalWidget_cls(
                self._data_store, self._trend_service, self._ai_service,
                self._app_config, self
            )
            print("DailyGoalWidget created OK", flush=True)
        except Exception as e:
            print(f"DailyGoalWidget creation FAILED: {e}", flush=True)
            import traceback
            traceback.print_exc()
            raise
        scroll1 = self._wrap_scroll(self._daily_goal_widget)
        self._content_stack.addWidget(scroll1)

        # Real focus-plan page (background monitoring is not started)
        from focus_capsule.settings_panel import SettingsPanel
        self._settings_panel = SettingsPanel()
        scroll_p1 = self._wrap_scroll(self._settings_panel)
        self._content_stack.addWidget(scroll_p1)

        # Real schedule page with an inert manager
        from focus_capsule.schedule_manager import ScheduleManager
        from focus_capsule.schedule_panel import SchedulePanel
        self._schedule_manager = ScheduleManager(self)
        self._schedule_panel = SchedulePanel(self._schedule_manager, self)
        self._schedule_panel.load_rules()
        scroll_p2 = self._wrap_scroll(self._schedule_panel)
        self._content_stack.addWidget(scroll_p2)

        # Calendar page
        self._calendar_page = CalendarPage(self._trend_service, self)
        self._calendar_page.refresh()  # picks up demo data from history DB
        self._content_stack.addWidget(self._calendar_page)

        # Trends page
        self._trend_page = TrendPage(self._trend_service, self)
        self._trend_page.refresh()
        self._content_stack.addWidget(self._trend_page)

        right.addWidget(self._content_stack, 1)
        root.addLayout(right, 1)

        # Set initial page
        self._nav_group.button(page_idx).setChecked(True)
        self._content_stack.setCurrentIndex(page_idx)
        self._update_page_header(page_idx)

    @staticmethod
    def _wrap_scroll(widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
        )
        scroll.setWidget(widget)
        return scroll

    def _build_nav_rail(self) -> QFrame:
        rail = QFrame()
        rail.setObjectName("navRail")
        rail.setFixedWidth(T.NAV_WIDTH)
        rail.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(rail)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(6)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        brand_mark = QLabel("◉")
        brand_mark.setObjectName("navBrandMark")
        brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_row.addWidget(brand_mark)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        brand_name = QLabel("专注舱")
        brand_name.setObjectName("navBrand")
        brand_text.addWidget(brand_name)
        brand_caption = QLabel("FOCUS CAPSULE")
        brand_caption.setObjectName("navBrandCaption")
        brand_text.addWidget(brand_caption)
        brand_row.addLayout(brand_text, 1)
        layout.addLayout(brand_row)
        layout.addSpacing(28)

        section_label = QLabel("专注空间")
        section_label.setObjectName("navSectionLabel")
        layout.addWidget(section_label)
        layout.addSpacing(4)

        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)

        nav_icons = ["◈", "◎", "◷", "▦", "⌁"]
        nav_labels = ["今日概览", "专注计划", "日程锁定", "专注日历", "数据趋势"]
        nav_tooltips = [
            "今日 · 任务与进展",
            "专注计划",
            "日程锁定",
            "日历",
            "趋势",
        ]

        for idx in range(5):
            btn = QPushButton(f"{nav_icons[idx]}    {nav_labels[idx]}")
            btn.setObjectName("navBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(nav_tooltips[idx])
            self._nav_group.addButton(btn, idx)
            layout.addWidget(btn)

        self._nav_group.idClicked.connect(self._set_page)
        layout.addStretch()

        local_card = QFrame()
        local_card.setObjectName("navLocalCard")
        local_layout = QVBoxLayout(local_card)
        local_layout.setContentsMargins(12, 10, 12, 10)
        local_layout.setSpacing(2)
        local_title = QLabel("●  本地专注空间")
        local_title.setObjectName("navLocalTitle")
        local_layout.addWidget(local_title)
        local_note = QLabel("记录只保存在这台电脑")
        local_note.setObjectName("navLocalNote")
        local_layout.addWidget(local_note)
        layout.addWidget(local_card)
        layout.addSpacing(10)

        divider = QFrame()
        divider.setObjectName("navDivider")
        divider.setFixedHeight(1)
        layout.addWidget(divider)
        layout.addSpacing(6)

        # History button (disabled in visual test)
        hist_btn = QPushButton("☷    历史记录")
        hist_btn.setObjectName("navSecondaryBtn")
        hist_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        hist_btn.setToolTip("\u5386\u53f2\u8bb0\u5f55")
        hist_btn.setEnabled(False)
        layout.addWidget(hist_btn)

        # Quit button
        quit_btn = QPushButton("⏻    退出专注舱")
        quit_btn.setObjectName("navSecondaryBtn")
        quit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        quit_btn.setToolTip("\u9000\u51fa")
        quit_btn.clicked.connect(QApplication.quit)
        layout.addWidget(quit_btn)

        return rail

    def _build_top_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("topBar")
        bar.setFixedHeight(T.TOP_BAR_HEIGHT)
        bar.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(32, 12, 28, 12)
        layout.setSpacing(16)

        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        title_box.setContentsMargins(0, 0, 0, 0)

        self._page_title_label = QLabel("\u4eca\u65e5")
        self._page_title_label.setObjectName("pageTitle")
        title_box.addWidget(self._page_title_label)

        self._page_subtitle_label = QLabel("今天的任务与专注进展")
        self._page_subtitle_label.setObjectName("pageSubtitle")
        title_box.addWidget(self._page_subtitle_label)

        layout.addLayout(title_box)

        self._date_label = QLabel("")
        self._date_label.setObjectName("dateChip")
        self._refresh_date_label()
        layout.addStretch()
        layout.addWidget(self._date_label)

        settings_btn = QPushButton("⚙  设置")
        settings_btn.setObjectName("topSettingsButton")
        settings_btn.setFixedHeight(36)
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setToolTip("\u8bbe\u7f6e")
        settings_btn.setEnabled(False)
        layout.addWidget(settings_btn)

        return bar

    def _refresh_date_label(self):
        today = china_today()
        weekdays = ["\u4e00", "\u4e8c", "\u4e09", "\u56db", "\u4e94", "\u516d", "\u65e5"]
        weekday_idx = today.weekday()
        self._date_label.setText(
            f"{today.year} 年 {today.month} 月 {today.day} 日  ·  周{weekdays[weekday_idx]}"
        )

    def _update_page_header(self, page_id: int) -> None:
        page_titles = {
            0: ("今日", "今天的任务与专注进展"),
            1: ("专注计划", "配置专注会话"),
            2: ("日程锁定", "自动化时间规则"),
            3: ("日历", "每日专注记录"),
            4: ("趋势", "专注数据分析"),
        }
        title, subtitle = page_titles.get(page_id, ("", ""))
        self._page_title_label.setText(title)
        self._page_subtitle_label.setText(subtitle)

    def _set_page(self, page_id: int) -> None:
        self._content_stack.setCurrentIndex(page_id)
        self._update_page_header(page_id)
        if page_id == 0 and hasattr(self, '_daily_goal_widget'):
            self._daily_goal_widget.refresh()
        elif page_id == 3 and hasattr(self, '_calendar_page'):
            self._calendar_page.refresh()
        elif page_id == 4 and hasattr(self, '_trend_page'):
            self._trend_page.refresh()

    @staticmethod
    def _make_placeholder(title: str, subtitle: str) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel(f"{title}\n{subtitle}")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(
            f"color:{T.get('TEXT_TERTIARY')}; font-size:16px;"
        )
        layout.addWidget(lbl)
        return w


# Aliasing fix for the import above
if "focus_capsule.daily_goal_page" in sys.modules:
    DailyGoalWidget_cls = sys.modules["focus_capsule.daily_goal_page"].DailyGoalWidget
else:
    from focus_capsule.daily_goal_page import DailyGoalWidget as DailyGoalWidget_cls


# ------------------------------------------------------------------
# Screenshot capture
# ------------------------------------------------------------------

def _capture_page(page_idx: int, res_w: int, res_h: int, page_name: str, out_dir: str):
    """Create a fresh app instance, show the page, capture screenshot."""
    print(f"  Capturing {page_name} at {res_w}x{res_h}...", flush=True)

    from PyQt6.QtGui import QImage, QPainter
    from PyQt6.QtWidgets import QApplication as _QApp
    app = _QApp.instance()
    if app is None:
        app = _QApp([sys.argv[0]])

    app.setStyleSheet(_build_stylesheet())
    _apply_app_font(app)

    win = VisualTestMainWindow(page_idx)
    win.resize(res_w, res_h)
    win.show()

    # Let the window settle
    time.sleep(1.5)

    filepath = os.path.join(out_dir, f"pa_{page_name}_{res_w}x{res_h}.png")
    filepath = os.path.abspath(filepath)

    # Render widget to QImage (works without display server)
    print(f"    Rendering widget to image... size={win.size().width()}x{win.size().height()}", flush=True)
    from PyQt6.QtGui import QColor as _QColor
    img = QImage(win.size(), QImage.Format.Format_ARGB32_Premultiplied)
    print(f"    QImage created: {img.width()}x{img.height()}", flush=True)
    img.fill(_QColor(T.current()["WINDOW_BG"]).rgba())
    print("    QImage filled", flush=True)
    p = QPainter(img)
    print("    QPainter started", flush=True)
    win.render(p)
    p.end()
    print(f"    QPainter ended, img.isNull={img.isNull()}", flush=True)

    if img.isNull():
        print("    Image is null/invalid, skipping", flush=True)
    else:
        # Save to temp ASCII path first (Qt has issues with non-ASCII paths)
        tmp_path = r"C:\Users\tele2\AppData\Local\Temp\focus_capsule_screenshot.png"
        saved = img.save(tmp_path, "PNG")
        print(f"    Saved to temp: {saved} at {tmp_path}", flush=True)
        if saved:
            if os.path.exists(tmp_path):
                # Ensure destination directory exists
                dest_dir = os.path.dirname(filepath)
                if dest_dir and not os.path.exists(dest_dir):
                    os.makedirs(dest_dir, exist_ok=True)

                # Read binary and write to destination (avoids non-ASCII path issues)
                with open(tmp_path, 'rb') as f_src:
                    data = f_src.read()
                with open(filepath, 'wb') as f_dst:
                    f_dst.write(data)
                filepath = os.path.abspath(filepath)
                if os.path.exists(filepath):
                    print(f"    Saved: {filepath} ({os.path.getsize(filepath):,} bytes)", flush=True)
                else:
                    print(f"    FAILED after write: {filepath}", flush=True)
            else:
                print(f"    Temp file not found: {tmp_path}", flush=True)
        else:
            print("    FAILED to save to temp", flush=True)

    app.quit()
    return filepath


def _run_screenshots(out_dir: str):
    """Capture all 4 target pages at 3 resolutions."""
    resolutions = [(1366, 768), (1440, 900), (1536, 1024)]
    pages = [
        (0, "shell", "应用外壳"),
        (0, "today", "今日页"),
        (3, "calendar", "日历页（含演示数据）"),
        (4, "trend", "趋势页（含演示数据）"),
    ]

    print(f"\n{'='*60}", flush=True)
    print("FOCUS CAPSULE VISUAL TEST — Screenshot Capture", flush=True)
    print(f"Output directory: {out_dir}", flush=True)
    print(f"{'='*60}", flush=True)

    for res_w, res_h in resolutions:
        print(f"\n{'─'*60}", flush=True)
        print(f"Resolution: {res_w}x{res_h}", flush=True)
        print(f"{'─'*60}", flush=True)

        for page_idx, page_name, desc in pages:
            _capture_page(page_idx, res_w, res_h, page_name, out_dir)

    print(f"\n{'='*60}", flush=True)
    print("Screenshot capture complete.", flush=True)
    print(f"Files saved to: {out_dir}", flush=True)
    print(f"{'='*60}", flush=True)


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():
    out_dir = os.environ.get("FOCUS_CAPSULE_SCREENSHOT_DIR", r"E:\专注神器")

    if os.environ.get("FOCUS_CAPSULE_SCREENSHOT") == "1":
        # Batch screenshot mode
        _run_screenshots(out_dir)
        return

    # Interactive preview mode
    page_idx = int(os.environ.get("FOCUS_CAPSULE_PAGE_INDEX", "0"))
    page_name = os.environ.get("FOCUS_CAPSULE_PAGE", "").lower()
    page_map = {"today": 0, "pomodoro": 1, "schedule": 2, "calendar": 3, "trend": 4}
    if page_name in page_map:
        page_idx = page_map[page_name]

    print(f"Focus Capsule Visual Test Mode — interactive preview (page {page_idx})", flush=True)

    app = QApplication(sys.argv)
    app.setStyleSheet(_build_stylesheet())
    _apply_app_font(app)

    win = VisualTestMainWindow(page_idx)
    win.resize(1440, 900)
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
