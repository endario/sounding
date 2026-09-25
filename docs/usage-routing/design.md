# Usage routing

Issue #92. Where the next unit of work should run, owned by unlimited and used by the agent runner
(`agent-runner/balance.py`) and 2mw2lt (`steering/spending.py`, doc 117). Built in three phases;
each ships and is judged before the next starts.

1. **Account verdicts.** Whether an account can take a unit of work, and how well spent its quota
   would be. Deterministic. Replaces the two consumers' duplicated logic.
2. **Model choice.** Which model, priced by the accounts that can run it, for a task of continuous
   difficulty. Deterministic, no learned state.
3. **Learning.** Record decisions and outcomes; evaluate offline; only then let a learned model
   steer.

The model catalog (`catalog.toml`) keeps saying what can run; readings keep reporting account
facts; consumers keep their hard constraints (host, maker independence, complement-of, machine
availability, failover).

## Phase 1: account verdicts

### Why first

Both consumers already decide, per account, whether it can take work and which account's quota is
best spent, and they disagree: on the same OpenCode Go reading the runner scores the month and 2mw2lt
the week; the runner prefers by name within a tie, 2mw2lt by the caller's key. Every new vendor
(Command Code) or rule (the monthly bucket) has had to be made twice. Phases 2 and 3 need this
verdict as their input anyway.

### Contract

A pure module, `unlimited.verdict`, over schema-1 readings (what `unlimited read` returns):

    verdict(reading, *, now, work, starts=None) -> Verdict
    order(entries, *, verdict_of, then, unread) -> list

`work` is the expected duration of the unit; `starts` defaults to `now`.

A `Verdict` is one of:

- `unread`, with a reason: no reading, not ok, stale, malformed, or a window the vendor must report
  is missing.
- `excluded`, with the window that binds and when the exclusion lifts: the vendor says it stopped
  the account (held with a stop basis), a window is used up, or a window is projected to run out
  before `starts + work`.
- `ranked`, with a tier and a score. Tier 0: no window projected past its limit. Tier 1: one is,
  but after the work ends; scored by the time until the first such window runs out. Within tier 0,
  the score is how much of the scored window's quota would otherwise expire, per unit of time left:
  `(1 − projected_at_reset) / fraction_of_window_left`.

The verdict names every window that bound it, so a caller can say why. It is bound to one account
(the reading's), so whoever launches the work launches that account.

Rules carried from doc 117 (`spending.verdict`), where they are already tested:

- Every live window constrains feasibility, whatever its length.
- A window that resets before the work starts constrains nothing.
- Only the vendor's own stop signal (`held` with a stop basis) excludes by itself; a threshold hold
  does not.
- unlimited's projection is used where it has one; otherwise the pace so far, floored while a
  window has only just opened.

The one rule that changes: **the scored window is the plan's monthly bucket where it enforces one,
else its weekly window** (owner, 2026-09-25; already the runner's rule, #160). Doc 117 capped the
scored window at a week because a week's quota expires first; the monthly bucket is scored instead
because it is the budget a plan runs out of, and the week still excludes the account when it would
run out during the work.

`order` ranks tier 0 before tier 1 and higher scores first; near ties (within 0.1 of the best still
standing) go to the caller's `then`. The runner's `then` is the catalog's `tie_preference`; 2mw2lt's
is its existing keys (DeepSeek, Grok, rotation, load).

### Stale readings and concurrency

A reading older than the caller's freshness bound is `unread`, never ranked. Two callers choosing at
once against the same account each see the same reading; this phase does not reserve capacity, and
says so. A reset during the work is covered by the runs-out check against `starts + work`.

### Proof

Both consumers' existing routing fixtures (`agent-runner/balance_test.py`, the hermetic suite's
balancing cases, `steering/test/spending_test.py`) are replayed through the new module, adapted to
schema-1 readings. Every decision must match today's except where the monthly-bucket rule changes it,
and each such change is listed. Only then does either consumer switch.

### Consumers

- The runner: `balance.py` becomes a caller of `unlimited verdict` (a CLI over the module); it keeps
  candidate order, account homes and the tie keys.
- 2mw2lt: `spending.verdict` and `order` become imports from unlimited; its wire readings carry the
  same fields under other names (`used` for `used_at_least`, `asked`), mapped at the boundary.

## Phase 2: model choice (sketch)

Each allow-listed model has an ability `θ_m` (prior: the Artificial Analysis Intelligence Index,
z-scored), a blended token price in dollars for our traffic (cache hit rate and output ratio measured
from our runs), and a speed (prior: Artificial Analysis output speed; corrected from our own run
times, since our endpoints are not the ones measured). A task has a continuous difficulty `b_t`, an
expected size, a required confidence per round kind, and a latency weight. Success is modelled as
`p = σ(a·(θ_m − b_t))`.

An account's price multiplier is the sum, over every window the work draws on, of that window's
expiring-quota price `λ_w(ρ_w)`: near zero when the quota would expire unused, rising steeply
towards the pay-as-you-go price as it nears its cap. A model's cost is its dollar price times the
multiplier of the best Phase-1-eligible account that runs it. A promotion is priced at zero but
still bound by its capacity. The choice is the cheapest model whose `p` meets the required
confidence; expected retries are charged only where a failed task is retried.

## Phase 3: learning (sketch)

Log every decision with its inputs and outcome. Evaluate the Phase 2 policy offline against that log
before any learned parameter steers routing. Outcome signals: whether the author acted on a finding,
whether the next round reversed it, whether the run completed. A judge model grading sampled reviews
is opt-in, and only a model already permitted to review the repository may see it.

## Open questions

1. Phase 1: whether the runner's per-provider "best account stands for the provider" and 2mw2lt's
   per-account ranking can share one `order`, or the runner keeps a reduction on top.
2. Phase 1: the freshness bound: the runner uses 300 s; 2mw2lt's is its own.
3. Phase 2: the calibration constants (IRT slope, index-to-θ mapping, the λ curve's shape, required
   confidence per round kind), set by hand from a worked example first.
