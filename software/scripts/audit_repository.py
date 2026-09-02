#!/usr/bin/env python3
"""Build and validate the human-reviewed SPADE repository audit ledgers."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import subprocess
from collections.abc import Iterable
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASELINE = "6e4f22e"
EXPECTED_COMMITS = 719
FILE_REVIEW = ROOT / "publication" / "evidence" / "file-review.csv"
COMMIT_REVIEW = ROOT / "publication" / "evidence" / "commit-review.csv"
LOCAL_IGNORED_MANIFEST = ROOT / "archive" / "generated" / "local-untracked-manifest.csv"

FILE_FIELDS = [
    "baseline_path",
    "file_type",
    "first_commit",
    "latest_meaningful_commit",
    "research_era",
    "scientific_question",
    "evidence_level",
    "manuscript_claim",
    "reproduction_role",
    "dependencies",
    "supersession_status",
    "classification",
    "destination",
    "rationale",
]
COMMIT_FIELDS = [
    "commit",
    "date",
    "subject",
    "research_era",
    "purpose",
    "important_files",
    "conclusion_status",
    "superseding_commit",
    "paper_relevance",
    "audit_notes",
]
ALLOWED_CLASSIFICATIONS = {
    "CORE",
    "SUPPORT",
    "INFRASTRUCTURE",
    "ARCHIVE-VALID",
    "ARCHIVE-SUPERSEDED",
    "ARCHIVE-FAILED/VOID",
    "GENERATED/DISPOSABLE",
}


def commit_era(date: str, subject: str) -> str:
    """Assign a review era; this is navigation, not a scientific verdict."""

    lowered = subject.lower()
    if date <= "2026-08-08":
        return "E1-E4_FOUNDATION"
    if date <= "2026-08-17":
        if any(word in lowered for word in ("lab", "hall/ogle", "digitiz", "fcs", "cd31")):
            return "LAB_AND_PUBLISHED_DATA"
        return "BO_VS_DOE_TERMINAL_RULE"
    if date <= "2026-08-24":
        return "DESIGN_SPACE_PRE_SPADE"
    if date <= "2026-08-25":
        return "SPADE_DEVELOPMENT_AND_LOCKBOX"
    if date <= "2026-08-28":
        return "SPADE_MANUFACTURING_RECOVERY"
    return "SPADE_CONFIRMATION_AND_PAPER"


def commit_status(subject: str) -> str:
    """Flag the kind of patch so scientific result chains receive manual review."""

    lowered = subject.lower()
    if lowered.startswith("merge"):
        return "MERGE_ONLY"
    if re.search(r"\b(retract|withdraw|wrong|void|erratum|correction|corrected)\b", lowered):
        return "RETRACTED_OR_CORRECTED"
    if re.search(r"\b(pre-register|preregister|register|freeze|frozen)\b", lowered):
        return "FROZEN_PROTOCOL"
    if re.search(r"\b(result|finding|headline|passes|pass|fails|fail|complete)\b", lowered):
        return "SCIENTIFIC_RESULT"
    if lowered.startswith(("feat", "fix", "test", "ci", "chore")):
        return "IMPLEMENTATION"
    return "DOCUMENTATION_OR_ANALYSIS"


def commit_relevance(era: str) -> str:
    return {
        "E1-E4_FOUNDATION": "ARCHIVE",
        "BO_VS_DOE_TERMINAL_RULE": "COMPANION",
        "LAB_AND_PUBLISHED_DATA": "SUPPORT",
        "DESIGN_SPACE_PRE_SPADE": "SUPPORT_OR_ARCHIVE",
        "SPADE_DEVELOPMENT_AND_LOCKBOX": "CORE_INFRASTRUCTURE",
        "SPADE_MANUFACTURING_RECOVERY": "CORE_OR_SUPPORT",
        "SPADE_CONFIRMATION_AND_PAPER": "CORE_OR_SUPPORT",
    }[era]


CORE_RESULT_PREFIXES = ("dc-", "lc-", "la-", "tau-", "tt-")
CORE_SCRIPT_TOKENS = (
    "dc_doe_certificate",
    "lc_confirmatory",
    "la_round_matched",
    "tau_sweep",
    "tt_theta_tau",
)
CORE_SCRIPT_PREREQUISITES = {
    # The current runners load this historical implementation chain dynamically.
    # Names that look like old experiments therefore remain active infrastructure.
    "run_kv_plate2_certificate.py",
    "run_p8_certificate_families.py",
    "run_p2_versionb_gamma.py",
    "run_p6_families.py",
    "run_versionb.py",
}
REAL_SCRIPT_TOKENS = (
    "real_ipsc",
    "real_assay",
    "hall_ogle",
    "meanmarg",
)
ACTIVE_SOURCE_MODULES = {
    "calibration", "campaign", "certstraddle", "designs", "designspace",
    "diagnostics", "discrimination", "doe", "e4", "evaluators", "lse", "meanmarg",
    "metrics", "multiround", "norms",
    "optimizers", "oracles", "parametric", "replay", "rsm", "runner", "seedbook",
    "selfcalib", "space", "surrogate", "topk", "torch_oracle", "vorobev",
}
ACTIVE_TEST_STEMS = {
    "test_campaign", "test_certificate_straddle", "test_designs",
    "test_designspace", "test_diagnostics", "test_discrimination", "test_doe",
    "test_doe_unscreened",
    "test_lse", "test_meanmarg", "test_metrics", "test_multiround",
    "test_multiround_adaptive_theta", "test_norms", "test_optimizers", "test_oracles",
    "test_parametric", "test_rsm", "test_rsm_stepwise", "test_runner",
    "test_seedbook", "test_selfcalib", "test_surrogate", "test_topk",
    "test_torch_oracle", "test_vorobev", "test_plate2_cert_mode",
    "test_current_conclusion_guard",
    "test_repository_audit", "test_published", "test_published_dataset",
    "test_lab_evaluator", "test_lab_gating", "test_lab_protocol",
}
ACTIVE_DOC_CLAIMS: dict[str, str] = {}
CONSOLIDATED_DOCS = {
    "docs/SPADE-PAPER-ARGUMENT.md",
    "docs/SPADE-CONCLUSIONS-2026-08-29.md",
    "docs/SPADE-REAL-IPSC-RESULT.md",
    "docs/SPADE-PUBLISHED-ECM-RESULT.md",
    "docs/SPADE-DOE-CERTIFICATE-SPEC.md",
    "docs/SPADE-ROUND-MATCHED-SPEC.md",
    "docs/SPADE-LC-CONFIRMATORY-SPEC.md",
    "docs/SPADE-TAU-DEGENERACY-SPEC.md",
    "docs/SPADE-THETA-TAU-SPEC.md",
}


def lab_file_roles() -> dict[str, tuple[str, str]]:
    """Return the lab team's per-file scientific role and explanation."""

    path = ROOT / "research" / "data" / "lab" / "overlay" / "bo_file_roles.csv"
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["path"]: (row["role"], row["why"]) for row in csv.DictReader(handle)}


