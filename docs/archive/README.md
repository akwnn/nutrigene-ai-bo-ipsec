# ARCHIVE — real work the paper does not ask for

**Nothing here is deleted, and nothing here is wrong.** Every item was archived because it
answers a question the paper does not ask, not because it failed. Several are better work
than things that stayed in the main line.

The main line is `docs/MAIN-LINE.md`. The label for every item in the project — including
these — is `docs/TRIAGE.md`.

**Rule:** an archived item keeps its record. If a result later turns out to matter, it must
be recoverable, and a file that was deleted is not. This project has already lost a run to
an untracked file (D12) and nearly overwrote a correct cell on a bad inference (D11), so
the bar here is preservation, not tidiness.

---

## `build-phase/` — the scaffolding that produced the code

Written 2026-08-07, day 1 of 14. These are build orders, work packages, gates and ownership
boundaries for a two-person parallel build. They are how the software got written; they are
not evidence, and no claim rests on them.

| file | what it is |
|---|---|
| `project_plan.md` | Document 2 of 3 — project context, the scientific argument, Phase 2/3 plans, design rationale. ⚠️ **Part E (§E.1–E.5) is NOT archived material — it is the live Phase 3 specification**, and Phase 3 began on 2026-08-13 with the in-house lab drop. Cited by `docs/LAB-DATA-FOR-BO.md` §9. Archived for the other nine tenths of the file; read Part E as current. |
| `phase1_build.md` | Document 1 of 3 — the buildable specification for the synthetic phase. The technical authority during the build. |
| `team_build_plan.md` | Shared gates, interfaces, ownership boundaries, rules for working in parallel. |
| `person_a_spec.md` | Person A's work package — data lane, E2 (efficiency), E3 (calibration). |
| `person_b_spec.md` | Person B's work package — loop lane, E4 (extrapolation detection). |
| `build-scope-person-b.md` | Day-1 build order and the exclusions list. Self-marked superseded for live status on 2026-08-07. |
| `what-each-file-does.md` | Plain-language tour of the modules, for a non-programmer. |
| `TASKS.md` | Task ordering and owners. Explicitly subordinate to `OPEN-QUESTIONS.md`, which wins on any disagreement. |
| `preflight-findings.md` | **PF3 and PF4 findings.** The one file in this folder that carries results — and they are recorded *nowhere else*. `RESULTS.md` PART 1 covers PF1, PF2 and PF-A/PF-B only. Reproduce with `scripts/preflight_pf3.py`, `scripts/preflight_pf4.py`. |

## `plain-english/` — the code explained without jargon

Ten short chapters written for a reader who does not program: the measuring tape, the curve
fitter, the test plan, the model builder, the proposal engine, the campaign loop, the rival
model, the comparison, the batch runner. Useful for onboarding and for checking that a
module does what its author thought. Not evidence.

## `exploratory/` — the unregistered mechanism search

**Nothing in this folder is a result, and its own front page says so in those words:**
*"No number produced here may enter `docs/RESULTS-PERSON-A.md`, `docs/METHODS.md`, or any
paper text without being re-run clean, on fresh instances, under a registration written
before that run."*

It asks what the second-order polynomial has that the GP does not — quadratic mean function,
replicated centre points, input warping — at the E2 primary cell. The question is mechanism,
not rescue. It is archived rather than promoted because an unregistered search over eight
model configurations, scored on the outcome, is the most favourable environment for exactly
the class of defect this project keeps logging.

Archived here **because it was untracked**, which is the one state from which work actually
disappears. Contents: `EXPLORATORY.md`, four `exploratory_*.py` scripts, the `exploratory.py`
module, its test file, and `results/` holding the four run logs.

- `tests/test_exploratory.py` moved here with the rest. It had two failures against `main`;
  keeping it out of `tests/` is what lets the committed suite stay green at 652 passing
  without deleting the work.
- The matching `results/exploratory-*.json*` raw rows are **still in `results/` and still
  gitignored** — regenerable from the archived scripts, so they were left as data rather
  than committed.
- This also settles the open instruction at `RESULTS.md` PART 3: *"`results/exploratory-kg.log`
  is untracked… either commit the log or drop the claim."* The log is now committed here, and
  the qKG swap stays **not citable** — archived, not promoted.

---

## Archived in place — labelled ARCHIVE, but NOT moved

Two large workstreams are labelled ARCHIVE in `TRIAGE.md` and deliberately left where they are.
**Moving them would break something**, and a broken anchor loses work more effectively than a
messy directory does.

| Workstream | Why it is ARCHIVE | Why it did not move |
|---|---|---|
| **E4** — extrapolation detection (`E4-RESULTS-v2.md`, `E4-FIRST-RESULTS.md`, `e4-*.log`, the three `figures/e4-*.png`) | Asks whether a GP's uncertainty beats plain nearest-neighbour distance at *flagging* extrapolation. No sentence of the paper's result depends on it, and its own headline is unresolved (Q19). | `results/` is raw data by the rule above; `docs/RESULTS.md` and `docs/CLAIMS.md` anchor to `E4-RESULTS-v2.md` **by path**; and `tests/test_surrogate.py` reads `NEGATIVE-shape-aware-mean.md`. |
| **Q47** — the multi-fidelity threshold (22 shards + merged, ~11 MB) | Answers *"when does a cheap second assay pay?"* — forward-looking design advice. Its own entry concedes the correlation is **assumed, not measured**, "which is why this is a threshold and not a result." | Raw data. `RESULTS.md` PART 9 anchors to it by path. |

⚠️ **Two E4 files have no producing script anywhere in the repo** — `E4-RESULTS-v2.md` and
`NEGATIVE-shape-aware-mean.md` are hand-authored narratives, and `run_e4.py` declares only
`E4-FIRST-RESULTS.md`. They **cannot be regenerated**. That is exactly why they are not touched.

---

## What is NOT in here, and why

- **Raw result files.** Everything in `results/` stays in `results/`. The rule is *archive the
  analysis, keep the data*.
- **The defect register** (`RESULTS.md` PART 8, `RESULTS-PERSON-A.md` §7). Twenty defects
  caught before publication is a methods contribution.
- **Wrong registered predictions** (`RESULTS.md` PART 10). They are what makes the correct
  ones credible.
- **Superseded numbers that are marked as superseded.** The marking is the record.
- **`docs/pdf_crosscheck_raw/`.** Four-reader raw readings of the source PDF — the evidence
  behind a DEFENCE item, not commentary on it.
