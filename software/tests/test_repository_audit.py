from __future__ import annotations

import csv
import importlib.util
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASELINE = "6e4f22e"


def _audit_module():
    path = ROOT / "software" / "scripts" / "audit_repository.py"
    spec = importlib.util.spec_from_file_location("audit_repository", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(*args: str) -> list[str]:
    output = subprocess.check_output(
        ["git", "-c", "core.quotePath=false", *args], cwd=ROOT, text=True
    )
    return output.splitlines()


def _rows(path: str) -> list[dict[str, str]]:
    with (ROOT / path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_baseline_commit_count_is_frozen() -> None:
    assert _git("rev-list", "--count", BASELINE) == ["719"]


def test_file_review_has_one_unique_row_per_baseline_file() -> None:
    tracked = _git("ls-tree", "-r", "--name-only", BASELINE)
    rows = _rows("publication/evidence/file-review.csv")
    paths = [row["baseline_path"] for row in rows]

    assert len(paths) == len(tracked)
    assert len(paths) == len(set(paths))
    assert sorted(paths) == sorted(tracked)


def test_commit_review_has_one_unique_row_per_baseline_commit() -> None:
    commits = _git("rev-list", BASELINE)
    rows = _rows("publication/evidence/commit-review.csv")
    hashes = [row["commit"] for row in rows]

    assert len(hashes) == 719
    assert len(hashes) == len(set(hashes))
    assert set(hashes) == set(commits)


def test_inventory_rows_have_required_headers() -> None:
    file_rows = _rows("publication/evidence/file-review.csv")
    commit_rows = _rows("publication/evidence/commit-review.csv")

    assert file_rows
    assert commit_rows
    assert set(file_rows[0]) == {
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
    }
    assert set(commit_rows[0]) == {
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
    }


def test_review_ledgers_have_no_provisional_markers() -> None:
    file_rows = _rows("publication/evidence/file-review.csv")
    commit_rows = _rows("publication/evidence/commit-review.csv")

    assert "UNREVIEWED" not in {row["classification"] for row in file_rows}
    assert "TRACE_DURING_MIGRATION" not in {row["dependencies"] for row in file_rows}
    assert "TO_CONFIRM_FROM_COMMIT_REVIEW" not in {row["research_era"] for row in file_rows}
    assert "PENDING MANUAL REVIEW" not in {row["supersession_status"] for row in file_rows}
    assert "UNREVIEWED" not in {row["conclusion_status"] for row in commit_rows}
    assert any(
        row["superseding_commit"] == "TRACE_IN_CLAIM_LEDGER" for row in commit_rows
    )


def test_git_inventory_decodes_non_ascii_paths() -> None:
    audit = _audit_module()

    paths = audit.baseline_paths()
    assert "data/lab/raw/protocols/IPSC分化EC-2.docx" in paths
    assert not any(path.startswith('"') for path in paths)


def test_commit_era_rules_preserve_scientific_transitions() -> None:
    audit = _audit_module()

    assert audit.commit_era("2026-08-08", "E4 v2 results") == "E1-E4_FOUNDATION"
    assert audit.commit_era("2026-08-14", "Q52 result") == "BO_VS_DOE_TERMINAL_RULE"
    assert audit.commit_era("2026-08-14", "Lab file index") == "LAB_AND_PUBLISHED_DATA"
    assert audit.commit_era("2026-08-23", "Version C benchmark") == "DESIGN_SPACE_PRE_SPADE"
    assert audit.commit_era("2026-08-25", "SPADE lockbox") == "SPADE_DEVELOPMENT_AND_LOCKBOX"
    assert audit.commit_era("2026-08-27", "real iPSC-EC") == "SPADE_MANUFACTURING_RECOVERY"
    assert audit.commit_era("2026-08-30", "SPADE paper argument") == "SPADE_CONFIRMATION_AND_PAPER"


def test_commit_status_rules_flag_correction_chains_for_manual_review() -> None:
    audit = _audit_module()

    assert audit.commit_status("Merge branch main") == "MERGE_ONLY"
    assert audit.commit_status("Freeze TT gate before data") == "FROZEN_PROTOCOL"
    assert audit.commit_status("RETRACT section 9") == "RETRACTED_OR_CORRECTED"
    assert audit.commit_status("DC RESULT: gate passes") == "SCIENTIFIC_RESULT"
    assert audit.commit_status("feat: add deterministic runner") == "IMPLEMENTATION"


def test_commit_relevance_follows_paper_scope_not_commit_recency() -> None:
    audit = _audit_module()

    assert audit.commit_relevance("E1-E4_FOUNDATION") == "ARCHIVE"
    assert audit.commit_relevance("BO_VS_DOE_TERMINAL_RULE") == "COMPANION"
    assert audit.commit_relevance("LAB_AND_PUBLISHED_DATA") == "SUPPORT"
    assert audit.commit_relevance("DESIGN_SPACE_PRE_SPADE") == "SUPPORT_OR_ARCHIVE"
    assert audit.commit_relevance("SPADE_DEVELOPMENT_AND_LOCKBOX") == "CORE_INFRASTRUCTURE"
    assert audit.commit_relevance("SPADE_MANUFACTURING_RECOVERY") == "CORE_OR_SUPPORT"
    assert audit.commit_relevance("SPADE_CONFIRMATION_AND_PAPER") == "CORE_OR_SUPPORT"


def test_file_rules_keep_core_hill_and_cross_family_evidence_active() -> None:
    audit = _audit_module()

    hill = audit.file_verdict("results/tau-hill.json")
    assert hill["classification"] == "CORE"
    assert hill["destination"] == "research/results/generalization/tau-hill.json"
    assert "five-family" in hill["rationale"]

    runner = audit.file_verdict("scripts/analyse_tau_sweep.py")
    assert runner["classification"] == "INFRASTRUCTURE"
    assert runner["manuscript_claim"] == "C5;C6"


def test_canonical_claim_inputs_are_tracked_in_current_tree() -> None:
    tracked = set(_git("ls-files"))
    expected = {
        *(f"research/results/comparisons/dc-{family}.json" for family in (
            "ackley", "hartmann6", "hill", "levy", "rosenbrock"
        )),
        *(f"research/results/comparisons/lc-{family}.json" for family in (
            "ackley", "hartmann6", "hill", "levy", "rosenbrock"
        )),
        *(f"research/results/comparisons/la-{family}.json" for family in (
            "ackley", "hartmann6", "levy", "rosenbrock"
        )),
        *(f"research/results/generalization/tau-{family}.json" for family in (
            "ackley", "hartmann6", "hill", "levy", "rosenbrock"
        )),
        *(f"research/results/mechanism/tt-{family}.json" for family in (
            "ackley", "hartmann6", "hill", "levy", "rosenbrock"
        )),
        "research/results/real-cell/replay-hall-ogle.log",
    }

    assert expected <= tracked


def test_original_protocol_narratives_are_consolidated_without_deletion() -> None:
    audit = _audit_module()

    for path in audit.CONSOLIDATED_DOCS:
        verdict = audit.file_verdict(path)
        assert verdict["classification"] == "ARCHIVE-SUPERSEDED"
        assert verdict["destination"].startswith("archive/superseded-spade/")


def test_dynamic_runner_prerequisites_remain_active() -> None:
    audit = _audit_module()

    for name in (
        "run_kv_plate2_certificate.py",
        "run_p8_certificate_families.py",
        "run_p2_versionb_gamma.py",
        "run_p6_families.py",
        "run_versionb.py",
    ):
        verdict = audit.file_verdict(f"scripts/{name}")
        assert verdict["classification"] == "INFRASTRUCTURE"
        assert verdict["destination"] == f"software/scripts/{name}"


def test_source_and_tests_follow_the_active_import_graph() -> None:
    audit = _audit_module()

    assert audit.file_verdict("src/boec/vorobev.py")["classification"] == "INFRASTRUCTURE"
    assert audit.file_verdict("src/boec/paper_figures/figure1.py")["classification"] == "ARCHIVE-SUPERSEDED"
    assert audit.file_verdict("tests/test_vorobev.py")["classification"] == "INFRASTRUCTURE"

    assert audit.file_verdict("src/boec/versionc.py")["classification"] == "ARCHIVE-VALID"
    assert audit.file_verdict("tests/test_versionc.py")["classification"] == "ARCHIVE-VALID"


def test_file_rules_preserve_real_data_as_support() -> None:
    audit = _audit_module()

    raw = audit.file_verdict(
        "data/lab/raw/flow/2026-08-06/Exp_20260806_cd31-cd140a/f0.5.fcs"
    )
    assert raw["classification"] == "SUPPORT"
    assert raw["destination"].endswith("f0.5.fcs")

    unrelated = audit.file_verdict(
        "data/lab/raw/flow/2026-07-21/10%FBS-p1.fcs"
    )
    assert unrelated["classification"] == "ARCHIVE-VALID"
    assert "assay_dev" in unrelated["rationale"]

    published = audit.file_verdict("data/published/hall_ogle_2025_stage1.csv")
    assert published["classification"] == "SUPPORT"
    assert published["manuscript_claim"] == "S2;S3"


def test_file_rules_archive_old_narratives_without_deleting_them() -> None:
    audit = _audit_module()

    old = audit.file_verdict("docs/E4-OLD-STUDY.md")
    assert old["classification"] == "ARCHIVE-VALID"
    assert old["destination"].startswith("archive/")

    planning = audit.file_verdict(".planning/STATE.md")
    assert planning["classification"] == "ARCHIVE-SUPERSEDED"
    assert planning["destination"].startswith("archive/")


def test_every_inactive_destination_is_unique_and_inside_archive() -> None:
    rows = _rows("publication/evidence/file-review.csv")
    inactive = [
        row for row in rows
        if row["classification"].startswith("ARCHIVE")
        or row["classification"] == "GENERATED/DISPOSABLE"
    ]
    destinations = [row["destination"] for row in inactive]

    assert len(destinations) == len(set(destinations))
    assert all(destination.startswith("archive/") for destination in destinations)