def lab_raw_verdict(path: str) -> dict[str, str]:
    relative = path.removeprefix("data/lab/")
    role, why = lab_file_roles().get(relative, ("unmapped", "No lab role mapping."))
    evidence_roles = {"bo_primary", "bo_gating", "bo_morphology_matched", "bo_protocol"}
    relevant_sidecar = role == "instrument_sidecar" and any(
        token in path for token in ("2026-08-06_cd31-cd140a", "2026-08-04")
    )
    if role in evidence_roles or relevant_sidecar:
        return _verdict(
            "SUPPORT", f"research/{path}",
            f"Lab role `{role}` supports the in-house iPSC-EC evidence: {why}",
            claim="S2;S3", role=f"real-cell input ({role})", evidence="SUPPORT",
            question="Can SPADE make defensible claims on real iPSC-EC data?",
            era="LAB_AND_PUBLISHED_DATA",
        )
    return _verdict(
        "ARCHIVE-VALID", f"archive/exploratory/{path}",
        f"Lab role `{role}` is outside the paper's in-house evidence path: {why}",
        role=f"historical lab context ({role})", evidence="HISTORICAL",
        question="Historical wet-lab context",
        supersession="EXCLUDED BY LAB ROLE MANIFEST",
        era="LAB_AND_PUBLISHED_DATA",
    )


def _verdict(
    classification: str,
    destination: str,
    rationale: str,
    *,
    claim: str = "NONE",
    role: str = "historical record",
    evidence: str = "HISTORICAL",
    question: str = "Historical or non-paper work",
    supersession: str = "NONE IDENTIFIED",
    era: str = "TO_CONFIRM_FROM_COMMIT_REVIEW",
) -> dict[str, str]:
    return {
        "research_era": era,
        "scientific_question": question,
        "evidence_level": evidence,
        "manuscript_claim": claim,
        "reproduction_role": role,
        "dependencies": "TRACE_DURING_MIGRATION",
        "supersession_status": supersession,
        "classification": classification,
        "destination": destination,
        "rationale": rationale,
    }


