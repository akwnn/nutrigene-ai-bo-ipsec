"""The release gate for `spade-final-2026-08-23` — spec §9, enforced mechanically.

    .venv/bin/python scripts/validate_final_spade_release.py
    .venv/bin/python scripts/validate_final_spade_release.py --pre-release

Exits non-zero and prints **every** violation, not the first one.

------------------------------------------------------------------------------
WHY A PROGRAM AND NOT A CHECKLIST
------------------------------------------------------------------------------

Every guard below exists because this project already made the mistake it stops,
and made it in writing, in a committed document, and did not notice for days.
`docs/SPADE-FINAL-SPEC.md` §9 lists seven of them; §13.6 and §10.1 add two more.
A checklist catches the mistakes its reader is already looking for, which is
never the one that ships. So each guard is a named function with two tests: one
proving it fires on a synthetic violation, one proving it stays quiet on clean
input (`tests/test_final_spade_reproducibility.py`).

The nine checks, and the failure each is a memorial to:

  claim_language        §9.1  — a word like "improved" attached to a decision the
                                kill ledger did not record as PASS. FINDINGS
                                §43.1: K-C1's headline was withdrawn because the
                                comparison behind the word was not the one made.
  table_completeness    §9.2  — FINDINGS §9.5: a containment table was published
                                without its denominators and one claim in it did
                                not survive being un-pooled.
  same_draw_primacy     §9.3  — FINDINGS §29.3: same-draw and cross-fit
                                containment differ by up to 3.5 points, and the
                                flattering one is the same-draw one.
  normal_approximation  §9.4  — FINDINGS §22: §14's Holm correction was computed
                                on a continuity-corrected normal tail and did not
                                survive the exact one. Nothing about the
                                measurements was wrong; the inference was.
  suppressed_failure    §9.5  — FINDINGS §41: SPADE certified nothing in 1,200
                                campaigns on ackley. That is a result. §11 lists
                                hiding it among the prohibited actions.
  universal_claim       §9.6  — spec §1: the claim this study may never support
                                is that SPADE beats Sobol, BO or DoE everywhere.
  alpha_star_misuse     §9.7  — FINDINGS §28/§31: alpha_star is a functional of
                                the fitted posterior. It measures willingness to
                                certify, and it ranks the *worst*-calibrated arm
                                first. No claim may rest on it.
  mandatory_comparator  §4/§13.6 — §4.2b, the Q57 trap: a headline that holds
                                against qLogEI and dies against the noisy
                                acquisition. A missing comparator is a hard
                                failure, not an absence.
  manifest_regeneration §10.1(7) — FINDINGS T1.4: two clones held two different
                                E2 grids under one filename and both fidelity
                                gates passed, because each compared a clone
                                against itself.

------------------------------------------------------------------------------
THE RULE FOR TELLING A CLAIM FROM A NEGATED CLAIM
------------------------------------------------------------------------------

This is the only judgement call in the file, so it is written down rather than
buried in a regex. An occurrence of a guarded word is **exempt** — it is a
mention, a quotation or a denial rather than an assertion — when any of:

  1. it is inside a fenced code block, or an inline `code span`. A column called
     ``murphy_calibration`` is a name, not an assertion that anything is
     calibrated;
  2. it is on a line beginning with ``>``. Blockquotes are how this project
     writes withdrawals (FINDINGS §29.4) and quotes the claim boundary (spec §1);
  3. it is inside a quoted span of **four words or fewer**. Quoting the guard
     list itself, as §9 does, is a mention. A longer quoted span is prose and
     stays subject to the check — quotation marks are not a laundry;
  4. it is part of a registered compound term: ``oracle-best`` / ``oracle_best``
     is the name of a ceiling in ROW_SCHEMA, not a superlative;
  5. it carries a negating prefix — ``non-significant``, ``un-improved``;
  6. a negator (not / no / never / cannot / without / fails / …) appears within
     eight tokens *before* it **and inside the same clause**. Clause boundaries
     are ``. , ; : — – ( ) ! ? |`` and newline.

Rule 6's clause restriction is the one that matters, and it is why a token
window alone is not enough. In

    SPADE did not win on regret, and m0 outperforms random_plate2.

the negation belongs to the first clause. A window of eight tokens would reach
back across the comma and license the second clause's claim — which is precisely
how a paragraph that reads as balanced ships an unsupported headline. The comma
stops it, so ``outperforms`` is flagged.

An occurrence that survives all six is an **assertion**, and an assertion is
permitted only when its sentence cites a kill-ledger id (``KF-n``) whose
registered status is ``PASS``. Anything else — a non-PASS id, or no id at all —
is a violation. ``INCONCLUSIVE`` does not license a claim: §7.1 says in as many
words that non-significance is not proof of validity.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FINDINGS_REL = "docs/FINDINGS-SPADE-FINAL.md"
ANALYSIS_REL = "scripts/analyse_final_spade_benchmark.py"
ARTEFACT_REL = {
    "ledger": "results/final-spade-kill-ledger.json",
    "feasibility": "results/final-spade-feasibility.json",
    "benchmark": "results/final-spade-primary.json",
    "certificates": "results/final-spade-certificate.json",
    "manifest": "results/final-spade-manifest.json",
}

#: Spec §4. `doe_unscreened` is mandatory *or* carries a structured
#: `unavailable_reason` -- §4 forbids approximating it into existence at d=8, and
#: forbids its silent disappearance just as firmly.
MANDATORY_ARMS = ("spade_cf_m0", "spade_cf_m4", "spade_cf_m8", "spade_plate1_only",
                  "spade_random_plate2", "sobol", "lhs", "random", "qlognei",
                  "qlogei", "doe", "doe_unscreened")


@dataclass(frozen=True)
class Violation:
    check: str
    section: str
    location: str
    detail: str

    def __str__(self) -> str:
        return f"  [{self.check}] {self.section}  {self.location}\n      {self.detail}"


@dataclass(frozen=True)
class Check:
    name: str
    section: str
    why: str
    run: Callable[["Release"], list[Violation]]


@dataclass
class Release:
    root: Path
    findings: str | None = None
    analysis: str | None = None
    ledger: dict | None = None
    feasibility: dict | None = None
    benchmark: dict | None = None
    certificates: dict | None = None
    manifest: dict | None = None
    missing: list[str] = field(default_factory=list)


# ==========================================================================
# Prose scanning primitives
# ==========================================================================

GUARDED = (
    # The seven registered in §9.1, plus the tense/number variants of each that
    # mean the identical thing. `certificate` is deliberately NOT here: it is the
    # object under study, and `\bcertified\b` does not match inside it.
    "best", "winner", "winners", "certified", "calibrated", "significant",
    "significantly", "improved", "outperform", "outperforms", "outperformed",
)
GUARDED_RE = re.compile(r"\b(" + "|".join(GUARDED) + r")\b", re.IGNORECASE)

#: Rule 4 -- registered compound terms, masked before anything else looks at the
#: text. `oracle_best_regret` is a ROW_SCHEMA column and `oracle-best` is what
#: FINDINGS §34/§39 call the ceiling; neither is a superlative about an arm.
DEFINED_TERMS_RE = re.compile(r"oracle[-_]best", re.IGNORECASE)

NEGATORS = {"not", "no", "never", "nor", "neither", "cannot", "cant", "without",
            "fails", "failed", "fail", "refuses", "refused", "declines",
            "declined", "lacks", "lacking", "absent", "unable", "withdrawn",
            "denies", "denied", "rejects", "rejected", "nothing", "none"}
NEGATING_PREFIX_RE = re.compile(r"(non-?|un-?|not-)$", re.IGNORECASE)
CLAUSE_BOUNDARY = set(".,;:!?()|\n\u2014\u2013")
NEGATION_WINDOW = 8

KF_RE = re.compile(r"\bKF-(\d+)\b")


def _mask(text: str) -> str:
    """The text with every exempt region replaced by spaces, offsets preserved.

    Exempt regions are rules 1-4 of the module docstring. Spaces rather than
    deletion so a match offset still maps to the right line of the real file.
    """
    out = list(text)

    def blank(a: int, b: int) -> None:
        for i in range(a, min(b, len(out))):
            if out[i] != "\n":
                out[i] = " "

    for m in re.finditer(r"```.*?```", text, re.DOTALL):      # rule 1, fenced
        blank(*m.span())
    for m in re.finditer(r"`[^`\n]*`", text):                  # rule 1, inline
        blank(*m.span())
    for m in re.finditer(r"^[ \t]*>.*$", text, re.MULTILINE):  # rule 2, blockquote
        blank(*m.span())
    for m in re.finditer(r"[\"\u201c][^\"\u201c\u201d\n]*[\"\u201d]", text):
        if len(m.group(0).strip("\"\u201c\u201d").split()) <= 4:   # rule 3, mention
            blank(*m.span())
    for m in DEFINED_TERMS_RE.finditer(text):                  # rule 4
        blank(*m.span())
    return "".join(out)


def _sentences(text: str) -> list[tuple[int, int]]:
    """Sentence spans. Boundaries are terminal punctuation, blank lines, and the
    start of a table row -- markdown wraps sentences across lines, so a newline
    alone is not one."""
    spans, start = [], 0
    for m in re.finditer(r"(?<=[.!?])\s+|\n\s*\n|\n(?=\s*\|)", text):
        spans.append((start, m.start()))
        start = m.end()
    spans.append((start, len(text)))
    return [(a, b) for a, b in spans if b > a]


def _sentence_at(spans: list[tuple[int, int]], i: int) -> tuple[int, int]:
    for a, b in spans:
        if a <= i < b:
            return a, b
    return (i, i)


def _is_negated(masked: str, i: int) -> bool:
    """Rules 5 and 6 -- a negating prefix, or a negator inside the same clause."""
    if NEGATING_PREFIX_RE.search(masked[max(0, i - 4):i]):
        return True
    j = i - 1
    while j >= 0 and masked[j] not in CLAUSE_BOUNDARY:
        j -= 1
    clause = masked[j + 1:i]
    tokens = re.findall(r"[A-Za-z']+", clause)
    return any(t.lower().strip("'") in NEGATORS for t in tokens[-NEGATION_WINDOW:])


def _line_of(text: str, i: int) -> int:
    return text.count("\n", 0, i) + 1


# ==========================================================================
# §9.1 -- claim language against the kill ledger
# ==========================================================================

def ledger_status(ledger: dict | None) -> dict[str, str]:
    """`{"KF-3": "FAIL", ...}` from whichever shape the ledger was written in."""
    if not ledger:
        return {}
    entries = ledger.get("entries") or ledger.get("rows")
    if entries is None:
        entries = [v for v in ledger.values() if isinstance(v, dict) and "status" in v]
    out = {}
    for e in entries:
        if isinstance(e, dict) and e.get("id"):
            out[str(e["id"])] = str(e.get("status", "NOT_RUN")).upper()
    return out


def check_claim_language(findings: str | None, ledger: dict | None) -> list[Violation]:
    """A claim word is permitted only beside a kill-ledger id that says PASS.

    The exemption rule is the module docstring's six clauses, in that order.
    """
    if findings is None or ledger is None:
        return []
    status = ledger_status(ledger)
    masked = _mask(findings)
    spans = _sentences(findings)
    out = []
    for m in GUARDED_RE.finditer(masked):
        if _is_negated(masked, m.start()):
            continue
        a, b = _sentence_at(spans, m.start())
        sentence = findings[a:b].strip()
        ids = KF_RE.findall(sentence)
        loc = f"{FINDINGS_REL}:{_line_of(findings, m.start())}"
        if not ids:
            out.append(Violation(
                "claim_language", "§9.1", loc,
                f"{m.group(0)!r} asserted with no kill-ledger id in its sentence — "
                f"an unattributed claim cannot be checked against a registered "
                f"decision: {sentence[:140]!r}"))
            continue
        bad = [f"KF-{i}" for i in ids if status.get(f"KF-{i}", "MISSING") != "PASS"]
        if bad and not any(status.get(f"KF-{i}") == "PASS" for i in ids):
            states = ", ".join(f"{k}={status.get(k, 'not in ledger')}" for k in bad)
            out.append(Violation(
                "claim_language", "§9.1", loc,
                f"{m.group(0)!r} asserted where the matching kill-ledger entry did "
                f"not PASS ({states}): {sentence[:140]!r}"))
    return out


# ==========================================================================
# §9.2 -- tables carry condition, terminal rule, denominators
# ==========================================================================

#: A curated subset, not all of ROW_SCHEMA: `arm`, `rounds` and `family` appear in
#: the arm-registry table, which is a table of definitions. Demanding a
#: denominator of it would train the reader to ignore the guard.
METRIC_TERMS = ("regret", "containment", "symmetric difference", "symmetric_difference",
                "type i", "type ii", "type_i", "type_ii", "brier", "calibration",
                "refinement", "auc", "iou", "false inclusion", "coverage",
                "identification gap", "prevalence", "empty rate", "empty-region",
                "certificate volume", "error volume", "alpha_star", "holm")
PROPORTION_TERMS = ("containment", "coverage", "rate", "proportion", "prevalence",
                    "empty", "%")
REGRET_TERMS = ("regret", "identification gap")
CONDITION_ID_RE = re.compile(r"\b[CS][1-9]\b")
FRACTION_RE = re.compile(r"\b\d+\s*/\s*\d+\b")


@dataclass
class _Table:
    line: int
    header: list[str]
    body: list[list[str]]
    caption: str
    blob: str


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _tables(text: str) -> list[_Table]:
    lines = text.split("\n")
    tables, i = [], 0
    while i < len(lines) - 1:
        if lines[i].lstrip().startswith("|") and re.match(
                r"^\s*\|[\s:\-|]+\|\s*$", lines[i + 1]):
            header, j = _cells(lines[i]), i + 2
            body = []
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                body.append(_cells(lines[j]))
                j += 1
            above = [ln for ln in lines[max(0, i - 3):i] if ln.strip()
                     and not ln.lstrip().startswith("|")]
            below = [ln for ln in lines[j:j + 2] if ln.strip()
                     and not ln.lstrip().startswith("|")]
            caption = " ".join(above[-2:] + below[:1])
            blob = "\n".join(lines[i:j])
            tables.append(_Table(i + 1, header, body, caption, blob))
            i = j
        else:
            i += 1
    return tables


def check_table_completeness(findings: str | None) -> list[Violation]:
    """Every table that reports a registered metric names its condition; every
    regret table names its terminal rule; every proportion carries a denominator.

    Scoped to *results* tables on purpose. §7.4 makes the terminal rule
    load-bearing only where regret appears, and §11 makes the denominator
    load-bearing only where a rate does.
    """
    if findings is None:
        return []
    out = []
    for t in _tables(findings):
        hay = (t.blob + " " + t.caption).lower()
        if not any(term in hay for term in METRIC_TERMS):
            continue
        loc = f"{FINDINGS_REL}:{t.line}"
        head = " ".join(t.header).lower()

        labelled = ("condition" in head or "cell" in head
                    or bool(CONDITION_ID_RE.search(" ".join(r[0] for r in t.body if r)))
                    or "condition" in t.caption.lower()
                    or bool(CONDITION_ID_RE.search(t.caption)))
        if not labelled:
            out.append(Violation(
                "table_completeness", "§9.2", loc,
                "table reports a registered metric but carries no condition label — "
                "a number with no cell is not attributable to a regime class"))

        if any(term in hay for term in REGRET_TERMS) and not re.search(
                r"\brule[ _][ap]\b|terminal rule|rule a\b|rule p\b", hay):
            out.append(Violation(
                "table_completeness", "§9.2 (§7.4)", loc,
                "regret table does not name its terminal rule — comparing rule A for "
                "one arm against rule P for another is a protocol violation, and an "
                "unnamed rule cannot be checked for it"))

        if any(term in hay for term in PROPORTION_TERMS):
            has_denom = (bool(re.search(r"\bn\b|denominator|non-?empty|x/n", head))
                         or any(FRACTION_RE.search(c) for r in t.body for c in r)
                         or "n=" in t.caption.lower())
            if not has_denom:
                out.append(Violation(
                    "table_completeness", "§9.2 (§11)", loc,
                    "proportion reported without its denominator — §11 lists "
                    "reporting a certificate rate without its non-empty denominator "
                    "among the prohibited actions"))
    return out


# ==========================================================================
# §9.3 -- same-draw containment is never the primary
# ==========================================================================

SAME_DRAW_RE = re.compile(r"same[-_ ]draw", re.IGNORECASE)
CROSSFIT_RE = re.compile(r"cross[-_ ]?fit", re.IGNORECASE)
PRIMACY_RE = re.compile(r"\bprimary\b|\bheadline\b|\bthe containment (?:is|was)\b",
                        re.IGNORECASE)
DIAGNOSTIC_RE = re.compile(r"non-?primary|not primary|never primary|diagnostic|beside",
                           re.IGNORECASE)


def check_same_draw_not_primary(findings: str | None) -> list[Violation]:
    """§29.3 measured same-draw and cross-fit differing by up to 3.5 points, always
    in the same direction. A table that prints only the same-draw column, or a
    sentence that calls it primary, hides exactly that gap."""
    if findings is None:
        return []
    out = []
    for t in _tables(findings):
        if SAME_DRAW_RE.search(t.blob) and not CROSSFIT_RE.search(t.blob + t.caption):
            out.append(Violation(
                "same_draw_primacy", "§9.3 (§2.1)", f"{FINDINGS_REL}:{t.line}",
                "table carries a same-draw containment column and no cross-fit "
                "column — the cross-fit estimate is the primary endpoint and the "
                "gap between them is the diagnostic"))
    for a, b in _sentences(findings):
        s = findings[a:b]
        if SAME_DRAW_RE.search(s) and PRIMACY_RE.search(s) and not DIAGNOSTIC_RE.search(s):
            out.append(Violation(
                "same_draw_primacy", "§9.3 (§2.1)", f"{FINDINGS_REL}:{_line_of(findings, a)}",
                f"same-draw containment presented as primary: {s.strip()[:140]!r}"))
    return out


# ==========================================================================
# §9.4 -- no normal approximation in certificate inference
# ==========================================================================

#: A function is doing certificate inference if its name or docstring says so.
#: Scoping matters: 1.96 is the straddle band's own constant (spec §5.1) and
#: flagging it everywhere would make the guard noise, and noise gets switched off.
CERT_FN_RE = re.compile(
    r"containment|certificate|clopper|interval|coverage|p_?value|tail|holm|assurance|"
    r"binomial|nominal", re.IGNORECASE)
Z_CONSTANTS = {1.96, 1.645, 1.6449, 2.576, 2.5758, 2.326, 2.3263, 1.2816}
EXACT_TAIL_RE = re.compile(r"binom\.(cdf|sf|pmf)|binomtest|binom_test|beta\.ppf|"
                           r"clopper|method\s*=\s*[\"']beta[\"']", re.IGNORECASE)


def _fn_source(src: str, node: ast.AST) -> str:
    return ast.get_source_segment(src, node) or ""


def check_no_normal_approximation(analysis: str | None,
                                  path: str = ANALYSIS_REL) -> list[Violation]:
    """FINDINGS §22 in executable form.

    §14's four containment measurements reproduced exactly; the p-values attached
    to them were a continuity-corrected normal tail, and the leading cell's Holm
    value moved from 0.043 to 0.2296 when the exact tail was used. Binomial(50,
    0.95) has ``np(1-p) = 2.5``, an order of magnitude under the usual rule of
    thumb, and the far-left tail is where the approximation is worst.

    Three things are refused: importing a normal distribution into the analysis at
    all; a z-constant or a non-exact ``proportion_confint`` inside a function whose
    own name or docstring says it is doing certificate inference; and — the
    positive requirement — certificate inference that never touches an exact tail,
    which has computed the tail some other way.
    """
    if analysis is None:
        return []
    try:
        tree = ast.parse(analysis)
    except SyntaxError as exc:
        return [Violation("normal_approximation", "§9.4", f"{path}:{exc.lineno}",
                          f"analysis source does not parse, so it cannot be audited: {exc}")]
    out = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and "scipy" in (node.module or ""):
            for al in node.names:
                if al.name == "norm":
                    out.append(Violation(
                        "normal_approximation", "§9.4 (§8)", f"{path}:{node.lineno}",
                        "scipy.stats.norm imported into the analysis — §8 requires "
                        "containment inference to be exact (scipy.stats.binom tails "
                        "and Clopper-Pearson), and FINDINGS §22 records what the "
                        "normal tail cost last time"))
        if (isinstance(node, ast.Attribute) and node.attr in {"cdf", "ppf", "sf", "isf"}
                and isinstance(node.value, ast.Name) and node.value.id == "norm"):
            out.append(Violation(
                "normal_approximation", "§9.4 (§8)", f"{path}:{node.lineno}",
                f"normal tail `norm.{node.attr}` used in the analysis"))

    cert_fns = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        doc = ast.get_docstring(node) or ""
        if not (CERT_FN_RE.search(node.name) or CERT_FN_RE.search(doc)):
            continue
        cert_fns.append(node.name)
        for sub in ast.walk(node):
            if (isinstance(sub, ast.Constant) and isinstance(sub.value, float)
                    and sub.value in Z_CONSTANTS):
                out.append(Violation(
                    "normal_approximation", "§9.4 (§8)",
                    f"{path}:{sub.lineno} in {node.name}()",
                    f"normal quantile {sub.value} inside certificate inference — a "
                    "Wald/normal interval, where §8 requires the exact tail"))
            if isinstance(sub, ast.Call) and getattr(
                    sub.func, "id", getattr(sub.func, "attr", "")) == "proportion_confint":
                methods = [k.value.value for k in sub.keywords
                           if k.arg == "method" and isinstance(k.value, ast.Constant)]
                if methods != ["beta"]:
                    out.append(Violation(
                        "normal_approximation", "§9.4 (§8)",
                        f"{path}:{sub.lineno} in {node.name}()",
                        f"proportion_confint(method={methods or 'unset'}) — only "
                        "method='beta' is Clopper-Pearson; every other method is an "
                        "approximation"))

    if cert_fns and not EXACT_TAIL_RE.search(analysis):
        out.append(Violation(
            "normal_approximation", "§9.4 (§8)", path,
            f"certificate inference ({', '.join(cert_fns)}) with no exact binomial "
            "tail anywhere in the file — §8 requires scipy.stats.binom and "
            "Clopper-Pearson, so the tail has been computed some other way"))
    return out


# ==========================================================================
# §9.5 -- nothing that failed, excepted, went unrankable or went missing is hidden
# ==========================================================================

def _rows(obj: dict | None, key: str = "rows") -> list[dict]:
    """Rows or cells, each carrying an explicit ``condition_id``.

    The benchmark runner takes ``--condition`` and records it **once, in the
    envelope**; the analyser's certificate cells call the field ``condition``.
    Both are reasonable, and neither gives a row the key these checks group by.
    Reconstructing it here rather than asking either to change keeps the artefact
    the record — but it has to be reconstructed, because a check that grouped by a
    missing key would find every condition complete by finding only one.
    """
    if not obj:
        return []
    v = obj.get(key) or obj.get("cells") or obj.get("entries") or []
    env_cond = obj.get("condition")
    out = []
    for r in v:
        if not isinstance(r, dict):
            continue
        cid = r.get("condition_id") or r.get("condition") or env_cond
        out.append({**r, "condition_id": str(cid)} if cid else dict(r))
    return out


def check_no_suppressed_failures(findings: str | None, ledger: dict | None,
                                 feasibility: dict | None,
                                 benchmark: dict | None) -> list[Violation]:
    """A conclusion may not suppress a failure, an exception, an unrankable cell or
    an unavailable arm.

    The bar is deliberately low — the identifier has to appear *somewhere* in the
    findings document. A validator cannot judge whether a disclosure is adequate,
    and pretending it can would make the check unfalsifiable. It can prove the
    word never appears at all, and FINDINGS §9.4 is why that is worth proving:
    the AUC claim read "18 of 18 cells" for weeks because the six unrankable ones
    were absent from the sentence, not from the data.
    """
    if findings is None:
        return []
    out = []

    for kid, st in sorted(ledger_status(ledger).items()):
        if st == "FAIL" and kid not in findings:
            out.append(Violation(
                "suppressed_failure", "§9.5 (§10)", FINDINGS_REL,
                f"kill-ledger entry {kid} resolved FAIL and is not mentioned anywhere "
                "in the findings — §10.1 narrows the paper claim on a failure, it "
                "never hides one"))

    for r in _rows(feasibility):
        cls, cid = r.get("regime_class"), str(r.get("condition_id", "?"))
        if cls in {"INFEASIBLE", "EXCEPTION"} and not re.search(rf"\b{cid}\b", findings):
            out.append(Violation(
                "suppressed_failure", "§9.5 (§5.1)", FINDINGS_REL,
                f"condition {cid} was classified {cls} "
                f"({r.get('classification_reason', 'no reason recorded')}) and is not "
                "mentioned in the findings"))

    unavailable, unrankable = set(), False
    for r in _rows(benchmark):
        if r.get("unavailable_reason"):
            unavailable.add((str(r.get("condition_id", "?")), str(r.get("arm", "?")),
                             str(r["unavailable_reason"])))
        if r.get("rankable") is False:
            unrankable = True
        if r.get("exclusion_reason"):
            unavailable.add((str(r.get("condition_id", "?")), str(r.get("arm", "?")),
                             str(r["exclusion_reason"])))
    for cid, arm, reason in sorted(unavailable):
        if arm not in findings:
            out.append(Violation(
                "suppressed_failure", "§9.5 (§4)", FINDINGS_REL,
                f"arm {arm} is unavailable in {cid} ({reason}) and is never named in "
                "the findings — §4 records an unavailable arm, it does not drop it"))
    if unrankable and not re.search(r"rankab", findings, re.IGNORECASE):
        out.append(Violation(
            "suppressed_failure", "§9.5 (§9.4 of FINDINGS)", FINDINGS_REL,
            "the benchmark contains unrankable cells and the findings never use the "
            "word 'rankable' — an unrankable cell is not a tie, and dropping it "
            "silently changes the denominator of every ranking claim"))
    return out


# ==========================================================================
# §9.6 -- no universal claim on a four-condition matrix
# ==========================================================================

UNIVERSAL_RE = re.compile(
    r"\balways\b|\buniversally\b|\buniversal\b|\beverywhere\b|in all settings|"
    r"in every setting|under all conditions|any landscape|every landscape|"
    r"all landscapes|for all families|in any setting", re.IGNORECASE)
SCOPE_RE = re.compile(
    r"\bTARGET\b|\bROBUSTNESS\b|\bEXCEPTION\b|\b[CS][1-9]\b|in this study|"
    r"in the conditions tested|conditional on|restricted to|\bwithin\b|\bhill\b|"
    r"\bhartmann6?\b|\backley\b|\blevy\b|\brosenbrock\b")


def check_no_universal_claims(findings: str | None,
                              feasibility: dict | None) -> list[Violation]:
    """A universal claim needs universal evidence, and a four-cell matrix is not.

    Spec §1 states the boundary: *the claim this study may never support is that
    SPADE beats Sobol, BO or DoE everywhere*, and FINDINGS §41 already refutes it
    (SPADE certified nothing in 1,200 ackley campaigns). So the check is not
    conditional on what the feasibility artefact happens to contain — no finite
    condition matrix licenses "always". The artefact supplies the counter-evidence
    the violation message quotes back: which regime classes and which conditions
    the study actually has.

    The exemption is a **scope qualifier in the same sentence** — a regime class,
    a condition id, a family name, "in this study". "In TARGET regimes SPADE always
    produced a non-empty certificate" is a bounded claim about TARGET, which §9.6
    permits, and is a different sentence from "SPADE always produces one".
    """
    if findings is None:
        return []
    rows = _rows(feasibility)
    classes = sorted({str(r.get("regime_class")) for r in rows if r.get("regime_class")})
    conds = sorted({str(r.get("condition_id")) for r in rows if r.get("condition_id")})
    evidence = (f"evidence exists for {len(conds)} condition(s) {conds} in regime "
                f"class(es) {classes}") if rows else "no feasibility artefact to bound it"

    masked = _mask(findings)
    spans = _sentences(findings)
    out = []
    for m in UNIVERSAL_RE.finditer(masked):
        if _is_negated(masked, m.start()):
            continue
        a, b = _sentence_at(spans, m.start())
        sentence = findings[a:b].strip()
        if SCOPE_RE.search(sentence):
            continue
        out.append(Violation(
            "universal_claim", "§9.6 (§1)", f"{FINDINGS_REL}:{_line_of(findings, m.start())}",
            f"unscoped universal {m.group(0)!r} — {evidence}: {sentence[:140]!r}"))
    return out


# ==========================================================================
# §9.7 -- alpha_star is not certificate quality
# ==========================================================================

ALPHA_STAR_RE = re.compile(r"alpha[_ ]?star|alpha\s?\*|\u03b1\s?\*|\u03b1[_ ]star",
                           re.IGNORECASE)
QUALITY_RE = re.compile(
    r"\bqualit|\bvalid|\bevidence\b|\breliab|\bcorrect\b|\btrustworth|\brank|"
    r"\bfirst on\b|\bbetter\b|\bsuperior\b|\bcontainment\b|\bcalibrat", re.IGNORECASE)
ALPHA_DISCLAIMER_RE = re.compile(
    r"willingness to certify|model-?internal|posterior confidence|"
    r"not (?:a )?(?:metric|measure|evidence)|never (?:a )?(?:metric|evidence)",
    re.IGNORECASE)


def check_alpha_star_not_quality_evidence(findings: str | None) -> list[Violation]:
    """FINDINGS §28 declared it and §31 explained it: alpha_star is a functional of
    the fitted posterior and nothing else. In the §28 table it ranks `doe` first —
    the arm with 5.2x the calibration error of any other in the study — and `sobol`
    last, the arm first on calibration, Brier and empirical containment. It
    measures how confidently a model asserts an excursion, not whether the
    assertion is right.

    §28's closing line is a standing prohibition: no ranking, no claim and no kill
    condition in this project may rest on it. So an alpha_star sentence that also
    reaches for quality, validity or a ranking must carry the label."""
    if findings is None:
        return []
    out = []
    for a, b in _sentences(findings):
        s = findings[a:b]
        if not ALPHA_STAR_RE.search(s):
            continue
        if QUALITY_RE.search(s) and not ALPHA_DISCLAIMER_RE.search(s):
            out.append(Violation(
                "alpha_star_misuse", "§9.7 (FINDINGS §28/§31)",
                f"{FINDINGS_REL}:{_line_of(findings, a)}",
                "alpha_star offered as evidence of certificate quality or as a "
                "ranking — §28 declared it MODEL-INTERNAL: it measures willingness "
                f"to certify, and ranks the worst-calibrated arm first: {s.strip()[:140]!r}"))
    return out


# ==========================================================================
# §4 / §13.6 -- every mandatory comparator present or explicitly unavailable
# ==========================================================================

def check_mandatory_comparators(benchmark: dict | None,
                                feasibility: dict | None) -> list[Violation]:
    """§4: every primary condition runs all twelve arms, or records a structured
    ``unavailable_reason``. A missing mandatory comparator is a hard failure that
    blocks any primary conclusion.

    §4.2b is the reason it is mechanical rather than a habit — the Q57 trap is a
    headline that holds against `qLogEI` and dies against the noisy acquisition,
    so running only the weaker of the two manufactures a win without anyone
    intending one. An INFEASIBLE condition is exempt: §10 KF-9 excludes it before
    campaigns run and it is never a method failure.
    """
    if benchmark is None or feasibility is None:
        return []
    live = {}
    for r in _rows(feasibility):
        cid = str(r.get("condition_id", "?"))
        if r.get("tier") != "primary":
            continue
        live[cid] = live.get(cid, False) or r.get("regime_class") != "INFEASIBLE"

    present, excused = set(), set()
    for r in _rows(benchmark):
        key = (str(r.get("condition_id", "?")), str(r.get("arm", "?")))
        (excused if r.get("unavailable_reason") else present).add(key)

    out = []
    for cid in sorted(c for c, alive in live.items() if alive):
        for arm in MANDATORY_ARMS:
            if (cid, arm) in present or (cid, arm) in excused:
                continue
            out.append(Violation(
                "mandatory_comparator", "§4 (§13.6)", f"{cid}",
                f"mandatory arm {arm!r} has no rows in primary condition {cid} and no "
                "structured unavailable_reason — §4 makes a missing comparator a hard "
                "failure that blocks any primary conclusion, not an absence"))

    # The runner computes this itself and prints a warning. A warning on a console
    # nobody kept is not a gate, so the recorded value is re-read here and given
    # the exit code §13.6 says it has.
    for arm in benchmark.get("missing_mandatory_arms") or []:
        out.append(Violation(
            "mandatory_comparator", "§4 (§13.6)",
            str(benchmark.get("condition", benchmark.get("source_files", "benchmark"))),
            f"the benchmark artefact records {arm!r} in 'missing_mandatory_arms' — it "
            "was neither run nor given an unavailable_reason"))
    return out


# ==========================================================================
# §10.1(7) -- every artefact regenerates from frozen code and manifests
# ==========================================================================

MANIFEST_KEYS = ("source_hashes", "code_commit", "config", "environment", "seed_policy")


def check_manifest_regenerates(manifest: dict | None, root: Path) -> list[Violation]:
    """§10.1 item 7: every artefact regenerates from frozen code and manifests.

    FINDINGS T1.4 is the memorial. `results/e2-grid.json` was untracked while five
    scripts anchored to it by path; two clones held two different runs under one
    filename and *both* fidelity gates passed, because each compared a clone
    against itself. A gate that compares a regeneration against an unpinned file
    can only report that a clone agrees with itself.

    So the manifest must pin the source it was produced by, by content hash, and
    this check recomputes every one of them. It must also carry the commit, the
    config, the package environment and the seed policy — §5.4 keys the noise
    stream on (family, d, sigma, instance, campaign) and an artefact that does not
    record which policy produced it cannot be regenerated even from correct code.
    """
    if manifest is None:
        return []
    out = []
    for key in MANIFEST_KEYS:
        if key == "code_commit" and ("code_commit" in manifest or "git_hash" in manifest):
            continue
        if key not in manifest:
            out.append(Violation(
                "manifest_regeneration", "§10.1(7)", ARTEFACT_REL["manifest"],
                f"manifest has no {key!r} — without it the artefact cannot be "
                "regenerated from frozen code"))
    env = manifest.get("environment")
    if isinstance(env, dict) and not (env.get("packages") or env.get("pip_freeze")):
        out.append(Violation(
            "manifest_regeneration", "§10.1(7)", ARTEFACT_REL["manifest"],
            "manifest 'environment' records no package versions — a python version "
            "alone does not pin the numerics"))

    hashes = manifest.get("source_hashes")
    if isinstance(hashes, dict):
        if not hashes:
            out.append(Violation(
                "manifest_regeneration", "§10.1(7)", ARTEFACT_REL["manifest"],
                "'source_hashes' is empty — a manifest that hashes nothing pins nothing"))
        for rel, expected in sorted(hashes.items()):
            p = root / rel
            if not p.is_file():
                out.append(Violation(
                    "manifest_regeneration", "§10.1(7)", rel,
                    "named in the manifest and absent from the tree"))
                continue
            got = hashlib.sha256(p.read_bytes()).hexdigest()
            if got != expected:
                out.append(Violation(
                    "manifest_regeneration", "§10.1(7)", rel,
                    f"source hash mismatch — manifest {str(expected)[:12]}…, tree "
                    f"{got[:12]}…; the artefacts were produced by different code than "
                    "the tree now holds, and cannot be said to regenerate"))
    return out


# ==========================================================================
# The registry, and the program
# ==========================================================================

CHECKS: dict[str, Check] = {
    c.name: c for c in (
        Check("claim_language", "§9.1",
              "a claim word beside a decision the kill ledger did not record as PASS",
              lambda r: check_claim_language(r.findings, r.ledger)),
        Check("table_completeness", "§9.2",
              "a table without condition labels, terminal rule, or denominators",
              lambda r: check_table_completeness(r.findings)),
        Check("same_draw_primacy", "§9.3",
              "same-draw containment presented as primary",
              lambda r: check_same_draw_not_primary(r.findings)),
        Check("normal_approximation", "§9.4",
              "a normal approximation in certificate inference",
              lambda r: check_no_normal_approximation(r.analysis)),
        Check("suppressed_failure", "§9.5",
              "a conclusion suppressing a failure, exception, unrankable cell or "
              "unavailable arm",
              lambda r: check_no_suppressed_failures(r.findings, r.ledger,
                                                     r.feasibility, r.benchmark)),
        Check("universal_claim", "§9.6",
              "a universal claim where only regime-scoped evidence exists",
              lambda r: check_no_universal_claims(r.findings, r.feasibility)),
        Check("alpha_star_misuse", "§9.7",
              "alpha_star offered as evidence of certificate quality",
              lambda r: check_alpha_star_not_quality_evidence(r.findings)),
        Check("mandatory_comparator", "§4 (§13.6)",
              "a mandatory comparator missing from a primary condition",
              lambda r: check_mandatory_comparators(r.benchmark, r.feasibility)),
        Check("manifest_regeneration", "§10.1(7)",
              "artefacts that do not regenerate: manifest hash mismatch",
              lambda r: check_manifest_regenerates(r.manifest, r.root)),
    )
}


def load_release(root: Path, *, pre_release: bool = False) -> Release:
    """Read every artefact the checks need. A missing one is recorded, never faked."""
    rel = Release(root=root)
    for attr, path in (("findings", FINDINGS_REL), ("analysis", ANALYSIS_REL)):
        p = root / path
        if p.is_file():
            setattr(rel, attr, p.read_text())
        else:
            rel.missing.append(path)
    for attr, path in ARTEFACT_REL.items():
        stem = path[:-len(".json")]
        # `run_final_spade_benchmark.py` takes --condition and writes one file per
        # condition, so a release may hold `final-spade-primary-C1.json` .. `-C4`
        # rather than one file. Reading only the bare name would audit one
        # condition and report the other three as complete by never seeing them.
        paths = sorted({*root.glob(f"{stem}.json"), *root.glob(f"{stem}-*.json")})
        if not paths:
            rel.missing.append(path)
            continue
        merged: dict = {}
        rows, cells = [], []
        for p in paths:
            obj = json.loads(p.read_text())
            if not isinstance(obj, dict):
                continue
            cond = obj.get("condition")
            merged = {**{k: v for k, v in obj.items() if k not in ("rows", "cells")},
                      **merged}
            for key, sink in (("rows", rows), ("cells", cells)):
                for item in obj.get(key) or []:
                    if not isinstance(item, dict):
                        continue
                    cid = item.get("condition_id") or item.get("condition") or cond
                    sink.append({**item, "condition_id": str(cid)} if cid else dict(item))
        if rows:
            merged["rows"] = rows
        if cells:
            merged["cells"] = cells
        merged["source_files"] = [str(p.relative_to(root)) for p in paths]
        setattr(rel, attr, merged)
    return rel


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=str(ROOT), type=Path)
    ap.add_argument("--pre-release", action="store_true",
                    help="downgrade absent artefacts to SKIP. The study has not run; "
                         "a gate that cannot be exercised before its inputs exist gets "
                         "written after the results are visible, which is the ordering "
                         "the registration exists to prevent.")
    args = ap.parse_args(argv)
    root = Path(args.root)

    rel = load_release(root, pre_release=args.pre_release)
    print(f"spade-final release audit · root {root}")
    print(f"{len(CHECKS)} checks · spec docs/SPADE-FINAL-SPEC.md §9, §4, §10.1\n")

    violations: list[Violation] = []
    for path in rel.missing:
        if args.pre_release:
            print(f"SKIP  {path} — absent (pre-release mode)")
        else:
            violations.append(Violation(
                "missing_artefact", "§10.1(7)", path,
                "required release artefact is absent; the release cannot be audited "
                "without it"))
    if rel.missing:
        print()

    for name, check in CHECKS.items():
        found = check.run(rel)
        violations.extend(found)
        mark = "FAIL" if found else "ok  "
        print(f"{mark}  {name:<22} {check.section:<12} {len(found)} violation(s)")

    if not violations:
        print("\nPASS — no publication guard fired.")
        return 0

    print(f"\n{len(violations)} VIOLATION(S)\n")
    for v in violations:
        print(v)
    print("\nFAIL — spec §9/§10.1. Nothing above is advisory; each one blocks release.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
