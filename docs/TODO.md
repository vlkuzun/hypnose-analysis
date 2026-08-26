# TODO — hypnose-behavior

Work that is known, scoped and deliberately not scheduled. Each entry carries the
measurement that makes it actionable, so picking one up does not mean re-deriving it.

Settled rules live in `DECISIONS.md`; closed plans live in `archive/`. Addresses below
were re-measured on `8e5ee27`.

---

## The standing caveat

> **The server has not been re-analysed.** Every saved session on the derivatives tree
> predates the v2.0.0 restructure. The nine coverage sessions in
> `src/hypnose_behavior/qc/sessions.yml` are the only ones current with this code, and the
> gates re-derive those from rawdata rather than reading what is saved.

This outlives any one plan.

---

## ~~`sleap-hypnose` still resolves the flat layout~~ — done 2026-08-26

`sleap_utils.py` spelled `session_dir / "saved_analysis_results"` in five places and
searched it non-recursively, so a migrated session's `movement_analysis/` files were
invisible to it. That file no longer exists: `sleap-hypnose` is now `hypnose-sleap`, a
package whose `io/layout.py` resolves both layouts with `rglob` — the same fix this repo
applied to `io/parquet_peek._parquet_files`.

The ordering constraint is lifted: SLEAP steps and migration can run in either order.
`hypnose-sleap`'s `qc/check_layout.py` asserts the two repos still agree on
`MOVEMENT_SUBFOLDER`, `RESULTS_DIRNAME` and `SUBJECT_PATTERN`, and calls this repo's
`find_tracking_file` against a file written at their `write_path`, so the agreement is
checked rather than assumed.

---

## Select hidden-rule sessions automatically

`summary.json` already carries `params.hidden_rule_odors` / `_positions` for every saved
session, pre-restructure ones included, so this needs no manifest flag and no
re-analysis — measured, it separated all nine fixture sessions correctly and found 29 of
sub-040's 48. Promote the `_session_hr_odors` closure in
`visualization/sampling.py:764` to `io/loaders.py` beside `iter_sessions`: it is a loader
concern, and five of the callers sit outside `visualization/`, so `prep.py` cannot hold
it (section 36). That also retires the copies in `visualization/hidden_rule.py` and
`movement/traces.py`, which each re-read `summary.json` for the same lookup. Then give
the `hidden_rule.py` plotters a `plot_hr_dates` flag that fills `dates` from it when no
dates are passed, so a hidden-rule figure stops needing the dates looked up by hand.
`plot_regression`-gated, since it reaches those 44 cases.

---

## The single-reward metrics are outside the registry

`metric_analysis/run.py:395-431` hardcodes the whole family, against 70 `@metric` /
`@session_metric` registrations elsewhere. It is why `run_all_metrics` cannot simply *be* a
loop over `REPORT` — item 9 collapsed the registry dispatch to one call
(`DECISIONS.md` section 37) and this block is what remains beside it, inside the same
buffer. Registering them is a real item, not a cleanup; noted, not scheduled.

---

## `debug/`

`debug/debug.py`, 512 lines, no `__init__.py`, imported by nothing, 395 of its lines
tab-indented against a space-indented repo, absent from the README structure map, and
recorded at `DECISIONS.md:1680` as deliberately unguarded. The user's call, later.

---

## A test suite for the pure leaves

Every gate but `check_qlearning.py` needs the server mount. `frames.py` (533 lines),
`trial_classification/outcome.py` (84), `parameters.py` (51) and `io/protocol_schema.py`
(350) need no mount, and `hypnose-helpers` already has a pytest layer
(`tests/test_layout.py`, `tests/test_provenance.py`) to mirror. `outcome.py` in particular
is the one rule three call sites depend on (`DECISIONS.md` section 14). `qc/check_layering.py`
is the first gate here that runs with no mount; a `tests/` directory is the natural next
step.