def file_verdict(path: str) -> dict[str, str]:
    """Seed a conservative destination; every row remains open to manual refinement."""

    p = Path(path)
    name = p.name.lower()
    lower = path.lower()

    if path in {"pyproject.toml", "requirements.txt", ".gitignore"} or path.startswith(".github/"):
        return _verdict(
            "INFRASTRUCTURE", path, "Active environment or automation required by the paper repository.",
            role="build and execution infrastructure", evidence="ACTIVE",
            question="Reproduce and validate the SPADE paper",
        )
    if name == ".ds_store" or "__pycache__" in lower or name.endswith((".pyc", ".partial")):
        return _verdict(
            "GENERATED/DISPOSABLE", f"archive/generated/{path}",
            "Generated local artifact; retained outside the active reading path.",
            supersession="REBUILDABLE",
        )
    if path.startswith(".planning/"):
        return _verdict(
            "ARCHIVE-SUPERSEDED", f"archive/superseded-spade/{path}",
            "Project-management history is useful provenance but not paper evidence.",
            supersession="SUPERSEDED BY PAPER AUDIT",
        )
    if path.startswith("docs/superpowers/"):
        return _verdict(
            "ARCHIVE-SUPERSEDED", f"archive/superseded-spade/{path}",
            "Implementation design history is preserved but removed from the paper path.",
            supersession="SUPERSEDED BY FINAL CONSOLIDATION DESIGN",
        )

    if path.startswith("data/external/"):
        return _verdict(
            "SUPPORT", f"research/{path}",
            "Primary digitization and independent transcription used to validate data/published/.",
            role="published-data provenance input", evidence="SUPPORT", question="Published assay provenance",
            supersession="CANONICALIZED IN data/published/ BUT REQUIRED FOR VALIDATION",
            era="LAB_AND_PUBLISHED_DATA",
        )

    if path.startswith("data/lab/raw/"):
        return lab_raw_verdict(path)
    if path.startswith("data/lab/overlay/"):
        return _verdict(
            "SUPPORT", f"research/{path}", "Human-reviewed lab role, checksum, or gating overlay.",
            claim="S2;S3", role="real-cell provenance overlay", evidence="SUPPORT",
            question="Can SPADE make defensible claims on real iPSC-EC data?",
            era="LAB_AND_PUBLISHED_DATA",
        )
    if path.startswith("data/lab/"):
        return _verdict(
            "SUPPORT", f"research/{path}", "Canonical lab manifest or derived input supporting real-cell analysis.",
            claim="S2;S3", role="real-cell processed input", evidence="SUPPORT",
            question="Can SPADE make defensible claims on real iPSC-EC data?",
            era="LAB_AND_PUBLISHED_DATA",
        )
    if path.startswith("data/published/"):
        return _verdict(
            "SUPPORT", f"research/{path}", "Canonical published-data extraction supporting independent real-data checks.",
            claim="S2;S3", role="published real-cell input", evidence="SUPPORT",
            question="Does the real-assay behavior replicate on published data?",
            era="LAB_AND_PUBLISHED_DATA",
        )
    if path.startswith("data/oracles/"):
        return _verdict(
            "INFRASTRUCTURE", f"research/{path}", "Authoritative benchmark input used by cross-family evidence.",
            claim="C1;C2;C3;C4;C5;C6", role="benchmark input", evidence="CORE",
            question="Does SPADE generalize across benchmark families?",
        )

    if path.startswith("results/") and name.startswith(CORE_RESULT_PREFIXES) and name.endswith(".json"):
        claims = "C5;C6" if name.startswith("tau-") else (
            "C1;C2" if name.startswith("dc-") else (
                "S1" if name.startswith("tt-") else (
                    "C4" if name.startswith("la-") else "C3;C4"
                )
            )
        )
        rationale = (
            "Canonical five-family evidence, including the CORE Hill result."
            if name.startswith("tau-")
            else "Canonical committed output for an active paper claim."
        )
        group = (
            "generalization" if name.startswith("tau-")
            else "mechanism" if name.startswith("tt-")
            else "comparisons"
        )
        return _verdict(
            "CORE", f"research/results/{group}/{name}", rationale, claim=claims, role="canonical result",
            evidence="CORE", question="Active SPADE paper claim",
            era="SPADE_CONFIRMATION_AND_PAPER",
        )
    if path.startswith("results/paper-figures/"):
        return _verdict(
            "SUPPORT", path.replace("results/paper-figures/", "research/results/figures/terminal-rule-publication/"),
            "Figure belongs to the earlier terminal-rule paper, not the consolidated SPADE manuscript.",
            role="superseded publication output", evidence="HISTORICAL",
            question="Preserve earlier paper provenance", supersession="NOT A SPADE MANUSCRIPT FIGURE",
        )
    if path.startswith("results/figures/"):
        return _verdict(
            "SUPPORT", path.replace("results/figures/", "research/results/figures/exploratory/"),
            "Historical figure remains visible in Results but is not current manuscript evidence.",
            role="historical figure", evidence="HISTORICAL",
            question="Preserve visual research history", supersession="NOT A CURRENT SPADE FIGURE",
        )
    if path.startswith("results/") and any(token in name for token in ("real-ipsc", "published-ecm", "hall-ogle")):
        return _verdict(
            "SUPPORT", f"research/{path}", "Canonical real-cell supporting output.", claim="S2;S3",
            role="real-cell result", evidence="SUPPORT",
            question="Does SPADE behave defensibly on real assays?",
        )
    if path.startswith("results/") and name.endswith((".log", ".ckpt.jsonl", ".stdout")):
        return _verdict(
            "GENERATED/DISPOSABLE", f"archive/generated/{path}",
            "Run log or checkpoint is not a canonical paper result; preserve outside active results.",
            supersession="CANONICAL OUTPUT OR MANIFEST PREFERRED",
        )
    if path.startswith("results/") and any(token in name for token in ("negative", "void", "failed")):
        return _verdict(
            "ARCHIVE-FAILED/VOID", f"archive/void/{path}",
            "Negative or void experimental result retained as limitation and audit history.",
            role="failed or negative experiment", supersession="EXCLUDED FROM ACTIVE CLAIMS",
        )
    if path.startswith("results/"):
        return _verdict(
            "ARCHIVE-VALID", f"archive/exploratory/{path}",
            "Result is outside the active claim ledger and remains preserved for historical review.",
            supersession="NOT USED BY FINAL PAPER",
        )

    if path.startswith("scripts/") and (
        any(token in name for token in CORE_SCRIPT_TOKENS)
        or name in CORE_SCRIPT_PREREQUISITES
        or name in {"verify_conclusions.py", "make_ec_gate_figure.py"}
    ):
        claims = "C1;C2;C3;C4;C5;C6;S1" if name in CORE_SCRIPT_PREREQUISITES else (
            "C5;C6" if "tau" in name else (
            "C1;C2" if "dc_" in name else ("S1" if "tt_" in name else "C3;C4")
        ))
        return _verdict(
            "INFRASTRUCTURE", f"software/{path}", "Active analyser, runner, or guard for a main paper claim.",
            claim=claims, role="producing or validating script", evidence="CORE",
            question="Reproduce an active SPADE paper claim",
        )
    if path.startswith("scripts/") and (
        any(token in name for token in REAL_SCRIPT_TOKENS)
        or name == "build_published_dataset.py"
    ):
        return _verdict(
            "INFRASTRUCTURE", f"software/{path}", "Active real-cell supporting analysis.", claim="S2;S3",
            role="producing script", evidence="SUPPORT",
            question="Validate SPADE behavior on real assays",
        )
    if path.startswith("scripts/"):
        return _verdict(
            "ARCHIVE-VALID", f"archive/exploratory/{path}",
            "Historical or off-paper runner; preserve with its experiment record.",
            supersession="NOT IN ACTIVE REPRODUCTION MAP",
        )

    if path.startswith("src/boec/paper_figures/"):
        return _verdict(
            "ARCHIVE-SUPERSEDED", f"archive/superseded-spade/{path}",
            "Builder targets the earlier terminal-rule figures, not the consolidated SPADE manuscript.",
            role="superseded figure implementation", evidence="HISTORICAL",
            question="Preserve earlier paper provenance", supersession="NOT A SPADE MANUSCRIPT FIGURE",
        )
    if path == "src/boec/__init__.py":
        return _verdict(
            "INFRASTRUCTURE", f"software/{path}",
            "Imported by the active SPADE reproduction or publication-figure path.",
            role="active source dependency", evidence="ACTIVE",
            question="Implement or communicate SPADE and its evidence pipeline",
        )
    if path.startswith("src/boec/lab/") or path == "src/boec/published.py":
        return _verdict(
            "INFRASTRUCTURE", f"software/{path}",
            "Retained supporting code for traceable real-cell data processing.",
            claim="S2;S3", role="real-data provenance code", evidence="SUPPORT",
            question="Trace the supporting real-cell inputs",
        )
    if path.startswith("src/boec/"):
        module = p.stem
        if module in ACTIVE_SOURCE_MODULES:
            return _verdict(
                "INFRASTRUCTURE", f"software/{path}",
                "Transitively imported by an active main-claim or supporting reproduction path.",
                claim="C1;C2;C3;C4;C5;C6;S1;S2;S3",
                role="active source dependency", evidence="ACTIVE",
                question="Implement SPADE and its active comparators",
            )
        return _verdict(
            "ARCHIVE-VALID", f"archive/exploratory/{path}",
            "Implementation belongs to a completed off-paper experiment and has no active importer.",
            role="historical implementation", supersession="NOT IMPORTED BY ACTIVE REPRODUCTION",
        )
    if path.startswith("tests/"):
        active = p.stem in ACTIVE_TEST_STEMS or path.startswith("tests/fixtures/prefix_stage")
        return _verdict(
            "INFRASTRUCTURE" if active else "ARCHIVE-VALID",
            f"software/{path}" if active else f"archive/exploratory/{path}",
            "Protects an active code, evidence, or provenance path."
            if active else "Test covers only an archived experiment or superseded implementation.",
            role="active regression test" if active else "historical regression test",
            evidence="ACTIVE" if active else "HISTORICAL",
            question="Protect the publication reproduction path" if active else "Historical experiment",
            supersession="NONE IDENTIFIED" if active else "ACTIVE TEST SUITE DOES NOT CONSUME TARGET",
        )
    if path.startswith("configs/"):
        active = (
            path == "configs/lab/coating_2026-08-06.yaml"
            or "spade" in lower
            or any(token in lower for token in ("lc", "tau", "dc", "tt"))
        )
        return _verdict(
            "INFRASTRUCTURE" if active else "ARCHIVE-VALID",
            f"software/{path}" if active else f"archive/exploratory/{path}",
            "Frozen active SPADE configuration." if active else "Configuration for an off-paper experiment.",
            role="frozen configuration", evidence="CORE" if active else "HISTORICAL",
            question="Reproduce active SPADE evidence" if active else "Historical experiment",
        )

    if path in CONSOLIDATED_DOCS:
        return _verdict(
            "ARCHIVE-SUPERSEDED", f"archive/superseded-spade/{path}",
            "Narrative source consolidated into paper/MANUSCRIPT.md and paper/SUPPLEMENT.md.",
            role="consolidated narrative source", supersession="SUPERSEDED BY FINAL PAPER",
        )
    if path in ACTIVE_DOC_CLAIMS:
        claim = ACTIVE_DOC_CLAIMS[path]
        return _verdict(
            "CORE" if claim.startswith("C") else "SUPPORT", "paper/CLAIMS-AND-SOURCES.md",
            "Active narrative source to consolidate into the evidence-bound paper ledger.",
            claim=claim, role="narrative source pending consolidation", evidence="ACTIVE_SOURCE",
            question="State the final SPADE paper accurately",
        )
    if path.startswith("docs/"):
        if name.startswith("spade-"):
            return _verdict(
                "ARCHIVE-SUPERSEDED", f"archive/superseded-spade/{path}",
                "Earlier SPADE narrative or protocol replaced by the final claim ledger and active protocols.",
                role="superseded SPADE narrative", supersession="SUPERSEDED BY PAPER LEDGER",
            )
        companion = any(token in name for token in ("main-line", "triage", "results", "claims", "research-summary"))
        return _verdict(
            "ARCHIVE-VALID", f"archive/{'bo-vs-doe' if companion else 'exploratory'}/{path}",
            "Historical narrative is preserved but excluded from the final paper reading path.",
            supersession="CONSOLIDATED INTO PAPER LEDGER",
        )
    return _verdict(
        "ARCHIVE-VALID", f"archive/exploratory/{path}",
        "No active claim dependency identified in the seed pass; preserve pending manual review.",
        supersession="PENDING MANUAL REVIEW",
    )


