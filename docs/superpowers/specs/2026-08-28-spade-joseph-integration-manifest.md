# SPADE Joseph Integration Manifest

**Status:** living integration ledger  
**Joseph reference:** `origin/kr-effective-resolution` → `07ae40e` (was `10970c3` at prior port)  
**Remote:** `origin/kr-effective-resolution`  
**Manufacturing trunk:** `main` (REGISTERED gate pipeline)

Joseph's branch remains the **read-only research reference**. This manifest tracks what is
ported into manufacturing `main` without rewriting his history.

## Ported into `main`

| Component | Path | Source commit / branch |
|-----------|------|----------------------|
| Mean marginalisation | `src/boec/meanmarg.py` | merged earlier |
| LOO self-calibration | `src/boec/selfcalib.py` | merged earlier |
| Cert contour straddle | `src/boec/certstraddle.py` | merged earlier |
| Top-k / bagged (research) | `src/boec/topk.py`, `bagged.py` | merged earlier |
| Certified-volume SUR | `src/boec/sur.py` | `458ff42` |
| Certificate-targeted policy | `src/boec/spade.py` | `9c51799` (local branch) |
| Hyperparameter mixture | `src/boec/hypermix.py` | `origin/kr-effective-resolution` |
| Multi-round schedules | `src/boec/multiround.py` | `origin/kr-effective-resolution` |
| LA/LB runners + probes | `scripts/run_la_round_matched.py`, `run_lb_round_sweep.py`, `probe_*.py` | Joseph branch |
| Certificate bench harness | `bench_certificate.py` | `9c51799` |
| Real-data LOO calibration | `scripts/calibrate_real_assay_loo.py` | Joseph branch |
| Hall/Ogle certification | `scripts/certify_hall_ogle.py` | Joseph branch |
| Combined real-data answer | `scripts/final_real_data_answer.py` | Joseph branch |
| Real assay LOO probe | `scripts/probe_loo_real_assay.py` | Joseph branch |
| LC confirmatory (hill) | `scripts/run_lc_confirmatory.py` | Joseph branch |
| B3 offline replay | `scripts/replay_certificate_scoring.py` | manufacturing |
| LA round-matched results | `results/la-*.json` | `origin/kr-effective-resolution` @ `07ae40e` |
| LB round-sweep results | `results/lb-*.json` | `origin/kr-effective-resolution` @ `07ae40e` |
| Round sweep spec + headline | `docs/SPADE-ROUND-SWEEP-SPEC.md` | `2cad89f` / `aafa65c` |
| SUR vs straddle probe | `results/probe-sur-vs-straddle.json` | `2cad89f` |
| Joseph handoff (adapted) | `docs/HANDOFF-2026-08-29.md` | `07ae40e` (paths adapted) |
| LC confirmatory runner | `scripts/run_lc_confirmatory.py` | `3bab48f` (already on main) |

## Joseph commits integrated 2026-08-29 (since `10970c3`)

| Commit | Content |
|--------|---------|
| `2cad89f` | LB-1 PASS — `results/lb-*.json`, `probe-sur-vs-straddle.json`, round-sweep spec §LB |
| `aafa65c` | Headline: SPADE R=5 parity with qLogNEI R=10 — spec §headline |
| `3bab48f` | `run_lc_confirmatory.py` (already ported) |
| `07ae40e` | Joseph handoff doc (adapted for manufacturing worktree) |

**Not ported:** Joseph `.gitignore` rewrite (drops manufacturing evidence allowlists). LC
`results/lc-*.json` not yet on his branch — run locally when compute free.

## Promoted to registered (B3 digest `2ef1875c…`)

| Item | Setting |
|------|---------|
| `certificate_bootstrap_bags` | **5** (intersect bootstrap refits) |
| `certificate_targeted` policy | **o32 only** (10th SPADE arm) |
| `reliability.alpha` | **0.95** (reverted from failed B2) |

## Pending promotion (research → registered)

| Item | Blocker |
|------|---------|
| `certificate_targeted` as 12th policy arm | New digest + hill+levy gate after B2/B3 |
| SUR acquisition in registered policy | Prereg + digest; probe shows no improvement vs straddle |
| Bagged certificate default | B3 spike running on manufacturing gate |
| LB round sweep R≥3 | **PASS** (`2cad89f`); results on main — separate from scalar gate |
| LC confirmatory (hill + 25 seeds) | Runner on main; **results pending** |

## Do not port (measured FAIL or wrong layer)

- `k_eff` / `resolution.py` as product filter (KR FAIL)
- `selectionblind.py` (KW FAIL)
- Wholesale merge of `kr-effective-resolution` (deletes manufacturing runners)
- Top-k as default region certificate (KZ: dead at realistic noise)

## Safeguards

- `scripts/run_spade_safeguard_tests.sh` — must pass before REGISTERED workers start
- `tests/test_spade_development.py::test_development_runner_reliability_matches_frozen_protocol_and_scoring`
- `~/spade-ops/spade_gate_then_full_watchdog.sh` — durable gate supervisor
