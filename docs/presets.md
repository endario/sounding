# Presets (#102)

A caller of `choose`/`rank` sets up to five knobs besides its candidates: `tier`, `deadline`,
`temperature`, `quota_weight` and `prefer`. Most callers do not know what a good `temperature` or
`quota_weight` is, and each writes its own constants: today the agent runner hard-codes
`temperature` 2 for one kind of use and 0 for another, and leaves `quota_weight` at the default. A
preset is a named set of those knobs, shipped as data, so a caller names a way of choosing instead
of tuning numbers. Prior art: OpenRouter's presets (`@preset/<slug>`), a named bundle of model,
routing and sampling settings that a request's own parameters override.

## Shape

In the catalog, beside tiers and offerings:

```toml
[presets.steady]            # take the best-scoring candidate; quota and time as the defaults weigh them
temperature = 0

[presets.spread]            # try near-equal candidates in turn, so each builds a record
temperature = 2

[presets.frugal]            # quota is scarce: a minute saved is worth less against it
quota_weight = 60
temperature = 0
```

- A preset may set `tier`, `temperature`, `quota_weight` and `prefer`, and nothing else. Not
  `deadline` (the size of a task is the caller's), not `candidates`, `exclude` or `vendors` (what
  a caller may use is the caller's).
- `unlimited choose --preset NAME ...` and `rank(..., preset="NAME")`: the preset fills every knob
  the caller did not give; one the caller gives wins, as on OpenRouter. `prefer` merges by name,
  the caller's value winning. A knob neither gives takes today's default.
- The request records `preset` and the effective values, so a decision is explainable without the
  catalog it was made under.
- An unknown preset name is refused. `unlimited presets [--json]` lists them with their values;
  `--catalog` includes them.
- A local catalog adds presets or replaces a shipped one by name, as it does offerings.
- unlimited never branches on a preset's name: it is only a label over the same parameters.

## Open questions

1. **Names: by how to choose, or by what the caller does?** The issue's examples (`analytical`,
   `code-review`, `design-critique`) name callers' scenarios, which CLAUDE.md keeps out of
   unlimited's shipped data. Proposed: ship presets named for how they choose (`steady`, `spread`,
   `frugal`), and let a caller name its own scenarios in its local catalog
   (`[presets.code-review]`) or, better, in its own code. The owner's examples then live where the
   scenario does.
2. **Which values ship.** The runner's two temperatures are the only settings in use; `frugal`'s
   60 is a judgment, not a measurement. Ship only `steady` and `spread` until a second caller's
   settings show another point worth naming?
3. **Whether `rank` takes `preset`,** or callers resolve it (`choice.preset(cat, name)` returns the
   dict and they merge). Taking it in `rank` keeps one merge rule and records the name; proposed.
