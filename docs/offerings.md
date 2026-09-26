# Offerings: one model, several vendors

Issue #104. Today a model id belongs to one provider and a provider to one usage vendor, so a model
sold by two vendors can only be listed by inventing a second provider, which breaks the provider's
meaning as the model's maker. As on OpenRouter, a model should have several offerings, and the
chooser should spread one model's load across them.

**The offering id is the route key everywhere**: in the catalog's candidates, in `choose`'s input and
decision, in attempts and in the statistics learned from them. Provider and model are descriptive
fields of an offering.

## Delivery (after critic round 2: decompose)

1. **Catalog identity**: `schema = 2` with models and offerings, `Catalog.routes`
   listing every live route, schema-1 local files converted, bans and switches by vendor or
   offering id.
2. **Choice over routes**: `choose --quota` keyed by offering id (the caller's projection for the
   account it would launch that route on; routes on one account get the same value), attempts record
   an explicit `offering` field, statistics keyed by it (a failure on one vendor's route leaves
   another's alone), and `unavailable` counted against the route.
3. **Callers and data**: the agent runner and 2mw2lt read `routes` and launch by vendor; then the
   shipped catalog adds second offerings (Command Code for DeepSeek Flash and Muse Spark).

4. **What a route debits.** Two plans can sell one model at the same list price and debit their
   quota differently for it. A caller measured Command Code spending 1.5× (DeepSeek Flash), 2.2×
   (GLM Flash) and 5.4× (Muse Spark) the plan share OpenCode Go did, over four runs each; both
   publish the same per-token prices for those models (2026-09-26). Command Code's meter, read
   around single runs on this machine, debited 1.2 to 12.9 times list price for one run (two
   identical 28k-token runs: $0.010 and $0.016), so a per-run measurement is too noisy to learn from
   yet, and token counts at card prices do not predict it (critic rounds 1 and 2).

   So the catalog states it as data: an offering may carry `debit`, an absolute multiplier of the
   account share one run uses (1, the default, is a plain offering). The quota term of that route's
   expected cost is multiplied by it:

       E = … + quota_weight·debit_r·π(ρ_r) − preference

   With `π = exp(5(ρ − 1))`, a route debiting 2× loses to its sibling until the sibling's account is
   about 0.14 more used (ln 2 / 5): the cheaper plan takes the work while it has room, the dearer
   one is overflow. With no projection for either, the debit alone decides. A promotion still costs
   nothing; each candidate in the logged decision carries its `debit`. The shipped catalog sets none
   until a measurement is corroborated beyond one machine; learning `debit` from the attempt log and
   readings waits for data that supports it.

Deferred: pricing pay-per-token routes in dollars against a budget, and unlimited choosing accounts
itself.
