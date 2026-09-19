"""Z.ai GLM coding plan: `quota/limit` on the API key the claude-glm wrapper reads."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

from ..credential import Credential
from ..schema import OK, REFUSED, failed, limit, reading

VENDOR = "zai"
URL = "https://api.z.ai/api/monitor/usage/quota/limit"
# Minutes per Z.ai unit: 3 is hours, 6 is the plan's week. An unknown unit keeps no length.
UNIT_MINUTES = {3: 60, 6: 10080}
NAMES = {300: "five_hour", 10080: "seven_day"}


def _env_file() -> Path:
    return Path(os.environ.get("CLAUDE_GLM_ENV") or Path.home() / ".config" / "claude-glm.env")


def discover() -> list[Credential]:
    key = os.environ.get("GLM_API_KEY")
    if not key:
        try:
            for line in _env_file().read_text().splitlines():
                k, _, v = line.partition("=")
                if k.strip().removeprefix("export ").strip() == "GLM_API_KEY":
                    key = v.strip().strip("'\"") or None
        except OSError:
            pass
    if not key:
        return []
    # Z.ai publishes no account id, so a truncated hash of the key stands in.
    return [Credential(hashlib.sha256(key.encode()).hexdigest()[:16], {"key": key})]


def _millis(value: object) -> datetime | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    except (OSError, OverflowError, ValueError):
        return None


def _num(x: object) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def limits(body: dict, now: datetime) -> list[dict]:
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    out = []
    for l in data.get("limits") or []:
        if not isinstance(l, dict):
            continue
        unit, number = l.get("unit"), l.get("number")
        minutes = (UNIT_MINUTES[unit] * number if unit in UNIT_MINUTES
                   and isinstance(number, int) and not isinstance(number, bool) else None)
        resets = _millis(l.get("nextResetTime"))
        total, spent = l.get("usage"), l.get("currentValue")
        used = (spent / total if _num(total) and _num(spent) and total > 0
                and resets is not None and resets > now else None)
        # Z.ai has no word for a held limit short of the 429 at the cap, so `held` is unknown.
        out.append(limit(NAMES.get(minutes) or f"{str(l.get('type')).lower()} {unit}x{number}",
                         window_minutes=minutes, used_at_least=used, resets_at=resets, held=None))
    return out


def read(cred: Credential, now: datetime, get) -> dict:
    ans = get(URL, {"Authorization": f"Bearer {cred.secret['key']}"}, now)
    if ans.body is None:
        return failed(VENDOR, cred.account, now, ans)
    if ans.body.get("success") is False:
        code = ans.body.get("code")
        return reading(VENDOR, cred.account, now, REFUSED,
                       why=f"vendor-{code}" if isinstance(code, int) else "vendor-refused")
    return reading(VENDOR, cred.account, now, OK, limits=limits(ans.body, now))
