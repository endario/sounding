# Presets (#102)

A caller of `choose`/`rank` tunes `temperature` and `quota_weight`, and may lean with `prefer`.
Few callers know what good values are, so each keeps its own constants: the agent runner
hard-codes `temperature` 2 for one kind of use and 0 for another. The owner wants unlimited to
offer these as named, officially recommended ways of choosing, so a caller names one instead of
tuning or maintaining numbers (#102). Prior art, partial: OpenRouter's presets, a named bundle of
settings that a request's own parameters override.

## Shape

```toml
[presets.steady]   # the lowest expected cost, every time
temperature = 0

[presets.spread]   # near-equal candidates take turns, so each keeps a record
temperature = 2
```

- **What a preset may set:** `temperature`, `quota_weight` and `prefer`: how to choose. Not
  `tier`, `deadline`, `candidates`, `exclude` or `vendors`: what the task is and what the caller may
  use stay the caller's, and `--tier` stays required.
- **Use:** `unlimited choose --preset NAME` and `rank(..., preset="NAME")`. A knob the caller gives
  wins; one it omits comes from the preset; one neither gives takes today's default (temperature 0,
  quota weight 20). Omission is tracked: `rank`'s `temperature` and `quota_weight` default to
  `None`, and so do the CLI flags, so an explicit `--temperature 0` overrides a preset's 2.
- **`prefer`:** the preset's map and the caller's merge key by key, the caller's value winning for
  a name both give; the merged map then resolves per route as `prefer` always does (most specific
  name wins). A caller that wants none of a preset's leans passes its own value for those names.
- **One resolver:** `rank` resolves the preset; callers never merge by hand.
- **Recorded:** the request carries `preset` and the effective `temperature`, `quota_weight` and
  `prefer`, so a decision is explainable without the catalog it was made under (a preset is
  mutable data: a release or a local file can change it).
- **Catalog:** `[presets.NAME]` tables. A local catalog adds a preset, or replaces a shipped one of
  the same name whole (no field merge). Validation at load: known keys only, `temperature` and
  `quota_weight` finite and not negative, `prefer` minutes finite, `prefer` names known to the
  catalog; a malformed preset is a `CatalogError`. An unknown preset name at choice time is a
  `ValueError` (CLI exit 2). `--catalog` lists presets; `choose --help` names the shipped ones.
- **Names say how they choose, never what for.** unlimited never branches on a preset's name.

## Decided (medium, for the critic to check)

- **Shipped names are generic** (`steady`, `spread`). The issue's examples (`analytical`,
  `code-review`, `design-critique`) name callers' scenarios, which CLAUDE.md keeps out of unlimited's
  shipped data; a caller maps its scenario to a preset in its own code, or defines a
  scenario-named preset in its local catalog.
- **Only the two evidenced presets ship.** They are the runner's settings in use. A third (a
  quota-scarce `quota_weight`, say) ships when a caller's use shows the value.
- **Built now, not after a second caller** (critic round 1's alternative): the owner asked for
  presets so callers stop keeping these constants; the runner switches to them in the same stack,
  and 2mw2lt adopts them with `rank`.
