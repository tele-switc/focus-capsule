"""严格模式：提前退出的三道纯逻辑锁。

对齐 Cold Turkey 的做法但不做驱动级对抗——用「冷静期倒计时 + 随机字符
+ 口令」三层，把「一时手痒」和「真的想结束」区分开：

* cooldown：确认后仍要等 N 分钟，期间可取消退出、专注照常计时；
* phrase：输入一段随机字符（长度可配 6–12）；
* passcode：输入用户自设口令（只存加盐哈希，不存明文）。

同时提供 :class:`ClockGuard`，用单调钟检测用户改系统时间绕过排程。
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# 冷静期允许的范围（分钟）
COOLDOWN_MINUTES_RANGE = (1, 240)
# 随机字符长度允许的范围
PHRASE_LENGTH_RANGE = (6, 12)
# 判定「改了系统时间」的容差（秒）：单调钟与墙上钟的偏差超过即视为篡改
CLOCK_DRIFT_TOLERANCE = 300
# 口令哈希参数
_SALT_BYTES = 16
_ITERATIONS = 120_000

_PHRASE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # 去掉易混的 I/O/0/1


@dataclass
class StrictPolicy:
    """一个会话或一条排程规则的严格程度。"""

    level: str = "off"  # off | cooldown | phrase | passcode
    cooldown_minutes: int = 5
    phrase_length: int = 8
    passcode_hash: str = ""  # 形如 "sha256$<salt_hex>$<digest_hex>"

    @property
    def is_strict(self) -> bool:
        return self.level in {"cooldown", "phrase", "passcode"}

    @property
    def cooldown_seconds(self) -> int:
        minutes = min(max(int(self.cooldown_minutes), COOLDOWN_MINUTES_RANGE[0]), COOLDOWN_MINUTES_RANGE[1])
        return minutes * 60

    def label(self) -> str:
        return {
            "off": "不锁定",
            "cooldown": "冷静期",
            "phrase": "输入随机字符",
            "passcode": "口令",
        }.get(self.level, "不锁定")

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "cooldown_minutes": self.cooldown_minutes,
            "phrase_length": self.phrase_length,
            "passcode_hash": self.passcode_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "StrictPolicy":
        data = data or {}
        level = str(data.get("level", "off"))
        if level not in {"off", "cooldown", "phrase", "passcode"}:
            level = "off"
        return cls(
            level=level,
            cooldown_minutes=int(data.get("cooldown_minutes", 5) or 5),
            phrase_length=int(data.get("phrase_length", 8) or 8),
            passcode_hash=str(data.get("passcode_hash", "") or ""),
        )


# ── 口令哈希 ──────────────────────────────────────────────────


def hash_passcode(plain: str) -> str:
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_passcode(plain: str, stored: str) -> bool:
    try:
        algo, iterations, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    if algo != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", plain.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
    )
    return secrets.compare_digest(digest.hex(), digest_hex)


def make_phrase(length: int = 8) -> str:
    length = min(max(int(length), PHRASE_LENGTH_RANGE[0]), PHRASE_LENGTH_RANGE[1])
    return "".join(secrets.choice(_PHRASE_ALPHABET) for _ in range(length))


# ── 提前退出闸门 ──────────────────────────────────────────────


@dataclass
class ExitGate:
    """管理一次「提前结束」请求需要满足的条件。

    用法::

        gate = ExitGate(policy)
        gate.begin()            # 用户点了「提前结束」
        gate.tick()             # 每秒驱动冷静期
        gate.ready_to_verify    # 冷静期是否走完
        gate.verify(phrase=..., passcode=...)
        gate.released           # 是否放行退出
    """

    policy: StrictPolicy
    elapsed_seconds: int = 0
    phrase: str = ""
    released: bool = False
    cancelled: bool = False
    failed_attempts: int = 0
    _remaining: int = field(default=0, repr=False)
    _started: bool = field(default=False, repr=False)

    def begin(self) -> None:
        if self._started:
            return
        self._started = True
        # 只有 cooldown 档带倒计时；phrase / passcode 档靠输入校验挡住即时退出
        self._remaining = self.policy.cooldown_seconds if self.policy.level == "cooldown" else 0
        if not self.policy.is_strict:
            self.released = True

    def cancel(self) -> None:
        """冷静期内反悔：专注继续，不留下任何破功记录。"""

        self.cancelled = True
        self.released = False

    def tick(self) -> int:
        """推进一秒，返回剩余冷静秒数。"""

        if self._remaining > 0:
            self._remaining -= 1
        return self._remaining

    @property
    def cooldown_remaining(self) -> int:
        return max(0, self._remaining)

    @property
    def waiting_for_cooldown(self) -> bool:
        return self._started and not self.released and self._remaining > 0

    @property
    def needs_phrase(self) -> bool:
        return (
            self.policy.level == "phrase"
            and self._remaining == 0
            and not self.released
        )

    @property
    def needs_passcode(self) -> bool:
        return (
            self.policy.level == "passcode"
            and self._remaining == 0
            and not self.released
        )

    @property
    def ready_to_verify(self) -> bool:
        return self._started and self._remaining == 0 and not self.released

    def verify(self, phrase: str = "", passcode: str = "") -> bool:
        if not self._started or self.released:
            return False
        if self._remaining > 0:
            return False
        if self.policy.level == "cooldown" or self.policy.level == "off":
            self.released = True
            return True
        if self.policy.level == "phrase":
            ok = bool(self.phrase) and phrase.strip().upper() == self.phrase
        elif self.policy.level == "passcode":
            ok = verify_passcode(passcode, self.policy.passcode_hash)
        else:
            ok = True
        if ok:
            self.released = True
        else:
            self.failed_attempts += 1
        return ok

    def arm_phrase(self) -> str:
        self.phrase = make_phrase(self.policy.phrase_length)
        return self.phrase

    def status_text(self) -> str:
        if self.released:
            return "已解锁，可结束本次专注"
        if self.waiting_for_cooldown:
            minutes, seconds = divmod(self.cooldown_remaining, 60)
            return f"冷静期剩余 {minutes:02d}:{seconds:02d}，期间专注照常计时"
        if self.needs_phrase:
            return f"请输入下方字符以确认结束（{self.policy.phrase_length} 位）"
        if self.needs_passcode:
            return "请输入你设置的专注口令"
        return "确认结束本次专注"


# ── 改时间检测 ────────────────────────────────────────────────


class ClockGuard:
    """用单调钟校准墙上钟，识别「把系统时间往前调以结束锁定」。

    状态落盘在用户数据目录，进程重启后仍可比较。
    """

    def __init__(self, path: Path | None = None):
        if path is None:
            base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".local" / "share")
            path = base / "FocusCapsule" / "clock_guard.json"
        self.path = Path(path)
        self._mono_anchor = time.monotonic()
        self._wall_anchor = time.time()

    def _load(self) -> dict[str, Any]:
        try:
            return json.loads(self.path.read_text("utf-8"))
        except Exception:
            return {}

    def _save(self, data: dict[str, Any]) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False), "utf-8")
            os.replace(tmp, self.path)
        except Exception:
            pass

    def check(self) -> tuple[bool, str]:
        """返回 (是否疑似篡改, 说明)。"""

        elapsed_mono = time.monotonic() - self._mono_anchor
        elapsed_wall = time.time() - self._wall_anchor
        drift = abs(elapsed_wall - elapsed_mono)
        state = self._load()
        last_wall = float(state.get("wall", 0) or 0)
        last_mono = float(state.get("mono", 0) or 0)
        wall_now = time.time()

        # 情况一：进程内墙上钟与单调钟脱钩（改时间会立刻体现）
        if drift > CLOCK_DRIFT_TOLERANCE:
            self._save({"wall": wall_now, "mono": time.monotonic()})
            return True, "系统时间在本次运行中被调整过"

        # 情况二：进程重启后墙上钟比上次记录倒退
        if last_wall and wall_now + 60 < last_wall:
            self._save({"wall": wall_now, "mono": time.monotonic()})
            return True, "系统时间被调回了过去"

        self._save({"wall": wall_now, "mono": time.monotonic()})
        return False, ""

    def now(self) -> datetime:
        """经过单调校准的当前时间（篡改后返回不早于上次记录的时间）。"""

        state = self._load()
        wall = time.time()
        last_wall = float(state.get("wall", 0) or 0)
        if last_wall and wall < last_wall:
            # 时间被调回：按上次记录 + 单调增量给出时间
            wall = last_wall + (time.monotonic() - float(state.get("mono", 0) or 0))
        return datetime.fromtimestamp(wall)
