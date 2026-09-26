# Exploring by default (Phase 2B, first step)

## Problem

`choose` defaults to `temperature` 0: always the lowest expected cost `E`. A route with more history
looks best, the others are never tried, so their records never improve (seen 2026-09-26: Codex took
14 of 17 finding rounds it was offered). Callers work around it with a temperature (the runner: 2 in
one kind of use, 0 in another), which no caller can set well; presets (0.0.54) named two such
settings and the owner found the names meaningless. The owner's rule: the default must be smart
enough that no caller wants to tune it; offer as few parameters as possible.

## Design

**Thompson sampling is the default.** For each call, each candidate's uncertain quantities are drawn
from what its record supports, instead of taken at their means:

- failure rate `p ~ Beta(0.5 + Σw·fail, 4.5 + Σw·ok)` (the posterior `p` already is the mean of);
- log time to succeed `μ ~ Normal(μ_post, σ² / (3 + Σw·ok))`, `T_ok = exp(μ + σ²/2)`, with `μ_post`
  and the pooled `σ²` as today.

`T_fail`, `T_next`, the quota price and the preference stay as today (means and caller inputs).
`E` is computed from the draw, and `order` is the candidates by drawn `E`, lowest first. A route
with little history draws widely and so is tried in proportion to its chance of being best; a
well-measured route draws near its mean; a route that cannot win on quota or preference whatever its
speed is not tried at all. As evidence accumulates, exploration fades by itself.

**Recorded.** Each candidate keeps `e` (at the means, as today) and gains `e_drawn`; `prob` becomes
each candidate's chance of coming first, estimated from 1000 draws on the decision's seed. The seed
replays the order.

**Parameters.** `--temperature` stays as the one override: `0` takes the lowest `E` at the means
with no exploration; above 0, today's softmax sampling. Omitted, Thompson sampling. `--quota-weight`
stays. Presets are removed (0.0.54, one caller, which moves in the same stack): the default makes
them unnecessary.

## Evidence (replayed on this machine's log, 2026-09-26)

For each logged finding-round decision, first-pick odds under Thompson sampling (2000 draws, the
record as it stood at that decision) against the softmax at temperature 2 that ran:

| decision | Thompson | softmax 2 |
|---|---|---|
| 11:22 | DeepSeek@CC 0.97, Claude 0.02, GLM 0.01 | 0.91, 0.06, 0.02 |
| 12:29 | DeepSeek@CC 0.79, Claude 0.16, GLM 0.05 | 0.72, 0.21, 0.06 |
| 12:52 | Codex 0.91, DeepSeek@CC 0.09 | 0.81, 0.19 |
| 13:03 | Claude 0.76, DeepSeek@CC 0.23 | 0.86, 0.14 |

Close to the hand-set temperature 2 with no parameter, and it declines to explore Muse on Command
Code (debit 5.4), whose quota price no speed can overcome, where the softmax spent 1–3% on it.

## Open

1. Is the `T_ok` draw the right uncertainty, or should `T_fail` also be drawn (its evidence is
   thin: most routes have no failures)?
2. Should a caller that wants no exploration (a single important use) pass `--temperature 0`, or is
   exploring there acceptable because an explored candidate is by construction plausibly best?
