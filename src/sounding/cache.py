"""The per-home cache. One file and one flock per vendor: the lock is held across the upstream
read, so a second process asking for the same vendor waits for the first one's answer instead of
asking again. Different vendors never wait on each other."""

from __future__ import annotations

import fcntl
import json
import os
from datetime import datetime
from pathlib import Path

from .schema import moment, settled


def default_dir() -> Path:
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "sounding"


def _age(r: dict, now: datetime) -> float | None:
    t = moment(r.get("taken_at"))
    return (now - t).total_seconds() if t is not None else None


def _backing_off(r: dict, now: datetime) -> bool:
    until = moment(r.get("retry_until"))
    return until is not None and until > now


def _write(path: Path, readings: list[dict]) -> None:
    tmp = path.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump({"readings": readings}, f)
    os.replace(tmp, path)


def through(adapter, *, max_age: float, clock, get, directory: Path | None = None) -> list[dict]:
    """This vendor's readings, from the cache when young enough, else asked upstream."""
    directory = directory or default_dir()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / f"{adapter.VENDOR}.json"
    with open(directory / f"{adapter.VENDOR}.lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        now = clock()  # after the wait: a reader that queued behind a fresh read sees it as fresh
        try:
            held = json.loads(path.read_text()).get("readings")
        except (OSError, ValueError, AttributeError):
            held = None
        cached = {r.get("account"): r for r in held or [] if isinstance(r, dict)}
        if cached and all(_backing_off(r, now) or (a := _age(r, now)) is not None and 0 <= a < max_age
                          for r in cached.values()):
            return [settled(r, now) for r in cached.values()]
        out = []
        for cred in adapter.discover():
            prior = cached.get(cred.account)
            # A refusal's deadline binds every caller, whatever --max-age it asked for.
            out.append(prior if prior is not None and _backing_off(prior, now)
                       else adapter.read(cred, now, get))
        _write(path, out)
        return [settled(r, now) for r in out]
