"""Automatic application classification with user overrides."""

from __future__ import annotations

from pathlib import Path

from focus_capsule.data_models import AppCategory, AppConfig

_CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "浏览器",
        (
            "chrome",
            "edge",
            "firefox",
            "brave",
            "opera",
            "vivaldi",
            "browser",
            "浏览器",
        ),
    ),
    (
        "编程",
        (
            "code",
            "visual studio",
            "pycharm",
            "intellij",
            "idea64",
            "webstorm",
            "android studio",
            "terminal",
            "powershell",
            "cmd.exe",
            "git",
            "docker",
            "postman",
        ),
    ),
    (
        "办公软件",
        (
            "word",
            "excel",
            "powerpoint",
            "office",
            "editors",
            "wps",
            "libreoffice",
            "acrobat",
            "pdf",
            "notepad",
            "记事本",
        ),
    ),
    (
        "通讯",
        (
            "wechat",
            "weixin",
            "dingtalk",
            "telegram",
            "discord",
            "slack",
            "teams",
            "zoom",
            "outlook",
            "mail",
            "钉钉",
            "微信",
        ),
    ),
    (
        "学习",
        (
            "anki",
            "duolingo",
            "每日西语",
            "ting_es",
            "kindle",
            "coursera",
            "notion",
            "obsidian",
            "学习",
        ),
    ),
    (
        "阅读",
        (
            "reader",
            "calibre",
            "book",
            "read",
            "阅读",
        ),
    ),
    (
        "影音娱乐",
        (
            "spotify",
            "music",
            "video",
            "vlc",
            "potplayer",
            "bilibili",
            "netflix",
            "youtube",
            "音乐",
            "视频",
        ),
    ),
    (
        "游戏",
        (
            "steam",
            "epicgames",
            "game",
            "gaming",
            "minecraft",
            "roblox",
            "游戏",
        ),
    ),
    (
        "系统工具",
        (
            "explorer",
            "settings",
            "control",
            "taskmgr",
            "snippingtool",
            "calculator",
            "7z",
            "winrar",
            "系统",
            "设置",
            "计算器",
        ),
    ),
    (
        "工作",
        (
            "figma",
            "photoshop",
            "illustrator",
            "blender",
            "autocad",
            "premiere",
            "after effects",
        ),
    ),
)


def infer_app_category(
    process_name: str,
    display_name: str = "",
    custom_path: str = "",
) -> str:
    """Infer a broad category without changing an existing user choice."""

    haystack = " ".join(
        (
            str(process_name).casefold(),
            str(display_name).casefold(),
            Path(custom_path).stem.casefold() if custom_path else "",
            str(custom_path).casefold(),
        )
    )
    for category, keywords in _CATEGORY_KEYWORDS:
        if any(keyword.casefold() in haystack for keyword in keywords):
            return category
    return "其他"


def merge_catalog_categories(
    config: AppConfig,
    catalog: list[dict],
) -> tuple[AppConfig, bool]:
    """Add newly discovered apps while preserving all user classifications."""

    existing = {
        item.process_name.strip().casefold(): item
        for item in config.app_categories
        if item.process_name.strip()
    }
    changed = False
    for raw in catalog:
        process = str(raw.get("process_name", "")).strip().casefold()
        display = str(raw.get("display_name", "")).strip()
        path = str(raw.get("custom_path", "")).strip()
        if not process or not display:
            continue
        current = existing.get(process)
        if current is not None:
            if path and not current.custom_path:
                current.custom_path = path
                changed = True
            if display and not current.display_name:
                current.display_name = display
                changed = True
            continue
        item = AppCategory(
            process_name=process,
            display_name=display,
            category=infer_app_category(process, display, path),
            icon_source=str(raw.get("icon_source", "")).strip(),
            custom_path=path,
        )
        config.app_categories.append(item)
        existing[process] = item
        changed = True
    config.app_categories.sort(
        key=lambda item: (item.category, item.display_name.casefold(), item.process_name)
    )
    return config, changed


def category_for_process(config: AppConfig, process_name: str) -> str:
    process = str(process_name).strip().casefold()
    for item in config.app_categories:
        if item.process_name.strip().casefold() == process:
            return item.category or "其他"
    return infer_app_category(process)


def display_name_for_process(config: AppConfig, process_name: str) -> str:
    process = str(process_name).strip().casefold()
    for item in config.app_categories:
        if item.process_name.strip().casefold() == process:
            return item.display_name or process
    clean = Path(process).stem
    return clean or process
