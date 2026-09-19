"""`sounding read [--vendor V]... [--max-age S] --json`"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from . import cache, transport
from .adapters import REGISTRY


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="sounding")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("read", help="print readings")
    r.add_argument("--vendor", action="append", choices=sorted(REGISTRY))
    r.add_argument("--max-age", type=float, default=300.0)
    r.add_argument("--json", action="store_true", help="JSON output (the only format for now)")
    a = p.parse_args(argv)
    out = []
    for v in a.vendor or sorted(REGISTRY):
        out += cache.through(REGISTRY[v], max_age=a.max_age,
                             clock=lambda: datetime.now(timezone.utc), get=transport.get)
    json.dump(out, sys.stdout, indent=None)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
