"""Integrity checks for the paper's actual source and retained evidence."""
from pathlib import Path
import gzip
import hashlib
import json
import re
from zipfile import ZipFile

import pytest

from test_spade_plos_claims import (
    assert_coherent_adverse_doe_claim,
    assert_coherent_c1_regret_claim,
    assert_coherent_c3_volume_claim,
    assert_manuscript_forbids_unqualified_superiority,
    assert_manuscript_pins_c1_regret,
    assert_manuscript_pins_c2_containment_and_adverse_doe,
    assert_manuscript_pins_c3_certified_volume,
    assert_manuscript_retains_required_limits,
    assert_manuscript_states_bounded_operating_region_superiority,
)

ROOT = Path(__file__).resolve().parents[1]


def _assert_current_figure_manifest(root):
    figures = root / "results/paper-figures"
    manifest = json.loads((figures / "build-manifest.json").read_bytes())
    assert manifest["preset"]["name"] == "plos", "stale manifest: rebuild the PLOS preset last"
    for section in ("figure_code_sha256", "sources"):
        assert manifest[section], f"missing {section} provenance"
        for path, expected in manifest[section].items():
            assert hashlib.sha256((root / path).read_bytes()).hexdigest() == expected, f"stale figure input: {path}"
    assert manifest["figures"], "missing figure exports"
    for records in manifest["figures"].values():
        for record in records.values():
            path = figures / record["path"]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == record["sha256"], f"stale figure export: {path}"


def test_figure_manifest_matches_current_sources_and_exports():
    _assert_current_figure_manifest(ROOT)


@pytest.mark.parametrize("changed", ["source.py", "evidence.json", "plos/fig1.png"])
def test_figure_freshness_check_rejects_changed_bytes(tmp_path, changed):
    figures = tmp_path / "results/paper-figures"
    (figures / "plos").mkdir(parents=True)
    (tmp_path / "source.py").write_text("source")
    (tmp_path / "evidence.json").write_text("evidence")
    (figures / "plos/fig1.png").write_bytes(b"figure")
    digest = lambda value: hashlib.sha256(value).hexdigest()
    manifest = {
        "preset": {"name": "plos"},
        "figure_code_sha256": {"source.py": digest(b"source")},
        "sources": {"evidence.json": digest(b"evidence")},
        "figures": {"fig1": {"png": {"path": "plos/fig1.png", "sha256": digest(b"figure")}}},
    }
    (figures / "build-manifest.json").write_text(json.dumps(manifest))
    _assert_current_figure_manifest(tmp_path)
    target = figures / changed if changed.startswith("plos/") else tmp_path / changed
    target.write_bytes(b"changed")
    with pytest.raises(AssertionError, match="stale"):
        _assert_current_figure_manifest(tmp_path)


def test_reading_copy_embeds_the_current_four_plos_images():
    with ZipFile(ROOT / "manuscript/SPADE-PLOS-ONE.docx") as archive:
        embedded = {hashlib.sha256(archive.read(name)).hexdigest()
                    for name in archive.namelist() if name.startswith("word/media/")}
    current = {hashlib.sha256((ROOT / f"results/paper-figures/plos/fig{i}.png").read_bytes()).hexdigest()
               for i in range(1, 5)}
    assert embedded == current, "stale manuscript images; rebuild the reading DOCX"


def test_paper_reports_the_implemented_map_and_certificate_estimands():
    text = (ROOT / "manuscript/SPADE-PLOS-ONE.md").read_text()
    assert "0.50 cutoff" in text
    assert "posterior self-consistency" in text
    assert "not empirical containment against the oracle" in text
    assert "### Artificial intelligence assistance" in text
    assert "## Funding statement" not in text
    assert "## Competing interests" not in text


def test_paper_identifies_the_shared_gp_in_figure2_rule_p():
    text = (ROOT / "manuscript/SPADE-PLOS-ONE.md").read_text()
    assert "The retrospective terminal-rule comparison also used a common GP" in text
    assert "twenty restarts and 4,096 raw starts" in text
    assert "retained the original arm-specific model recommendations" not in text


def test_paper_citations_follow_first_appearance_and_resolve():
    text = (ROOT / "manuscript/SPADE-PLOS-ONE.md").read_text()
    body, references = text.split("## References\n", 1)
    references = references.split("## Supporting information captions", 1)[0]
    body = re.sub(r"\$[^$]*\$", "", body)
    numbers = [int(n) for n in re.findall(r"^(\d+)\. ", references, flags=re.M)]
    assert numbers == list(range(1, 21))
    first_seen = []
    for group in re.findall(r"\[([0-9, –-]+)\]", body):
        for piece in group.split(","):
            bounds = re.split(r"[–-]", piece.strip())
            values = range(int(bounds[0]), int(bounds[-1]) + 1)
            for number in values:
                assert number in numbers
                if number not in first_seen:
                    first_seen.append(number)
    assert first_seen == numbers


def test_paper_retains_comparator_and_novelty_boundaries():
    text = (ROOT / "manuscript/SPADE-PLOS-ONE.md").read_text()
    assert "TruVaR" in text
    assert "**Table 5." in text
    assert "only 0.0063 above primary SPADE" not in text
    assert_manuscript_states_bounded_operating_region_superiority(text)
    assert_manuscript_pins_c1_regret(text)
    assert_manuscript_pins_c3_certified_volume(text)
    assert_manuscript_pins_c2_containment_and_adverse_doe(text)
    assert_manuscript_forbids_unqualified_superiority(text)
    abstract = text.split("## Abstract\n", 1)[1].split("## Introduction", 1)[0]
    assert len(abstract.split()) <= 250
    assert "0.0016" not in abstract
    assert_coherent_c1_regret_claim(abstract)
    assert_coherent_c3_volume_claim(abstract)
    assert_coherent_adverse_doe_claim(abstract)
    assert re.search(r"no detectable (?:regret )?difference", abstract, flags=re.IGNORECASE)
    assert re.search(r"\bn\s*=\s*320\b", abstract)


