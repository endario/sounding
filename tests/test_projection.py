"""Projection: where an open window is heading, from the readings of it so far."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from sounding import cache, projection, show
from sounding.schema import limit, reading
from sounding.transport import Answer
from sounding.adapters import zai

NOW = datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)
WEEK = 10080
RESET = NOW + timedelta(days=3)  # four days of the week gone


def at(t, used, resets=RESET):
    return reading("zai", "a", t, "ok", limits=[
        limit("seven_day", window_minutes=WEEK, used_at_least=used, resets_at=resets, held=False)])


def history(*pairs):
    h = {}
    for t, u in pairs:
        h = projection.record(h, [at(t, u)])
    return h


def proj(h, t, used):
    return projection.attach(at(t, used), h)["limits"][0]["projection"]


class Project(unittest.TestCase):
    def test_a_steady_pace_projects_the_same_from_average_and_recent(self):
        # 10% a day since the window opened: 40% now, 70% at reset.
        h = history(*[(NOW - timedelta(days=d), 0.4 - 0.1 * d) for d in (1, 0)])
        self.assertEqual(proj(h, NOW, 0.4)["at_reset"], [0.7, 0.7])

    def test_a_recent_burst_raises_the_high_end_and_says_when_it_runs_out(self):
        # 20% in the last day after 20% over three: average 10%/day → 70%, recent 20%/day → 100%+.
        h = history((NOW - timedelta(days=1), 0.2), (NOW, 0.45))
        p = proj(h, NOW, 0.45)
        lo, hi = p["at_reset"]
        self.assertLess(lo, 1)
        self.assertGreater(hi, 1)
        self.assertEqual(p["exhausts_at"], (NOW + timedelta(days=2.2)).isoformat())

    def test_one_reading_gives_only_the_average_pace(self):
        p = proj(history((NOW, 0.4)), NOW, 0.4)
        self.assertEqual(p["at_reset"], [0.7, 0.7])
        self.assertEqual(p["samples"], 1)

    def test_nothing_is_projected_just_after_a_window_opens(self):
        opened = RESET - timedelta(minutes=WEEK)
        self.assertIsNone(proj(history((opened + timedelta(minutes=5), 0.01)), opened + timedelta(minutes=5), 0.01))

    def test_a_reset_starts_the_history_over(self):
        h = history((NOW - timedelta(days=1), 0.9))
        h = projection.record(h, [at(NOW, 0.05, resets=NOW + timedelta(days=7) - timedelta(hours=1))])
        self.assertEqual(len(h["a\tseven_day"]), 1)

    def test_readings_closer_than_the_sampling_step_are_not_kept(self):
        h = history((NOW, 0.4), (NOW + timedelta(minutes=5), 0.41))
        self.assertEqual(len(h["a\tseven_day"]), 1)

    def test_windows_that_have_reset_are_pruned(self):
        h = history((NOW, 0.4))
        self.assertEqual(projection.prune(h, RESET + timedelta(seconds=1)), {})

    def test_a_malformed_history_is_ignored_not_fatal(self):
        h = {"a\tseven_day": [["x", 0.1, None], "junk", [1, 2]]}
        self.assertIsNone(proj(h, NOW, 0.4))
        self.assertEqual(len(projection.record(h, [at(NOW, 0.4)])["a\tseven_day"]), 1)
        self.assertEqual(projection.prune({"k": "junk"}, NOW), {})

    def test_a_window_past_its_reset_is_not_projected(self):
        from sounding.schema import settled
        r = settled(at(NOW, 0.4), RESET + timedelta(seconds=1))
        self.assertIsNone(projection.attach(r, history((NOW, 0.4)))["limits"][0]["projection"])


class ThroughCache(unittest.TestCase):
    def test_history_accumulates_across_reads_and_reaches_the_reading(self):
        tmp = Path(tempfile.mkdtemp())
        used = {"v": 2000}

        def get(url, headers, now):
            return Answer({"code": 200, "success": True, "data": {"level": "max", "limits": [
                {"type": "CREDIT_LIMIT", "unit": 6, "number": 1, "usage": 10000, "currentValue": used["v"],
                 "nextResetTime": int(RESET.timestamp() * 1000)}]}}, 200, None)

        with mock.patch.dict(os.environ, {"GLM_API_KEY": "k", "XDG_CACHE_HOME": str(tmp)}):
            cache.through(zai, max_age=60, clock=lambda: NOW - timedelta(days=1), get=get)
            used["v"] = 4000
            out = cache.through(zai, max_age=60, clock=lambda: NOW, get=get)
        p = next(l for l in out[0]["limits"] if l["window_minutes"] == WEEK)["projection"]
        self.assertEqual(p["samples"], 2)
        self.assertEqual(p["at_reset"], [0.7, 1.0])


class Shown(unittest.TestCase):
    def test_the_status_row_shows_the_projected_range(self):
        r = projection.attach(at(NOW, 0.45), history((NOW - timedelta(days=1), 0.2), (NOW, 0.45)))
        with mock.patch.object(show, "_claude_dirs", lambda: {}):
            out = show.render([r], NOW)
        self.assertRegex(out, r"→ \d+–\d+% at reset, full in 2d 4h")

    def test_a_held_row_says_held_not_where_it_is_heading(self):
        r = projection.attach(at(NOW, 0.45), history((NOW, 0.45)))
        r["limits"][0]["held"] = True
        with mock.patch.object(show, "_claude_dirs", lambda: {}):
            self.assertNotIn("→", show.render([r], NOW))


if __name__ == "__main__":
    unittest.main()
