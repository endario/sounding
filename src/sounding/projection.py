"""Where each open window is heading: arithmetic on the readings sounding has already taken.

A reading says how much of a window is used; it cannot say whether that is a lot for the time
elapsed. The history is every reading of the current window, and the projection extends two paces
from it to the window's reset:

- the window's average pace so far (used / time since the window opened), and
- the recent pace, over the last seventh of the window (a day of a week, ~43 minutes of 5 hours).

`at_reset` is the pair as [low, high], unclamped: 1.07 means the pace would pass the limit.
`exhausts_at` is when the faster pace reaches 1.0, if that is before the reset. Neither is advice.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from .schema import iso, moment

# Readings of one window whose resets differ by less than this are the same window; vendors
# re-derive the reset per request and it drifts by fractions of a second.
SAME_WINDOW = timedelta(minutes=10)
# At most this many samples per window: a sample closer than window/SAMPLES to the last is skipped.
SAMPLES = 500
RECENT = 7  # the recent pace looks back window/RECENT
MIN_SPAN = 50  # a pace needs at least window/MIN_SPAN of time behind it


def _key(account: str | None, name: str) -> str:
    return f"{account}\t{name}"


def _sample(s: object) -> tuple | None:
    """A stored [taken_at, used, resets_at], parsed; None for anything else in the cache file."""
    if not (isinstance(s, list) and len(s) == 3 and isinstance(s[1], (int, float))):
        return None
    t, at = moment(s[0]), moment(s[2])
    return (t, s[1], at) if t is not None and at is not None else None


def _samples(v: object) -> list[tuple]:
    return [p for p in map(_sample, v) if p] if isinstance(v, list) else []


def _trackable(l: dict) -> bool:
    return isinstance(l.get("name"), str) and bool(l.get("window_minutes")) and l.get("used_at_least") is not None \
        and moment(l.get("resets_at")) is not None


def record(history: dict, readings: list[dict]) -> dict:
    """`history` with each ok reading's open windows appended. A window that has reset starts over."""
    out = dict(history)
    for r in readings:
        taken = moment(r.get("taken_at"))
        if r.get("status") != "ok" or taken is None:
            continue
        for l in r.get("limits", []):
            if not _trackable(l):
                continue
            key, resets = _key(r.get("account"), l["name"]), moment(l["resets_at"])
            samples = _samples(out.get(key))
            if samples and abs(samples[-1][2] - resets) >= SAME_WINDOW:
                samples = []
            if samples and taken - samples[-1][0] < timedelta(minutes=l["window_minutes"]) / SAMPLES:
                continue
            samples.append((taken, l["used_at_least"], resets))
            out[key] = [[iso(t), u, iso(at)] for t, u, at in samples]
    return out


def prune(history: dict, now: datetime) -> dict:
    """Drop windows that have reset."""
    return {k: v for k, v in history.items() if (s := _samples(v)) and s[-1][2] > now}


def project(samples: list, l: dict) -> dict | None:
    """The projection for limit `l` from its window's samples, or None where there is too little."""
    if not _trackable(l) or not samples:
        return None
    window = timedelta(minutes=l["window_minutes"])
    resets = moment(l["resets_at"])
    pts = [(t, u) for t, u, at in _samples(samples) if abs(at - resets) < SAME_WINDOW]
    if not pts:
        return None
    t, u = pts[-1]
    left, elapsed = resets - t, t - (resets - window)
    if left <= timedelta(0) or elapsed < window / MIN_SPAN:
        return None
    paces = [u / elapsed.total_seconds()]
    back = [(t0, u0) for t0, u0 in pts if t - window / RECENT <= t0 <= t - window / MIN_SPAN]
    if back:
        t0, u0 = back[0]
        paces.append(max(u - u0, 0.0) / (t - t0).total_seconds())
    ends = [u + p * left.total_seconds() for p in paces]
    fast = max(paces)
    exhausts = t + timedelta(seconds=(1 - u) / fast) if u < 1 < u + fast * left.total_seconds() else None
    return {"at_reset": [round(min(ends), 4), round(max(ends), 4)], "exhausts_at": iso(exhausts),
            "samples": len(pts), "since": iso(pts[0][0])}


def attach(r: dict, history: dict) -> dict:
    """`r` with a `projection` on each limit (None where there is none)."""
    return dict(r, limits=[dict(l, projection=project(history.get(_key(r.get("account"), l.get("name"))) or [], l))
                           for l in r.get("limits", [])])
