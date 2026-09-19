# sounding

Read AI-subscription quota usage, per window, as facts. Part of the 2mw2lt family.

```
sounding read [--vendor anthropic|openai|zai]... [--max-age SECONDS] --json
sounding capture claude-statusline      # in a Claude Code statusline script
```

Each reading gives each limit's window length, the fraction used so far, and its reset time. It
also gives whether the vendor says the limit is held, and why. sounding reports what the vendor
says: it never picks an account or draws a threshold. Choosing what to do with a reading is up to
the consumer.

## Sources

| Vendor | Local, no network | Network |
|---|---|---|
| Anthropic (Claude Code, claude.ai sign-in) | the `rate_limits` Claude Code hands its statusline, via `capture` | `oauth/usage` on Claude Code's own token |
| OpenAI (Codex, ChatGPT sign-in) | `rate_limits` in Codex's session logs | `wham/usage` on Codex's own token |
| Z.ai (GLM coding plan) | — | `quota/limit` on the plan's API key |
| OpenCode Go | — | `zen/go/v1/usage` on the Go API key |

The network endpoints are not officially documented and may change without notice. sounding
reads each harness's credential where the harness keeps it. It never refreshes a token or
writes a credential, and no token appears in its output, cache or errors.

## Cache

There is one cache file and one `flock` per vendor under `$XDG_CACHE_HOME/sounding`, mode
`0600`. Concurrent callers share one upstream request. A 429's `Retry-After` holds off every
caller until it passes, capped at 24 hours. On macOS the keychain is readable only from the
user's GUI session or launchd, not over plain ssh.

## Status

Pre-release. The schema (`"schema": 1`) may still change.
