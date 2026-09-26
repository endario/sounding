# Offerings: one model, several vendors

Issue #104. Today a model id belongs to one provider and a provider to one usage vendor, so a model
sold by two vendors can only be listed by inventing a second provider, which breaks the provider's
meaning as the model's maker. As on OpenRouter, a model should have several offerings, and the
chooser should spread one model's load across them.

**The offering id is the route key everywhere**: in the catalog's candidates, in `choose`'s input and
decision, in attempts and in the statistics learned from them. Provider and model are descriptive
fields of an offering.

## Data model (catalog `schema = 2`)

```toml
schema = 2
tiers = ["standard", "heavy"]

[models."deepseek-v4.1-flash"]       # one entry per model, keyed by a vendor-neutral name
provider = "deepseek"                # its maker
tiers = ["standard"]                 # the tiers it may serve
intelligence = 39.5                  # optional, vendor-independent

[[offerings]]                        # a vendor's route to that model, most preferred first
id = "opencode-go/deepseek-v4.1-flash"   # the vendor's id for it: unique, what a caller launches
model = "deepseek-v4.1-flash"
vendor = "opencode"                  # the vendor whose account a use spends
plan = "go"                          # optional
tok_s = 237                          # optional published figures, with source and as_of
price = { input = 0.15, output = 0.60, cache_read = 0.003 }
source = "https://…"
as_of = 2026-09-26

[[offerings]]
id = "commandcode/deepseek/deepseek-v4.1-flash"
model = "deepseek-v4.1-flash"
vendor = "commandcode"
free_until = 2026-09-30              # optional: a promotion through that day, UTC
```

- A **model** has one maker and the tiers it serves; it needs no `[providers]` table.
- **Cards** become offerings' published figures; `intelligence` moves to the model.
- **Promotions** become an offering attribute (`free_until`).
- **Order** among one model's offerings is the catalog keeper's stated preference, used where a
  caller asks for one offering without choosing (below).
- **Merging a local file**: models merge key by key; an offering replaces the shipped offering with
  the same id, or is added; `tiers` and `tie_preference` are replaced whole; `banned` is the union.
- **Bans and switches** take a provider, a model, a vendor, an offering id, or `provider:model`
  (`unlimited off commandcode` takes every Command Code offering out).
- A local **schema-1** file is read as before and converted on load: each provider's model at a tier
  becomes a model of that provider with one offering of the same id on the provider's `usage` vendor.

## Choice over offerings

`choose` candidates are offerings: every live offering, at the tier, of a model whose maker is among
the providers the caller allows. The caller's quota input is keyed by **offering id**
(`--quota ID=ρ`): the projected use of the account it would launch that offering on, since only the
caller knows which account and plan that is. An offering with no `ρ` is priced at the limit, a
promotion at zero. The decision names the offering id, with its provider, model and vendor.

Statistics are per offering id, so a failure on one vendor's route does not lower another's. An
attempt records the offering id it launched (its `model` field today holds exactly that id, so the
history already logged carries over). `unavailable` now counts against the offering: a vendor that
cannot be reached is that route's failure, not the model's elsewhere.

Out of this change: pricing pay-per-token offerings in dollars, and unlimited choosing the account
from its own readings. Both need an unambiguous account and price contract first.

## Compatibility for callers that have not moved

- `Catalog.candidates(tier)` returns every live offering (`provider`, `model` = the offering id,
  `promoted`), promotions first, then models in file order and their offerings in preference order.
- `Catalog.model(provider, tier)` returns the provider's most preferred live offering at the tier,
  and `provider_of(id)` the maker of an offering id.
- `models --catalog` adds `models` and `offerings`, and keeps a derived `providers` view (each
  provider's most preferred offering per tier, with its vendor as `usage`) for callers still reading
  it.
- `choose --quota` keyed by a provider name is refused with a message: a provider no longer names
  one vendor.

## Callers (outside unlimited)

A caller launches an offering by its vendor (its own mapping from vendor to launcher) and its id,
passes `ρ` per offering for the account it would use, and records the attempt with that id.
