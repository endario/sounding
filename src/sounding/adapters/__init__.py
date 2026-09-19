"""Vendor adapters. Each exposes `VENDOR`, `discover() -> list[Credential]` and
`read(cred, now, get) -> reading`, where `get(url, headers, now)` returns a transport.Answer."""

from . import openai, zai

REGISTRY = {m.VENDOR: m for m in (openai, zai)}