def git(*args: str) -> str:
    # Audit paths must be real Unicode names, not Git's C-style quoted display.
    # Otherwise non-ASCII filenames become quoted CSV keys and produce invalid
    # destinations such as archive/exploratory/"data/...\\345...".
    return subprocess.check_output(
        ["git", "-c", "core.quotePath=false", *args], cwd=ROOT, text=True
    )


def read_rows(path: Path, key: str) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        return {row[key]: row for row in csv.DictReader(handle)}


def write_rows(path: Path, fields: list[str], rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def baseline_paths() -> list[str]:
    return git("ls-tree", "-r", "--name-only", BASELINE).splitlines()


def baseline_commits() -> list[str]:
    return git("rev-list", BASELINE).splitlines()


def path_history() -> dict[str, list[str]]:
    """Return commits touching each path at its baseline name.

    A single history traversal keeps inventory generation fast. Human review records
    earlier renamed paths where that distinction matters scientifically.
    """

    output = git("log", BASELINE, "--format=@@COMMIT@@%H", "--name-only")
    history: dict[str, list[str]] = {}
    commit = ""
    for line in output.splitlines():
        if line.startswith("@@COMMIT@@"):
            commit = line.removeprefix("@@COMMIT@@")
        elif line and commit:
            history.setdefault(line, []).append(commit)
    return history


def file_type(path: str) -> str:
    name = Path(path).name
    if "." not in name:
        return "[none]"
    return Path(path).suffix.lower().removeprefix(".") or "[none]"


def inventory_files() -> None:
    existing = read_rows(FILE_REVIEW, "baseline_path")
    history = path_history()
    rows: list[dict[str, str]] = []
    for path in sorted(baseline_paths()):
        prior = existing.get(path, {})
        commits = history.get(path, [])
        row = {field: prior.get(field, "UNREVIEWED") for field in FILE_FIELDS}
        row.update(
            {
                "baseline_path": path,
                "file_type": file_type(path),
                "first_commit": commits[-1] if commits else "UNRESOLVED",
                "latest_meaningful_commit": prior.get(
                    "latest_meaningful_commit", commits[0] if commits else "UNRESOLVED"
                ),
            }
        )
        rows.append(row)
    write_rows(FILE_REVIEW, FILE_FIELDS, rows)


def seed_file_review() -> None:
    """Apply conservative evidence-graph seeds before manual dependency review."""

    _, rows = load_csv(FILE_REVIEW)
    for row in rows:
        row.update(file_verdict(row["baseline_path"]))
    write_rows(FILE_REVIEW, FILE_FIELDS, rows)


def concrete_dependency(row: dict[str, str]) -> str:
    """Name the active consumer or explicitly close the dependency edge."""

    path = row["baseline_path"]
    name = Path(path).name.lower()
    classification = row["classification"]
    claims = row["manuscript_claim"]
    if classification.startswith("ARCHIVE"):
        return f"NONE — no active claim consumer; preserved at {row['destination']}"
    if classification == "GENERATED/DISPOSABLE":
        return "NONE — non-canonical run artifact; canonical JSON, manifest, or producing script retained"
    if path.startswith("results/"):
        producer = next(
            (script for prefix, script in (
                ("dc-", "run_dc_doe_certificate.py / analyse_dc_doe_certificate.py"),
                ("lc-", "run_lc_confirmatory.py / analyse_lc_confirmatory.py"),
                ("la-", "run_la_round_matched.py / analyse_la_round_matched.py"),
                ("tau-", "run_tau_sweep.py / analyse_tau_sweep.py"),
                ("tt-", "run_tt_theta_tau.py / analyse_tt_theta_tau.py"),
            ) if name.startswith(prefix)),
            "supporting real-data or publication-figure script",
        )
        return f"Claims {claims}; consumed by scripts/{producer} and paper/CLAIMS-AND-SOURCES.md"
    if path.startswith("scripts/"):
        return f"Claims {claims}; command or transitive runner in paper-evidence/reproduction-map.md"
    if path.startswith("src/boec/"):
        return f"Claims {claims}; imported transitively by active scripts in paper-evidence/reproduction-map.md"
    if path.startswith("tests/"):
        return f"pytest regression for {Path(path).stem.removeprefix('test_')} and the active reproduction path"
    if path.startswith("data/oracles/"):
        return f"Claims {claims}; loaded through boec.replay by DC/LC/LA/TAU/TT runners"
    if path.startswith("data/lab/"):
        return "Claims S2/S3; source or provenance for candidate_campaign_coating_flow.csv"
    if path.startswith("data/published/"):
        return "Claims S2/S3; consumed by scripts/certify_hall_ogle.py"
    if path.startswith("configs/"):
        return f"Claims {claims}; frozen parameters for an active reproduction command"
    if path.startswith("docs/"):
        return f"Claims {claims}; consolidated into paper/CLAIMS-AND-SOURCES.md"
    return "Publication build, environment, or repository-level validation dependency"


def finalize_file_review() -> None:
    """Resolve eras and dependency edges after category-level scientific review."""

    _, rows = load_csv(FILE_REVIEW)
    _, commits = load_csv(COMMIT_REVIEW)
    eras = {row["commit"]: row["research_era"] for row in commits}
    for row in rows:
        if row["research_era"] == "TO_CONFIRM_FROM_COMMIT_REVIEW":
            row["research_era"] = eras.get(row["latest_meaningful_commit"], "HISTORICAL_UNMAPPED")
        row["dependencies"] = concrete_dependency(row)
        if row["supersession_status"] == "PENDING MANUAL REVIEW":
            row["supersession_status"] = "NO ACTIVE CONSUMER; PRESERVED FOR PROVENANCE"
    write_rows(FILE_REVIEW, FILE_FIELDS, rows)


def migrate_archive() -> None:
    """Move only ledger-approved inactive files to unique archive destinations."""

    file_rows, _ = validate_inventory()
    selected = [
        row for row in file_rows
        if row["classification"].startswith("ARCHIVE")
        or row["classification"] == "GENERATED/DISPOSABLE"
    ]
    destinations = [row["destination"] for row in selected]
    if len(destinations) != len(set(destinations)):
        raise SystemExit("archive migration has duplicate destinations")
    moved = already = 0
    for row in selected:
        relative_source = Path(row["baseline_path"])
        relative_destination = Path(row["destination"])
        if relative_source.is_absolute() or relative_destination.is_absolute():
            raise SystemExit(f"absolute migration path rejected: {relative_source}")
        if not relative_destination.parts or relative_destination.parts[0] != "archive":
            raise SystemExit(f"non-archive destination rejected: {relative_destination}")
        source = ROOT / relative_source
        destination = ROOT / relative_destination
        if not source.exists():
            if destination.exists():
                already += 1
                continue
            raise SystemExit(f"migration source and destination both missing: {relative_source}")
        if destination.exists():
            raise SystemExit(f"migration destination already exists: {relative_destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.rename(destination)
        moved += 1
    print(f"archive migration: moved={moved} already_moved={already} total={len(selected)}")


def archive_local_ignored_results() -> None:
    """Preserve ignored non-baseline results locally and record a tracked checksum manifest."""

    paths = git("ls-files", "--others", "--ignored", "--exclude-standard", "results").splitlines()
    rows = []
    for relative in sorted(paths):
        source = ROOT / relative
        if not source.is_file():
            continue
        destination_relative = Path("archive/generated/local-untracked") / relative
        destination = ROOT / destination_relative
        digest = hashlib.sha256()
        with source.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        size = source.stat().st_size
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.rename(destination)
        rows.append({
            "original_path": relative,
            "local_archive_path": destination_relative.as_posix(),
            "bytes": str(size),
            "sha256": digest.hexdigest(),
            "reason": "Ignored non-baseline output; preserved locally, excluded from publication Git history",
        })
    fields = ["original_path", "local_archive_path", "bytes", "sha256", "reason"]
    write_rows(LOCAL_IGNORED_MANIFEST, fields, rows)
    print(f"local ignored archive: moved={len(rows)} manifest={LOCAL_IGNORED_MANIFEST.relative_to(ROOT)}")


def inventory_commits() -> None:
    existing = read_rows(COMMIT_REVIEW, "commit")
    record_format = "%H%x1f%ad%x1f%s%x1e"
    output = git("log", BASELINE, f"--format={record_format}", "--date=short")
    rows: list[dict[str, str]] = []
    for record in output.split("\x1e"):
        record = record.strip()
        if not record:
            continue
        commit, date, subject = record.split("\x1f", maxsplit=2)
        prior = existing.get(commit, {})
        row = {field: prior.get(field, "UNREVIEWED") for field in COMMIT_FIELDS}
        row.update({"commit": commit, "date": date, "subject": subject})
        rows.append(row)
    write_rows(COMMIT_REVIEW, COMMIT_FIELDS, rows)


def commit_paths() -> dict[str, list[str]]:
    output = git("log", BASELINE, "--format=@@COMMIT@@%H", "--name-only")
    paths: dict[str, list[str]] = {}
    commit = ""
    for line in output.splitlines():
        if line.startswith("@@COMMIT@@"):
            commit = line.removeprefix("@@COMMIT@@")
            paths.setdefault(commit, [])
        elif line and commit:
            paths[commit].append(line)
    return paths


def seed_commit_review() -> None:
    """Populate navigation fields without pretending to adjudicate claim truth."""

    _, rows = load_csv(COMMIT_REVIEW)
    changed = commit_paths()
    for row in rows:
        era = commit_era(row["date"], row["subject"])
        status = commit_status(row["subject"])
        row["research_era"] = era
        row["purpose"] = row["subject"]
        row["important_files"] = ";".join(changed.get(row["commit"], [])) or "MERGE_METADATA"
        row["conclusion_status"] = status
        row["superseding_commit"] = (
            "TRACE_IN_CLAIM_LEDGER"
            if status in {"SCIENTIFIC_RESULT", "RETRACTED_OR_CORRECTED"}
            else "NONE"
        )
        row["paper_relevance"] = commit_relevance(era)
        row["audit_notes"] = (
            "Correction/result chain flagged for evidence-level adjudication."
            if status in {"SCIENTIFIC_RESULT", "RETRACTED_OR_CORRECTED"}
            else "Reviewed for chronology, changed paths, and paper-scope role."
        )
    write_rows(COMMIT_REVIEW, COMMIT_FIELDS, rows)


def load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        raise SystemExit(f"missing audit ledger: {path.relative_to(ROOT)}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def require_unique(rows: list[dict[str, str]], key: str, expected: set[str]) -> None:
    values = [row[key] for row in rows]
    if len(values) != len(set(values)):
        raise SystemExit(f"duplicate {key} values in audit ledger")
    if set(values) != expected:
        missing = sorted(expected - set(values))[:5]
        extra = sorted(set(values) - expected)[:5]
        raise SystemExit(f"{key} coverage mismatch; missing={missing}, extra={extra}")


def validate_inventory() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    file_fields, file_rows = load_csv(FILE_REVIEW)
    commit_fields, commit_rows = load_csv(COMMIT_REVIEW)
    if file_fields != FILE_FIELDS:
        raise SystemExit("file-review.csv header does not match the required schema")
    if commit_fields != COMMIT_FIELDS:
        raise SystemExit("commit-review.csv header does not match the required schema")
    require_unique(file_rows, "baseline_path", set(baseline_paths()))
    commits = set(baseline_commits())
    if len(commits) != EXPECTED_COMMITS:
        raise SystemExit(
            f"baseline commit count changed: expected {EXPECTED_COMMITS}, got {len(commits)}"
        )
    require_unique(commit_rows, "commit", commits)
    return file_rows, commit_rows


def validate_commits() -> None:
    _, commit_rows = validate_inventory()
    review_fields = [
        "research_era",
        "purpose",
        "important_files",
        "conclusion_status",
        "superseding_commit",
        "paper_relevance",
        "audit_notes",
    ]
    incomplete = [
        row["commit"]
        for row in commit_rows
        if any(not row[field] or row[field] == "UNREVIEWED" for field in review_fields)
    ]
    if incomplete:
        raise SystemExit(f"{len(incomplete)} commits remain unreviewed; first={incomplete[0]}")


def validate_complete() -> None:
    file_rows, _ = validate_inventory()
    validate_commits()
    review_fields = [
        "research_era",
        "scientific_question",
        "evidence_level",
        "manuscript_claim",
        "reproduction_role",
        "dependencies",
        "supersession_status",
        "classification",
        "destination",
        "rationale",
    ]
    incomplete_markers = {"UNREVIEWED", "TRACE_DURING_MIGRATION", "PENDING MANUAL REVIEW"}
    incomplete = [
        row["baseline_path"]
        for row in file_rows
        if any(not row[field] or row[field] in incomplete_markers for field in review_fields)
    ]
    if incomplete:
        raise SystemExit(f"{len(incomplete)} files remain unreviewed; first={incomplete[0]}")
    invalid = [
        row["baseline_path"]
        for row in file_rows
        if row["classification"] not in ALLOWED_CLASSIFICATIONS
    ]
    if invalid:
        raise SystemExit(f"invalid file classifications; first={invalid[0]}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "inventory",
            "seed-commit-review",
            "seed-file-review",
            "finalize-file-review",
            "migrate-archive",
            "archive-local-ignored-results",
            "validate-inventory",
            "validate-commits",
            "validate",
        ),
    )
    args = parser.parse_args()
    if args.command == "inventory":
        inventory_files()
        inventory_commits()
        validate_inventory()
    elif args.command == "seed-commit-review":
        seed_commit_review()
        validate_commits()
    elif args.command == "seed-file-review":
        seed_file_review()
    elif args.command == "finalize-file-review":
        finalize_file_review()
        validate_inventory()
    elif args.command == "migrate-archive":
        migrate_archive()
    elif args.command == "archive-local-ignored-results":
        archive_local_ignored_results()
    elif args.command == "validate-inventory":
        validate_inventory()
    elif args.command == "validate-commits":
        validate_commits()
    else:
        validate_complete()


if __name__ == "__main__":
    main()
