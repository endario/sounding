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

4. **What a route spends — measured before it is priced.** Two plans can sell one model and debit
   their quota differently for it: a caller measured Command Code spending 1.5× (DeepSeek Flash),
   2.2× (GLM Flash) and 5.4× (Muse Spark) what OpenCode Go did over four runs each, though both
   publish the same per-token list prices for those models (checked 2026-09-26). So token counts at
   card prices cannot stand in for it (critic round 1): each plan's own meter can.

   **4a, measure.** unlimited already keeps every reading's windows as samples (`projection`), and
   the attempt log names the account each attempt ran on. For an attempt with an end and an
   account, whose account ran nothing else between the last sample before its start and the first
   after its end, its **use** of each window is the rise in that window's used fraction between
   those two samples (same reset; a reset in between discards it). `unlimited outcomes` reports, per
   route, the decayed mean use of each window role and how many attempts it rests on. Use by
   anything this log does not see (another machine, a person) lands in the same readings and
   inflates it; that is reported, not corrected. Nothing in `choose` changes.

   **4b, price.** Once 4a shows routes' use differing reliably (the three measured models first),
   the quota term becomes `quota_weight·π(ρ_r)·u_r/ū`, where `u_r` is the route's measured use of
   the window its `ρ` is projected on and `ū` the median over candidates that have one (`u/ū = 1`
   with no measurement, and when `ū` is 0). Its design is settled on 4a's data, not now.

Deferred: pricing pay-per-token routes in dollars against a budget, and unlimited choosing accounts
itself.