def test_manuscript_uses_current_plos_figures_and_no_phantom_supplements():
    text = (ROOT / "manuscript/SPADE-PLOS-ONE.md").read_text()
    targets = re.findall(r"!\[[^]]*\]\(([^)]+)\)", text)
    assert len(targets) == 4
    assert [Path(target).name for target in targets] == [
        "fig1.png",
        "fig2.png",
        "fig3.png",
        "fig4.png",
    ]
    assert re.findall(r"\bFig\s+([1-4])\.", text) == ["1", "2", "3", "4"]
    for target in targets:
        assert "/plos/" in target
        assert (ROOT / "manuscript" / target).is_file()
    assert "**S1 Fig." not in text
    assert "Internal validity completed" not in text
    assert_manuscript_retains_required_limits(text)


def test_manuscript_captions_match_retained_plos_plots():
    text = (ROOT / "manuscript/SPADE-PLOS-ONE.md").read_text()

    def caption(number: str) -> str:
        match = re.search(
            rf"\*\*Fig {number}\.\s.*?(?=\n\n|\Z)",
            text,
            flags=re.S,
        )
        assert match, f"missing Fig {number} caption"
        return match.group(0)

    def supporting_table(number: str) -> str:
        match = re.search(
            rf"\*\*S{number} Table\.\*\*\s.*?(?=\n\n|\Z)",
            text,
            flags=re.S,
        )
        assert match, f"missing S{number} Table caption"
        return " ".join(match.group(0).split())

    fig1, fig2, fig3, fig4 = caption("1"), caption("2"), caption("3"), caption("4")
    assert "Matched-round certified-volume comparisons" not in text
    assert "shaded practical-effect band" not in text
    abstract = text.split("## Abstract\n", 1)[1].split("## Introduction", 1)[0]
    results = text.split("## Results\n", 1)[1].split("## Discussion", 1)[0]
    headlines = abstract + results
    assert "Plate-2 gain" not in headlines
    assert "seven-condition comparison" not in headlines.lower()
    assert re.search(r"Benchmark decisions and estimands", fig1)
    assert re.search(r"Rule A versus Rule P", fig2)
    assert re.search(r"\$n=50\$", fig2)
    assert "shaded band" not in fig2
    assert re.search(r"map error versus Rule-P", fig3)
    assert re.search(r"Hartmann", fig3)
    assert re.search(r"shaded band", fig3)
    assert re.search(r"not matched-round certified volume", fig3)
    assert re.search(r"posterior self-consistency", fig4)
    s1, s2, s3 = supporting_table("1"), supporting_table("2"), supporting_table("3")
    assert "prospective calibration" in s1
    assert "25 Hill landscape instances" in s1
    assert "latent acceptability labels" in s1
    assert "0.50 cutoff" in s1
    assert "common GP" in s1
    assert "12 available target-condition arms" in s1
    assert "40-well reference" in s1
    assert "seven-condition comparison" not in s1.lower()
    assert "kill-ledger" not in s1
    assert "seven-condition comparison" in s2.lower()
    assert "six matched-budget strategies" in s2
    assert "100 campaigns" in s2
    assert "not the C3 matched-round certified-volume comparison" in s2
    assert "prospective calibration" not in s2
    assert "kill-ledger" not in s2
    assert "claim decisions" in s3
    assert "kill-ledger" in s3
    assert re.search(r"Original statuses.*corrected interpretation", s3, flags=re.S)
    assert "Certificate checks do not establish empirical validity" in s3
    assert "prospective calibration" not in s3
    assert "seven-condition comparison" not in s3.lower()


def test_development_artifact_bundle_matches_its_original_selection_hashes():
    results = ROOT / "results"
    selected = json.loads((results / "spade-selected-protocol.json").read_bytes())
    assert selected["status"] == "NO_SELECTION"
    assert selected["selected_candidate"] is None
    assert hashlib.sha256((results / selected["analysis_file"]).read_bytes()).hexdigest() == selected["analysis_sha256"]
    count = 0
    for artifact in selected["development_artifacts"]:
        for kind in ("raw", "manifest", "resume"):
            path = results / artifact[f"{kind}_file"]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact[f"{kind}_sha256"]
        with gzip.open(results / artifact["raw_file"], "rt") as stream:
            rows = [json.loads(line) for line in stream]
        assert len(rows) == 550
        count += len(rows)
    assert count == 2750


def test_development_table_ranges_reconcile_to_all_nine_candidates():
    analysis = json.loads((ROOT / "results/spade-development-analysis.json").read_bytes())
    text = (ROOT / "manuscript/SPADE-PLOS-ONE.md").read_text()
    candidates = list(analysis["candidates"].values())
    assert len(candidates) == 9
    for family in ("hill", "ackley", "hartmann6", "levy", "rosenbrock"):
        rows = [candidate["families"][family] for candidate in candidates]
        counts = [row["answer_count"] for row in rows]
        rates = [row["empirical_containment"] for row in rows]
        count_range = str(min(counts)) if min(counts) == max(counts) else f"{min(counts)}–{max(counts)}"
        assert f"| {family.capitalize()} | {count_range} | {min(rates):.3f}–{max(rates):.3f} |" in text
