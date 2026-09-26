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

4. **What a route spends.** Two plans can sell one model at different rates: measured by a caller
   over four runs each, Command Code spent 1.5× (DeepSeek Flash), 2.2× (GLM Flash) and 5.4× (Muse
   Spark) what OpenCode Go did. The quota price `π(ρ)` says how scarce an account is, not how much
   of it one run uses, so today the dearer route wins whenever its account is emptier. Each route's
   quota term is scaled by its expected spend relative to the other candidates':

       s_r = cost_r / median(cost over the candidates with one)      (1 when cost_r is unknown)
       E   = … + quota_weight·π(ρ_r)·s_r − preference

   `cost_r`, in USD per run, is the route's decayed mean tokens from the attempt log (`in`, `out`,
   `cache`) at its vendor's card price (the card whose vendor and models match the offering), the
   figure `unlimited cards` already shows; with fewer than one attempt's weight of tokens, the
   model's mean tokens on any route stand in, at this route's price. A route with no card price, or
   a promotion, keeps `s = 1` and `π` as today. The median makes `s` dimensionless and leaves a
   single candidate's cost exactly as before. Each candidate in the logged decision carries `cost`
   and `s`.

   Cards gain the OpenCode Go prices where OpenCode publishes them. Nothing changes for a caller:
   the flags are the same, and a model sold by one vendor scores as it does now.

Deferred: pricing pay-per-token routes in dollars against a budget, and unlimited choosing accounts
itself.
