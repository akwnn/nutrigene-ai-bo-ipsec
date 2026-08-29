# SPADE Scalar Recovery — Diagnosis Ledger

**Purpose:** Durable record of what was tried, what failed, what helped, and where
artifacts live. Update when any gate completes (PASS or FAIL).

**Gate criterion (unchanged):** hill+levy keys 0–15; per arm ans≥0.5 **and** emp≥0.9 on
**both** families; ≥1 SPADE survivor required to advance to full 5×50.

---

## 1. Executive summary

| Verdict | Detail |
|---------|--------|
| **Binding failure mode** | Complementary near-misses — no single 9-arm config passes hill **and** levy together |
| **Levy is harder** | Best levy emp ~0.90 (`o32-validity_gated`); hill often 1.0 on different arms |
| **Model-internal containment lies** | Failed runs still show selection containment ~0.97–0.99; truth emp False |
| **B3 in flight** | Digest `2ef1875c…` — bagged5 + cert_targeted o32 + α=0.95 + 12 arms/family |
| **Parallel win** | Multi-CQA benchmark PASS (`b29bb57e…`) — separate EC claim |

---

## 2. Experiment chronology

| Phase | Digest (prefix) | Change | Outcome | Archive / analysis |
|-------|-----------------|--------|---------|-------------------|
| floor15+meanmarg | `1c5c3b7e` | Joseph meanmarg wired | **FAIL** 0 survivors | `results/historical-mfg-cert-floor15-loo-tail-meanmarg-gate-fail/` → [JSON](artifacts/gate-summaries/historical-mfg-cert-floor15-loo-tail-meanmarg-gate-fail.json) |
| floor20 (B1) | `b846fe2d` | inflation floor 1.5→2.0 | **FAIL** — hurt levy | `results/historical-mfg-cert-floor20-loo-tail-meanmarg-gate-fail/` → [JSON](artifacts/gate-summaries/historical-mfg-cert-floor20-loo-tail-meanmarg-gate-fail.json) |
| alpha0.98 (B2) | `7ba21e73` | reliability α 0.95→0.98 | **FAIL** — levy ans collapsed | `results/historical-mfg-cert-floor15-loo-tail-meanmarg-alpha098-gate-fail/` → [JSON](artifacts/gate-summaries/historical-mfg-cert-floor15-loo-tail-meanmarg-alpha098-gate-fail.json) |
| **B4 Joseph-aligned (B3 fix)** | `967eb654` | ρ=0.95 + schedule (32,8,8) + per-round menu | **RUNNING** | live shards |
| bagged5+cert_targeted (B3) | `2ef1875c` | ρ=0.5 + four×4 batches (wrong defaults) | **SUPERSEDED** | do not resume |

**Commits (implementation):** `ddddfb8` (B3 protocol), `cc43b09` (manifest hash fix).

---

## 3. Wrong vs right

### What did **not** work (measured)

| Idea | Verdict | Evidence |
|------|---------|----------|
| Raise inflation floor to 2.0 | **Reject** | floor20 gate FAIL; levy emp/ans worse vs meanmarg baseline |
| Raise α to 0.98 | **Reject** | o32-staged levy ans **0.07**; still 0 survivors |
| `map_iou` abstention filter | **Reject** | No separation OK vs FAIL; pooled levy emp drops (§10.2 decisions) |
| Higher selection_containment threshold | **Reject** | FAIL runs have *higher* sel containment |
| `k_eff`, selection-blind, SNR detectors | **Banned** | Registered FAIL per KR/KW |
| Single-arm hill-only or levy-only claim | **Invalid** | Gate requires **both** families on **one** arm |

### What **helped** (partial — not sufficient alone)

| Idea | Effect | Still insufficient because |
|------|--------|---------------------------|
| Mean marginalisation (Joseph) | Levy emp 0.75→0.875 on o32-staged | Hill/levy still split across arms |
| LOO-tail inflation + floor 1.5 | Near-miss (1 leak/family on best arms) | Complementary pairing persists |
| smallest volume rule + Vmax | Honest abstention on tiny regions | Answer rate binds some arms |
| o32 opening | Best mean emp hill/levy vs o40/o44 | Still no co-pass |
| validity_gated policy | Best levy emp (0.90) | Hill emp 0.875 on same arm |

