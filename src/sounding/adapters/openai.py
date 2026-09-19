"""OpenAI Codex (ChatGPT sign-in): `/wham/usage` on the token in Codex's own auth.json."""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from ..credential import Credential
from ..schema import OK, UNREAD, failed, limit, reading

VENDOR = "openai"
URL = "https://chatgpt.com/backend-api/wham/usage"


def _home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")


def discover() -> list[Credential]:
    try:
        got = json.loads((_home() / "auth.json").read_text())
    except (OSError, ValueError):
        return []
    tokens = got.get("tokens") if isinstance(got, dict) else None
    if not (isinstance(tokens, dict) and isinstance(tokens.get("access_token"), str)):
        return []
    who = tokens.get("account_id")
    return [Credential(who if isinstance(who, str) and who else None,
                       {"access_token": tokens["access_token"], "account_id": who or ""})]


def _jwt_expiry(token: str) -> datetime | None:
    if token.count(".") != 2:
        return None
    part = token.split(".")[1]
    try:
        exp = json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))).get("exp")
        return datetime.fromtimestamp(exp, tz=timezone.utc) if isinstance(exp, (int, float)) else None
    except (ValueError, TypeError, AttributeError, OSError, OverflowError):
        return None


def _seconds(value: object) -> datetime | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return datetime.fromtimestamp(value, tz=timezone.utc)
    except (OSError, OverflowError, ValueError):
        return None


def limits(body: dict, now: datetime) -> list[dict]:
    named = [("codex", body.get("rate_limit"))]
    for extra in body.get("additional_rate_limits") or []:
        if isinstance(extra, dict):
            named.append((str(extra.get("limit_name") or extra.get("metered_feature")),
                          extra.get("rate_limit")))
    out = []
    for name, rl in named:
        if not isinstance(rl, dict):
            continue
        # The vendor's own word that the limit has stopped work; nothing is derived from a number.
        reached = rl.get("limit_reached") is True or rl.get("allowed") is False
        for which in ("primary", "secondary"):
            w = rl.get(f"{which}_window")
            if not isinstance(w, dict):
                continue
            resets = _seconds(w.get("reset_at"))
            pct = w.get("used_percent")
            secs = w.get("limit_window_seconds")
            out.append(limit(
                name if which == "primary" else f"{name} ({which})",
                window_minutes=secs // 60 if isinstance(secs, int) and not isinstance(secs, bool) else None,
                used_at_least=pct / 100 if isinstance(pct, (int, float)) and not isinstance(pct, bool)
                and resets is not None and resets > now else None,
                resets_at=resets, held=reached, held_why="limit_reached" if reached else None))
    return out


def read(cred: Credential, now: datetime, get) -> dict:
    token = cred.secret["access_token"]
    expires = _jwt_expiry(token)
    if expires is not None and expires <= now:
        # Codex refreshes its own token on its next run; sounding never writes auth.json.
        return reading(VENDOR, cred.account, now, UNREAD, why="credential-expired")
    ans = get(URL, {"Authorization": f"Bearer {token}",
                    "ChatGPT-Account-Id": str(cred.secret["account_id"])}, now)
    if ans.body is None:
        return failed(VENDOR, cred.account, now, ans)
    return reading(VENDOR, cred.account, now, OK, limits=limits(ans.body, now))
