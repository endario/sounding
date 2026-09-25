# Usage routing

Issue #92. One model for where a unit of work should run, owned by unlimited and used by the agent
runner (`balance.py`) and 2mw2lt (`steering/spending.py`, doc 117), replacing both.

Status: draft for critique. Nothing here is built.

## The question

Given a task and the models on the allow-list, which model (and which budget pool behind it)
spends the next unit of usage best? "Best" trades three things off: how likely the model is to do
the task well, what it really costs, and how long it takes. Today that is two ad-hoc heuristics,
a binary standard/heavy tier, and a tie rule.

## 1. Models

Each allow-listed model `m` carries:

- **Ability `θ_m`**: a latent skill on one scale. Prior: the Artificial Analysis Intelligence Index,
  z-scored across the allow-list. Its sub-indices (coding, agentic, terminal) can replace it later
  without changing anything below.
- **Token price `c_m`**: blended for our traffic, not list price:
  `c_m = c_in·(1−h) + c_cache·h + c_out·r`, with cache hit rate `h` and output ratio `r` measured
  from our own runs per task class.
- **Speed `v_m`**: output tokens per second, and time to first token. Prior: Artificial Analysis's
  published output speed. Posterior: our own runs (tokens and wall time are already recorded per
  run), since our endpoints (OpenCode Go, Command Code) are not the ones measured.

## 2. Tasks

Each task `t` carries:

- **Difficulty `b_t`** on the same scale as `θ`. It is continuous, and replaces standard/heavy.
  First estimate: a linear score over features consumers already have (diff size, files touched,
  new mechanism or security surface, critic vs review, finding vs final round). Learned from
  outcomes later (section 5).
- **Size `L_t`**: expected tokens, from the same features.
- **Required confidence `p*_t`**: the probability of a good outcome the task must reach. Set per
  round kind (a finding round lower, a final round higher).
- **Latency weight `κ_t`**: the cost of waiting. Zero for work that is not time-sensitive.

## 3. Success

Item response theory puts a model and a task on one scale:

    p(m, t) = σ(a · (θ_m − b_t))

The curve is flat at the top: on an easy task, more ability buys almost nothing, which is why a
heavy model on an easy task is waste.

## 4. Budget pools and their shadow prices

A pool `w` is what a run spends: a subscription window, a credit balance, a promotion. Each has a
shadow price `λ_w` per unit, from unlimited's own forecast `ρ_w` of the fraction used at reset:

    λ_w = λ_max · (e^{k·ρ_w} − 1) / (e^k − 1)

Quota projected to expire unused (`ρ ≪ 1`) is nearly free; a pool approaching its cap costs
towards `λ_max`, the pay-as-you-go price of the same work. A pay-as-you-go pool's `λ` is its
price; a live promotion's is zero. The exponential form is the standard one for online allocation
against budgets (Buchbinder and Naor), and `k` sets how early a pool starts to look expensive.

A model's effective price is its cheapest pool that can serve it:

    π_m = min over pools w serving m of  λ_w · c_m

## 5. The choice

Among models the consumer allows (host, maker independence, complement-of stay hard
constraints), take the cheapest in expected cost that is good enough:

    m* = argmin over m with p(m,t) ≥ p*_t of   π_m · L_t / p(m,t)  +  κ_t · L_t / v_m

`/p` charges for retries: a cheap model that fails half the time costs twice. If no model reaches
`p*_t`, take the most likely one.

Consequences, not rules:

- **Pareto front.** A model dominated on (price, ability, speed) is never chosen; the front is
  the set some task can select, and is computed only for display.
- **Load balancing.** As a pool fills, its `λ` rises and work moves elsewhere. The runner's tie
  preference and 2mw2lt's tier split both disappear into price.
- **Overkill.** An easy task reaches `p*` on a cheap model, so the heavy one loses on price.

## 6. Learning from outcomes

`θ_m`, per-class offsets on `b_t`, speeds and token counts are uncertain, and are updated from
outcomes. Selection uses Thompson sampling (choose on a draw from the posterior, not its mean), so
new and stealth models are explored while they are cheap.

The outcome of a review is a noisy reward from two sources:

- **Behaviour** (free, every run): the author acted on a finding (a later commit touches the cited
  lines), the next round did not reverse it, the run did not time out or fail.
- **A judge** (paid, sampled): a model from a maker other than the reviewer's grades a sample of
  reviews against the diff with a fixed rubric, preferring pairwise comparisons of two reviews of
  the same diff to absolute scores. Its reliability is itself estimated against the behavioural
  signal, and its reward is weighted by that reliability.

## 7. Interface

unlimited owns the allow-list, prices, priors, pools and the posterior:

    choose(task_features, constraints, now) -> [(model, pool, p, expected_cost, why)]
    record(run_outcome)

and a CLI for the runner. Consumers supply task features and constraints and report outcomes.

## Open questions

1. The calibration constants: the IRT slope `a`, the mapping from index points to `θ`, `k` and
   `λ_max`, `p*` per round kind. Proposed: set by hand from a worked example, then learned.
2. Whether a subscription's forecast is good enough for `λ` early in a window, where there is little
   history (2mw2lt's doc 117 floors the pace for the same reason).
3. Doc 117 excludes an account only on the vendor's own stop signal and caps scoring at a week.
   Here a stopped pool simply has no capacity, and every window's `λ` counts; the cheapest serving
   pool wins. Whether any of doc 117's reasoning is lost needs checking against its cases.
4. Where the posterior lives (unlimited's cache directory, per machine) and whether machines share
   it.
5. The judge's cost: what fraction of reviews to sample, and whether a cheap judge is reliable
   enough for rubric checks.