### B4 hypothesis (Joseph-aligned acquisition)

| Lever | Mechanism | Source |
|-------|-----------|--------|
| **certificate_rho=0.95** | High-exceedance contour, not median 0.5 | Joseph LA `spade_cert_rho95` |
| **Schedule (32,8,8)** | LB R=3 matched-round winner | `multiround` / LB-1 PASS |
| **Per-round candidate menu** | Fresh Sobol menu each adaptive batch | `multiround.py` |

B3 used ρ=0.5 (Bryan's median straddle) — Joseph measured that as wrong layer.

---

## 4. Best arms per failed gate (keys 0–15)

### Meanmarg baseline (`1c5c3b7e`)

| Arm | hill ans / emp | levy ans / emp |
|-----|----------------|----------------|
| o32-staged | 0.53 / **1.00** | 0.13 / 0.50 |
| o32-validity_gated | 0.67 / 0.90 | 0.53 / **0.875** |

### B2 alpha0.98 (`7ba21e73`)

| Arm | hill ans / emp | levy ans / emp |
|-----|----------------|----------------|
| o32-staged | 0.47 / **1.00** | **0.07** / 1.00 |
| o32-validity_gated | 0.33 / **1.00** | 0.47 / 0.86 |
| o40-staged | 0.60 / **1.00** | **0.07** / 1.00 |

Full per-arm tables: `.planning/artifacts/gate-summaries/*.json`.

---

## 5. Tooling for future diagnosis

| Tool | Use |
|------|-----|
| `scripts/analyze_gate_failures.py` | Summarize archived hill+levy shards → survivors + abstention breakdown |
| `scripts/replay_certificate_scoring.py` | Re-run campaigns from seeds; score with alternate `certificate_bootstrap_bags` (TEST_ONLY) |
| `scripts/run_spade_safeguard_tests.sh` | Pre-REGISTERED validation (193 tests) |
| `~/spade-ops/spade_gate_then_full_watchdog.sh` | Durable gate→full supervisor |
| `/tmp/spade-durable.status` | Live phase, row counts, commit |
| `/tmp/spade-gate-tail-verdict.json` | Post-gate survivor list |

**Replay example (offline, does not mutate archived digests):**
```bash
./scripts/replay_certificate_scoring.py \
  results/historical-mfg-cert-floor15-loo-tail-meanmarg-gate-fail/spade-development-hill-000-015.jsonl.gz.resume.json \
  results/historical-mfg-cert-floor15-loo-tail-meanmarg-gate-fail/spade-development-levy-000-015.jsonl.gz.resume.json \
  --bootstrap-bags 5 --alpha 0.95
```

---

## 6. Ops incidents (for replay)

| Date | Issue | Fix |
|------|-------|-----|
| 2026-08-29 | B2 worker crash loop | `eb60339` — runner alpha must match yaml |
| 2026-08-29 | Levy blocked after hill complete | `ddd0468` — allow `.planning/STATE.md` edits during gate |
| 2026-08-29 | Watchdog REFUSE dirty | Uncommitted `.planning/` blocked gate; runner now ignores all `.planning/` edits |
| 2026-08-29 | Safeguard ~60s per worker spawn | By design; expect slow gate ramp |

---

## 7. Joseph integration status

**Complete on `main`** (manifest: `docs/superpowers/specs/2026-08-28-spade-joseph-integration-manifest.md`):

- Core: meanmarg, selfcalib, certstraddle, sur, hypermix, multiround, bagged, topk
- Real-data: `calibrate_real_assay_loo`, `certify_hall_ogle`, `final_real_data_answer`, `probe_loo_real_assay`, `run_lc_confirmatory`
- B3 registered: `certificate_targeted` policy on o32 only

**Do not wholesale-merge** `origin/kr-effective-resolution` (deletes manufacturing runners).

---

## 8. Update protocol

When a gate completes:

1. If FAIL: `mv results/spade-development-{hill,levy}-000-015.* results/historical-mfg-cert-<suffix>/`
2. Run `analyze_gate_failures.py` → save JSON under `.planning/artifacts/gate-summaries/`
3. Update §2 table and STATE.md
4. Amend `docs/superpowers/specs/2026-08-27-spade-certificate-improvement-decisions.md` §7
