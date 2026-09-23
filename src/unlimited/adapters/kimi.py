"""Moonshot Kimi Code coding plan: `/usages` on each API key the claude-kimi wrappers read."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..credential import Credential
from ..schema import OK, UNREAD, failed, limit, reading

VENDOR = "kimi"
BASE_URL = "https://api.kimi.com/coding/v1"
URL = f"{BASE_URL}/usages"
FALLBACK_URL = f"{BASE_URL}/usage"
# Minutes per Kimi window unit; a duration in an unrecognised unit keeps no length.
UNIT_MINUTES = {"MINUTE": 1, "HOUR": 60, "DAY": 1440, "MONTH": 43200}
NAMES = {300: "five_hour", 10080: "seven_day", 43200: "month"}
# `usages.limit_5h/limit_7d.used_ratio`: a fallback only. Confirmed against the real endpoint
# (and MoonshotAI/kimi-code#3951) to sit stuck at 0 while the account's real `usage`/`limits`
# counts, in the same response, show real activity — so it is read only when those are absent.
RATIO_WINDOWS = {"limit_5h": 300, "limit_7d": 10080}


def env_files() -> list[Path]:
    """Every wrapper's env file (claude-kimi, claude-kimi-2, ...), and $CLAUDE_KIMI_ENV. A Kimi
    session exports its own file and key, so neither may narrow discovery to that one account."""
    files = sorted((Path.home() / ".config").glob("claude-kimi*.env"))
    named = os.environ.get("CLAUDE_KIMI_ENV")
    return files + ([Path(named)] if named else [])


def key_in(path: Path) -> str | None:
    try:
        for line in path.read_text().splitlines():
            k, _, v = line.partition("=")
            if k.strip().removeprefix("export ").strip() == "KIMI_API_KEY":
                return v.strip().strip("'\"") or None
    except OSError:
        pass
    return None


def account_of(key: str) -> str:
    # Kimi publishes no account id on this endpoint, so a truncated hash of the key stands in.
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def discover() -> list[Credential]:
    keys = [os.environ.get("KIMI_API_KEY")] + [key_in(f) for f in env_files()]
    found = {account_of(k): k for k in keys if k}
    return [Credential(a, {"key": k}) for a, k in sorted(found.items())]


def _num(x: object) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _float(x: object) -> float | None:
    # `/usages`' `limit`/`used`/`remaining` come back as strings; its `used_ratio` does not.
    if _num(x):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x)
        except ValueError:
            return None
    return None


def _reset_at(d: dict, now: datetime) -> datetime | None:
    v = d.get("resetTime") or d.get("reset_at") or d.get("reset_time")
    if isinstance(v, str):
        try:
            t = datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            return None
        return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
    if _num(v):
        try:
            return datetime.fromtimestamp(v, tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None
    reset_in = _float(d.get("reset_in"))
    return now + timedelta(seconds=reset_in) if reset_in is not None else None


def _used_ratio(d: dict) -> float | None:
    lim = _float(d.get("limit"))
    if lim is None:
        lim = _float(d.get("limit_amount"))
    used = _float(d.get("used"))
    if used is None:
        used = _float(d.get("used_amount"))
    if used is None:
        remaining = _float(d.get("remaining"))
        used = lim - remaining if remaining is not None and lim is not None else None
    return used / lim if used is not None and lim is not None and lim > 0 else None


def _window_minutes(window: dict) -> int | None:
    duration = _float(window.get("duration"))
    unit = str(window.get("timeUnit") or window.get("time_unit") or "").upper()
    per_minute = next((v for u, v in UNIT_MINUTES.items() if u in unit), None)
    return int(duration * per_minute) if duration is not None and per_minute is not None else None


def _ratio_limits(usages: dict, now: datetime) -> list[dict]:
    out = []
    for key, minutes in RATIO_WINDOWS.items():
        w = usages.get(key)
        if not isinstance(w, dict):
            continue
        ratio, resets = _float(w.get("used_ratio")), _reset_at(w, now)
        if ratio is None and resets is None:
            continue
        out.append(limit(NAMES[minutes], window_minutes=minutes, used_at_least=ratio, resets_at=resets, held=None))
    return out


def limits(body: dict, now: datetime) -> list[dict]:
    out = []
    raw_limits = body.get("limits")
    for i, item in enumerate(raw_limits if isinstance(raw_limits, list) else []):
        if not isinstance(item, dict):
            continue
        detail = item.get("detail") if isinstance(item.get("detail"), dict) else item
        window = item.get("window") if isinstance(item.get("window"), dict) else {}
        minutes = _window_minutes(window)
        used, resets = _used_ratio(detail), _reset_at(detail, now)
        if used is None and resets is None:
            continue
        out.append(limit(NAMES.get(minutes, f"window_{i}"), window_minutes=minutes,
                         used_at_least=used, resets_at=resets, held=None))
    usage = body.get("usage")
    if isinstance(usage, dict):
        used, resets = _used_ratio(usage), _reset_at(usage, now)
        if used is not None or resets is not None:
            # The vendor's own Kimi Code CLI labels this top-level aggregate "Weekly Usage";
            # its reset time matches `usages.limit_7d`'s.
            out.append(limit("seven_day", window_minutes=10080, used_at_least=used, resets_at=resets, held=None))
    if out:
        return out
    usages = body.get("usages")
    if isinstance(usages, dict):
        # Last resort: `used_ratio` here is not to be trusted over real counts (see `_ratio_limits`
        # docstring) but is better than nothing when the account's plan omits `usage`/`limits`.
        found = _ratio_limits(usages, now)
        if found:
            return found
    data = body.get("data")
    for item in data if isinstance(data, list) else []:
        if not isinstance(item, dict):
            continue
        used, resets = _used_ratio(item), _reset_at(item, now)
        if used is None and resets is None:
            continue
        # The per-model breakdown shape: no window is named, so none is guessed.
        name = "all" if item.get("model_name") == "all" else str(item.get("model_name") or "model")
        out.append(limit(name, window_minutes=None, used_at_least=used, resets_at=resets, held=None))
    return out


def read(cred: Credential, now: datetime, get) -> dict:
    headers = {"Authorization": f"Bearer {cred.secret['key']}"}
    ans = get(URL, headers, now)
    if ans.status == 404:
        ans = get(FALLBACK_URL, headers, now)
    if ans.body is None:
        return failed(VENDOR, cred.account, now, ans)
    found = limits(ans.body, now)
    if not found:
        return reading(VENDOR, cred.account, now, UNREAD, why="no-limits")
    return reading(VENDOR, cred.account, now, OK, limits=found)
