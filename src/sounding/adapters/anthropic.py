"""Anthropic (Claude Code, claude.ai sign-in). Two sources:

- local: the `rate_limits` Claude Code hands its statusline, saved by `sounding capture
  claude-statusline` into a per-account file. No network, no token.
- api: `oauth/usage` on the token Claude Code keeps in the macOS keychain (or
  `.credentials.json` elsewhere). Read, never refreshed: refreshing rotates the refresh token and
  would break Claude Code's own copy.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from ..credential import Credential
from ..schema import OK, UNREAD, failed, limit, reading

VENDOR = "anthropic"
URL = "https://api.anthropic.com/api/oauth/usage"
WINDOWS = {"five_hour": 300, "seven_day": 10080, "seven_day_opus": 10080, "seven_day_sonnet": 10080}
KEYCHAIN = "Claude Code-credentials"


def _default_dir() -> Path:
    return Path.home() / ".claude"


def _wrapped_dirs() -> set[Path]:
    """Config directories that wrappers (claude-glm, claude-kimi, …) point at another vendor.
    Their keychain slot can hold a copy of an Anthropic credential, which would be read twice."""
    out = set()
    for env in (Path.home() / ".config").glob("claude-*.env"):
        try:
            for line in env.read_text().splitlines():
                k, _, v = line.partition("=")
                if k.strip().removeprefix("export ").strip() == "CLAUDE_CONFIG_DIR":
                    out.add(Path(os.path.expandvars(os.path.expanduser(v.strip().strip("'\"")))).resolve())
        except OSError:
            continue
    return out


def _identity(config_dir: Path) -> str | None:
    for f in (config_dir / ".claude.json",) + ((Path.home() / ".claude.json",)
                                               if config_dir.resolve() == _default_dir().resolve() else ()):
        try:
            o = json.loads(f.read_text()).get("oauthAccount")
        except (OSError, ValueError, AttributeError):
            continue
        uuid = o.get("accountUuid") if isinstance(o, dict) else None
        if isinstance(uuid, str) and uuid:
            return uuid
    return None


def config_dirs() -> list[Path]:
    skip = _wrapped_dirs()
    home = Path.home()
    return sorted(p for p in home.glob(".claude*") if p.is_dir() and p.resolve() not in skip
                  and ((p / ".claude.json").is_file() or p.resolve() == _default_dir().resolve()))


def _services(config_dir: Path) -> list[str]:
    named = KEYCHAIN + "-" + hashlib.sha256(str(config_dir).encode()).hexdigest()[:8]
    # The default directory's suffixed item can go stale while the unsuffixed one stays current.
    return [named, KEYCHAIN] if config_dir.resolve() == _default_dir().resolve() else [named]


def _oauth(config_dir: Path) -> list[dict]:
    recs = []
    if sys.platform == "darwin":
        for service in _services(config_dir):
            r = subprocess.run(["security", "find-generic-password", "-s", service, "-w"],
                               capture_output=True, text=True)
            if r.returncode == 0:
                try:
                    recs.append(json.loads(r.stdout).get("claudeAiOauth"))
                except (ValueError, AttributeError):
                    pass
    try:
        recs.append(json.loads((config_dir / ".credentials.json").read_text()).get("claudeAiOauth"))
    except (OSError, ValueError, AttributeError):
        pass
    return [r for r in recs if isinstance(r, dict) and isinstance(r.get("accessToken"), str)]


def _expiry(rec: dict) -> datetime | None:
    at = rec.get("expiresAt")
    if isinstance(at, bool) or not isinstance(at, (int, float)):
        return None
    try:
        return datetime.fromtimestamp(at / 1000, tz=timezone.utc)
    except (OSError, OverflowError, ValueError):
        return None


def discover() -> list[Credential]:
    """One credential per account. An account signed in under several directories is read once,
    on whichever token is unexpired (or, failing that, any)."""
    now = datetime.now(timezone.utc)
    found: dict[str, list[dict]] = {}
    for d in config_dirs():
        who = _identity(d)
        if who is not None:
            found.setdefault(who, []).extend(_oauth(d))
    best = {who: next((r for r in recs if (_expiry(r) or now) > now), recs[0] if recs else {})
            for who, recs in found.items()}
    return [Credential(who, {"token": rec.get("accessToken"), "expires": rec.get("expiresAt")})
            for who, rec in sorted(best.items())]


def _limits(body: dict, now: datetime) -> list[dict]:
    out = []
    for name, w in body.items():
        if not isinstance(w, dict) or "utilization" not in w:
            continue
        resets = _iso(w.get("resets_at"))
        u = w.get("utilization")
        out.append(limit(name, window_minutes=WINDOWS.get(name),
                         used_at_least=u / 100 if isinstance(u, (int, float)) and not isinstance(u, bool)
                         and resets is not None and resets > now else None,
                         resets_at=resets, held=None))
    return out


def _iso(v: object) -> datetime | None:
    if not isinstance(v, str):
        return None
    try:
        t = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else None


def read(cred: Credential, now: datetime, get) -> dict:
    token = cred.secret.get("token")
    if not token:
        return reading(VENDOR, cred.account, now, UNREAD, why="no-credential")
    exp = _expiry({"expiresAt": cred.secret.get("expires")})
    if exp is not None and exp <= now:
        # Asking on an expired token answers 429, which reads like a real limit.
        return reading(VENDOR, cred.account, now, UNREAD, why="credential-expired")
    ans = get(URL, {"Authorization": f"Bearer {token}", "anthropic-beta": "oauth-2025-04-20"}, now)
    if ans.body is None:
        return failed(VENDOR, cred.account, now, ans)
    return reading(VENDOR, cred.account, now, OK, limits=_limits(ans.body, now))


# ---- local: statusline captures ----------------------------------------------------------

def capture_dir() -> Path:
    from ..cache import default_dir
    return default_dir() / "claude-statusline"


def capture(payload: dict, now: datetime) -> dict | None:
    """Save the statusline's `rate_limits` for the account this Claude Code runs as. Returns the
    reading written, or None when the payload has none (API-key sign-in, or before the first
    response)."""
    rl = payload.get("rate_limits") if isinstance(payload, dict) else None
    d = Path(os.environ.get("CLAUDE_CONFIG_DIR") or _default_dir()).expanduser()
    who = _identity(d)
    if not isinstance(rl, dict) or who is None:
        return None
    out = []
    for name in ("five_hour", "seven_day"):
        w = rl.get(name)
        if not isinstance(w, dict):
            continue
        at, pct = w.get("resets_at"), w.get("used_percentage")
        try:
            resets = datetime.fromtimestamp(at, tz=timezone.utc) if isinstance(at, (int, float)) \
                and not isinstance(at, bool) else None
        except (OSError, OverflowError, ValueError):
            resets = None
        out.append(limit(name, window_minutes=WINDOWS[name],
                         used_at_least=pct / 100 if isinstance(pct, (int, float)) and not isinstance(pct, bool)
                         and resets is not None and resets > now else None,
                         resets_at=resets, held=None))
    if not out:
        return None
    r = reading(VENDOR, who, now, OK, limits=out, source="statusline")
    path = capture_dir()
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path / f".{who}.tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(r, f)
    os.replace(tmp, path / f"{who}.json")
    return r


def local(now: datetime) -> list[dict]:
    out = []
    for f in capture_dir().glob("*.json"):
        try:
            r = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(r, dict) and r.get("vendor") == VENDOR and r.get("account"):
            out.append(r)
    return out
