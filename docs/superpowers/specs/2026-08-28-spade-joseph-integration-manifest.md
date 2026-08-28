# SPADE Joseph Integration Manifest

**Status:** living integration ledger  
**Joseph reference:** `joseph/kr-effective-resolution-2026-08-28` → `10970c3bb64f0dc842387fdd680febba37a4d69c`  
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

## Pending promotion (research → registered)

| Item | Blocker |
|------|---------|
| `certificate_targeted` as 12th policy arm | New digest + hill+levy gate after B2/B3 |
| SUR acquisition in registered policy | Prereg + digest |
| Bagged certificate default | B3 spike + calibration |
| LB round sweep R≥3 | Preregistered LB study; may change round budget claim |

## Do not port (measured FAIL or wrong layer)

- `k_eff` / `resolution.py` as product filter (KR FAIL)
- `selectionblind.py` (KW FAIL)
- Wholesale merge of `kr-effective-resolution` (deletes manufacturing runners)
- Top-k as default region certificate (KZ: dead at realistic noise)

## Safeguards

- `scripts/run_spade_safeguard_tests.sh` — must pass before REGISTERED workers start
- `tests/test_spade_development.py::test_development_runner_reliability_matches_frozen_protocol_and_scoring`
- `~/spade-ops/spade_gate_then_full_watchdog.sh` — durable gate supervisor
