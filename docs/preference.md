# A caller's preference (#110)

A caller sometimes wants to lean a choice without ruling anything out: favour some candidates, or
disfavour others, for reasons of its own that unlimited never learns. `--exclude` is the hard form
(a route is not a candidate); this is the soft one (a route still competes, at a handicap or an
advantage). Example: a caller that wants variety across a series of uses disfavours the providers
it has already used; when every other candidate is out or much worse, it still gets one of them.

## Shape

`unlimited choose ... --prefer NAME=MINUTES,...`, and `prefer={name: minutes}` on `choice.rank`
and `choice.choose`.

- `MINUTES` is signed and finite: positive favours, negative disfavours. It is subtracted from the
  candidate's expected cost `E`, so `--prefer codex=-5` makes Codex's routes cost five minutes
  more, exactly as if each took five minutes longer.
- `NAME` is what `--candidates` takes: a provider (its routes), a model (its routes) or an offering
  id (that route). A route matched by several names takes the most specific one's value (offering
  id, then model, then provider); values are not added, so naming a provider and then one of its
  routes sets that route apart from its siblings.
- A name that matches no candidate is recorded and otherwise ignored, as `--exclude` treats one.
- The catalog's `tie_preference` stays as it is, the maintainers' default of up to a minute; a
  caller's preference is added to it.
- Recorded: the request carries `prefer` as given; each scored candidate carries the `prefer`
  minutes applied to it, so the log shows why an order came out as it did. unlimited never reads
  why the caller leans.

The term in minutes is the whole mechanism: `E` is already in minutes, `--temperature` is in
minutes, and a caller that knows what an extra minute of waiting is worth to it can say how much a
lean is worth in the same unit. At temperature 0 a preference of `m` minutes overturns any gap
smaller than `m`; above it, each minute of preference multiplies a candidate's odds at each draw
by `e^(1/temperature)`.

## Open questions

1. **The name.** `--prefer` (positive favours, reads with `tie_preference`), `--bias` (neutral,
   sign convention must be learned), or a pair `--favour`/`--avoid` taking unsigned minutes
   (no sign to remember, two flags). Leaning: `--prefer`, one flag, signed.
2. **Most specific wins vs sum.** Most specific is proposed above: a caller that says
   `deepseek=2,commandcode/deepseek/deepseek-v4.1-flash=-3` means the Command Code route at -3,
   not -1. Sum is simpler to explain but surprising in exactly that case.
3. **Vendors as names.** A caller may want to lean by whose account a use spends
   (`opencode=+2`). Not proposed now: `--quota` already prices accounts, and adding vendors widens
   the name space `--candidates` and `--exclude` share. Worth it?
