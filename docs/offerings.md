# Offerings: one model, several vendors

Issue #104. Today a model id belongs to one provider and a provider to one usage vendor, so a model
sold by two vendors can only be listed by inventing a second provider, which breaks the provider's
meaning as the model's maker. As on OpenRouter, a model should have several offerings, and the
chooser should spread one model's load across them by price, quota and reliability.

## Data model (catalog `schema = 2`)

```toml
schema = 2
tiers = ["standard", "heavy"]

[providers.deepseek]                 # a maker; facts about the maker only (none required)

[models."deepseek-v4.1-flash"]       # one entry per model, keyed by a vendor-neutral name
provider = "deepseek"                # its maker
tiers = ["standard"]                 # the tiers it may serve
intelligence = 39.5                  # optional, vendor-independent

[[offerings]]                        # a vendor selling that model
model = "deepseek-v4.1-flash"
vendor = "opencode"                  # the vendor whose account a use spends
id = "opencode-go/deepseek-v4.1-flash"   # the vendor's id for it: what a caller launches
plan = "go"                          # optional
tok_s = 237                          # optional published figures, with source and as_of
price = { input = 0.15, output = 0.60, cache_read = 0.003 }
source = "https://…"
as_of = 2026-09-26

[[offerings]]
model = "deepseek-v4.1-flash"
vendor = "commandcode"
id = "commandcode/deepseek/deepseek-v4.1-flash"
free_until = 2026-09-30              # optional: a promotion, no quota cost through that day
```

- A **model** has one maker and the tiers it serves. An **offering** is a vendor's route to it.
  An offering id is unique across the catalog.
- **Cards** become offerings' published figures; `intelligence` moves to the model.
- **Promotions** become an offering attribute (`free_until`, or `free = true` with no end).
- **Bans and switches** take a provider, a model, a vendor, an offering id, or `provider:model`.
- `tie_preference` stays a list of providers.

## Choice over offerings

`choose` candidates become offerings: every live offering of every model, at the tier, whose maker
is among the providers the caller allows. Each is scored as today (failure rate and durations per
offering; quota price), with one change: the caller's quota input is keyed by **vendor** (the
projected use of the account it would launch there), since one model's offerings spend different
vendors. The decision names provider, model, vendor and offering id.

Why per offering and not per model: two vendors selling the same model differ in speed, reliability
and price, which is the point of having both.

**Price across billing kinds**, all in minutes so they add:

- Subscription with a quota: the quota shadow price already used, `π(ρ)`.
- Promotion: zero.
- Pay per token (a vendor without quota readings): the offering's price for a typical use (tokens
  observed on that offering, else pooled) times a caller-supplied value of money
  (`--money-weight`, minutes per dollar; default 0, so dollars are ignored unless asked).
- A plan whose quota is in dollars (Command Code's): a subscription; its readings already give `ρ`.

A model normally served by its maker's own plan, with resellers as the fallback (GLM Flash on Z.ai),
needs no rule: while Z.ai's quota is cheap the reseller's price loses; as Z.ai's `ρ` climbs, it wins.

## Compatibility

- Schema 1 is refused with a message naming the new format (no machine holds a local schema-1 file
  today).
- `Catalog.candidates(tier)`, `model(provider, tier)` and `provider_of(id)` keep their meaning for
  existing callers: a provider's model at a tier is its first live offering there, in file order.
- `models --catalog` adds `models` and `offerings`, and keeps a derived `providers` view (each
  provider's first offering per tier, with that offering's vendor as `usage`), so a caller that has
  not moved still works, seeing one vendor per model.
- `choose --quota` accepts vendor keys; a provider key is read as that provider's first offering's
  vendor, for one release.

## Callers (outside unlimited)

A caller launches an offering by its vendor (its own mapping from vendor to launcher) and its id. The
agent runner's per-vendor scoring and account choice stay its own until unlimited chooses accounts
itself (not in this change).

## Not in this change

- unlimited choosing the account itself from its own readings (callers still pass `ρ` per vendor).
- Presets (#102).
