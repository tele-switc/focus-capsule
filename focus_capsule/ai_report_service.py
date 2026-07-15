"""AI daily report generation service.

Generates a daily summary of focus sessions. When an AI API key is
configured, calls the LLM to produce a reflective summary. If the API
is unavailable or no key is set, falls back to a local rule-based
summary that uses only the actual session data — never inventing numbers.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from focus_capsule.data_models import DailyReport, AppConfig
from focus_capsule.data_store import DataStore
from focus_capsule.history_db import HistoryService
from focus_capsule.models import SessionRecord
from focus_capsule.schedule_manager import china_now
from focus_capsule.trend_service import TrendService, DaySummary


CST = timezone(timedelta(hours=8), name="CST")


class AIReportService:
    """Generates daily reports, AI or local fallback."""

    def __init__(
        self,
        history: HistoryService,
        data_store: DataStore,
        app_config: AppConfig,
    ):
        self._history = history
        self._store = data_store
        self._config = app_config
        self._trend = TrendService(history, app_config)

    def generate_for_today(self) -> DailyReport:
        return self.generate_for_date(china_now().date())

    def generate_for_date(self, target_date) -> DailyReport:
        date_str = target_date.isoformat() if hasattr(target_date, "isoformat") else str(target_date)
        day_summary = self._get_day_summary(target_date)
        records = self._get_records_for_date(target_date)

        if self._config.ai_api_key and self._config.ai_daily_report_enabled:
            report = self._generate_ai(date_str, day_summary, records)
        else:
            report = self._generate_local(date_str, day_summary, records)

        self._store.save_report(report)
        return report

    def _get_day_summary(self, target_date) -> DaySummary:
        records = self._get_records_for_date(target_date)
        s = DaySummary(date=target_date)
        for r in records:
            started = _parse_cst_date(r.started_at)
            if started and started == target_date:
                s.total_focus_seconds += max(0, r.actual_focus_seconds)
                s.session_count += 1
                if r.outcome == "completed":
                    s.completed_count += 1
                elif r.outcome == "terminated":
                    s.terminated_count += 1
                s.distraction_count += r.distraction_count
                s.esc_used += r.esc_used
        return s

    def _get_records_for_date(self, target_date) -> list[SessionRecord]:
        all_records = self._history.load_history()
        result = []
        for r in all_records:
            d = _parse_cst_date(r.started_at)
            if d == target_date:
                result.append(r)
        return result

    # ── Local rule-based report ─────────────────────────────

    def _generate_local(
        self, date_str: str, day: DaySummary, records: list[SessionRecord]
    ) -> DailyReport:
        focus_min = day.focus_minutes
        total = day.session_count
        completed = day.completed_count
        rate = day.completion_rate

        # Top distractions
        distraction_counts: dict[str, int] = {}
        for r in records:
            for d in r.distractions:
                name = d.get("process_name", "") if isinstance(d, dict) else ""
                if name:
                    distraction_counts[name] = distraction_counts.get(name, 0) + 1
        top_distractions = sorted(distraction_counts, key=distraction_counts.get, reverse=True)[:5]

        # Summary
        if total == 0:
            summary = "今天还没有专注记录。开始第一轮专注吧 — 哪怕只有 10 分钟。"
            highlights = []
            suggestions = ["设一个可达成的每日目标（如 30 分钟）", "选一个需要的应用再开始"]
        else:
            hours = focus_min // 60
            mins = focus_min % 60
            time_text = f"{hours} 小时 {mins} 分钟" if hours else f"{mins} 分钟"
            summary = f"今天完成了 {total} 轮专注，累计专注 {time_text}。"

            if rate >= 0.8:
                summary += "完成率很高，节奏稳定。"
            elif rate >= 0.5:
                summary += "有一些中断，但整体在前进。"
            else:
                summary += "中断较多，明天可以试试更短的专注时长。"

            highlights = []
            if completed > 0:
                highlights.append(f"完整完成了 {completed} 轮专注")
            if day.distraction_count > 0:
                highlights.append(f"总共 {day.distraction_count} 次分心提醒")
            if day.esc_used > 0:
                highlights.append(f"使用了 {day.esc_used} 次临时休息")

            suggestions = []
            if rate < 0.5 and total > 0:
                suggestions.append("尝试缩短单轮专注时长（如 15-20 分钟）以提高完成率")
            if day.distraction_count > total * 2 and total > 0:
                suggestions.append("分心较频繁，可以考虑切换到标准或深度模式")
            if day.esc_used > total:
                suggestions.append("休息次数较多，检查一下是否需要调整工作环境")
            if not suggestions:
                suggestions.append("保持节奏，继续积累")
            if focus_min < 30:
                suggestions.append("今天专注时间较短，明天可以增加一点")

        return DailyReport(
            date_str=date_str,
            summary=summary,
            highlights=highlights,
            suggestions=suggestions,
            total_focus_minutes=focus_min,
            total_sessions=total,
            completion_rate=round(rate, 2),
            top_distractions=top_distractions,
            generated_at=china_now().isoformat(),
            source="local",
        )

    # ── AI-powered report ────────────────────────────────────

    def _generate_ai(
        self, date_str: str, day: DaySummary, records: list[SessionRecord]
    ) -> DailyReport:
        local = self._generate_local(date_str, day, records)
        try:
            import urllib.request
            import urllib.error

            system_prompt = (
                "你是一个专注教练。根据用户今天的专注数据写一段简短的每日总结（80-150字）。"
                "要求：用中文，语气温和鼓励但不说空话。"
                "只基于提供的数据进行评论，绝对不要编造任何数字或事件。"
                "如果数据为零或很少，要承认这一点并给出简单可行的建议。"
                "格式要求：\n"
                "summary: 一段话总结\n"
                "highlights: 亮点列表（每条一行，最多3条）\n"
                "suggestions: 建议列表（每条一行，最多2条）"
            )

            user_data = (
                f"日期: {date_str}\n"
                f"专注轮数: {day.session_count}\n"
                f"完整完成: {day.completed_count}\n"
                f"提前结束: {day.terminated_count}\n"
                f"累计专注分钟: {day.focus_minutes}\n"
                f"完成率: {day.completion_rate:.1%}\n"
                f"分心次数: {day.distraction_count}\n"
                f"休息次数: {day.esc_used}\n"
                f"主要分心应用: {', '.join(local.top_distractions) or '无'}\n"
            )

            body = json.dumps({
                "model": self._config.ai_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_data},
                ],
                "max_tokens": 400,
                "temperature": 0.7,
            }).encode("utf-8")

            req = urllib.request.Request(
                self._config.ai_api_url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._config.ai_api_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            parsed = self._parse_ai_content(content)

            local.summary = parsed.get("summary", local.summary)
            local.highlights = parsed.get("highlights", local.highlights)
            local.suggestions = parsed.get("suggestions", local.suggestions)
            local.source = "ai"
            local.generated_at = china_now().isoformat()
        except Exception as e:
            logging.warning("AI report generation failed: %s", e)
        return local

    @staticmethod
    def _parse_ai_content(content: str) -> dict:
        result = {"summary": "", "highlights": [], "suggestions": []}
        current_key = None
        for line in content.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.lower().startswith("summary:"):
                result["summary"] = line[8:].strip()
                current_key = "summary"
            elif line.lower().startswith("highlights:"):
                current_key = "highlights"
            elif line.lower().startswith("suggestions:"):
                current_key = "suggestions"
            elif current_key in ("highlights", "suggestions"):
                cleaned = line.lstrip("-•·* ").strip()
                if cleaned:
                    result[current_key].append(cleaned)
            elif current_key == "summary":
                result["summary"] += " " + line
        return result


def _parse_cst_date(iso_str: str):
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=CST)
        return dt.astimezone(CST).date()
    except (TypeError, ValueError):
        return None
