#!/usr/bin/env python3
"""Prepare a local PLOS upload bundle, without submitting or claiming approval."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
from zipfile import ZIP_DEFLATED, ZipFile


UPLOADS = {
    "manuscript.docx": "manuscript/SPADE-PLOS-ONE-submission.docx",
    "cover-letter.docx": "manuscript/SPADE-PLOS-ONE-cover-letter.docx",
    **{f"Fig{i}.tiff": f"results/paper-figures/plos/fig{i}.tiff" for i in range(1, 5)},
    "S1_Table.csv": "results/publication-tables/table-spade-prospective-calibration.csv",
    "S2_Table.csv": "results/publication-tables/table-spade-comparison.csv",
    "S3_Table.csv": "results/publication-tables/table-spade-kill-ledger.csv",
}
AUTHOR_ACTIONS = [
    "Confirm author names/order, affiliations, corresponding-author email and ORCID, and CRediT roles.",
    "Approve funding and competing-interest declarations and acknowledgment permissions.",
    "Complete study-wide AI-use disclosure and human scientific/reference/code review.",
    "Approve the disclosed historical replay limitations and the scope of the claims.",
    "Deposit the clean archival release with its approved licenses and insert the DOI.",
    "Confirm related submissions/preprints, prior PLOS interactions, and editor/reviewer preferences.",
    "Obtain every author's submission approval and resolve journal-account and fee arrangements.",
]


def require_hash(path: Path, expected: str) -> None:
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError(f"stale publication input or export: {path}")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_docx(root: Path, name: str, source_name: str, include_figures: bool,
                   cover_letter: bool) -> None:
    output = root / "manuscript" / f"{name}.docx"
    source = root / "manuscript" / f"{source_name}.md"
    manifest = _read_json(output.with_suffix(".docx.manifest.json"))
    require_hash(source, manifest["source_sha256"])
    require_hash(root / "scripts/build_manuscript_docx.py", manifest["builder_sha256"])
    require_hash(output, manifest["output_sha256"])
    if manifest["include_figures"] is not include_figures:
        raise ValueError(f"wrong figure mode: {output}")
    if manifest["cover_letter"] is not cover_letter:
        raise ValueError(f"wrong letter mode: {output}")
    for target, digest in manifest["image_sha256"].items():
        require_hash(source.parent / target, digest)


def validate_inputs(root: Path) -> None:
    """Check derivative provenance; these checks do not resolve scientific replay."""
    figures = root / "results/paper-figures"
    manifest = _read_json(figures / "build-manifest.json")
    if manifest["preset"]["name"] != "plos":
        raise ValueError("stale figure manifest: build the PLOS preset last")
    for section in ("sources", "figure_code_sha256"):
        for name, digest in manifest[section].items():
            require_hash(root / name, digest)
    for exports in manifest["figures"].values():
        for record in exports.values():
            require_hash(figures / record["path"], record["sha256"])
    tables = root / "results/publication-tables"
    manifest = _read_json(tables / "publication-tables.json")
    require_hash(root / "scripts/make_publication_tables.py", manifest["builder_sha256"])
    for name, digest in manifest["source_hashes"].items():
        require_hash(root / "results" / name, digest)
    for name, digest in manifest["output_hashes"].items():
        require_hash(tables / name, digest)
    _validate_docx(root, "SPADE-PLOS-ONE", "SPADE-PLOS-ONE", True, False)
    _validate_docx(root, "SPADE-PLOS-ONE-submission", "SPADE-PLOS-ONE", False, False)
    _validate_docx(root, "SPADE-PLOS-ONE-cover-letter", "SPADE-PLOS-ONE-cover-letter", False, True)


def prepare_bundle(root: Path, output: Path) -> dict:
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"refusing to replace an existing bundle: {output}")
    validate_inputs(root)
    documents = "\n".join((root / "manuscript" / name).read_text() for name in
                          ("SPADE-PLOS-ONE.md", "SPADE-PLOS-ONE-cover-letter.md"))
    manifest = {
        "status": "AUTHOR_REVIEW_REQUIRED",
        "not_a_public_archive": True,
        "scope": "Journal upload files only; not the underlying code/data archival release. No submission performed.",
        "required_author_actions": AUTHOR_ACTIONS,
        "unresolved_manuscript_fields": sorted(set(re.findall(
            r"\[[^\]\n]*(?:CONFIRM|REQUIRED)[^\]\n]*\]", documents))),
        "files": {},
    }
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for name, relative in UPLOADS.items():
            data = (root / relative).read_bytes()
            archive.writestr(name, data)
            manifest["files"][name] = {"source": relative, "sha256": hashlib.sha256(data).hexdigest()}
        archive.writestr("submission-manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as handle:
        handle.write(buffer.getvalue())
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New local ZIP path; existing files are never replaced")
    args = parser.parse_args()
    manifest = prepare_bundle(Path(__file__).resolve().parents[1], args.output)
    print(f"Prepared {len(manifest['files'])} upload files: {args.output}")
    print("AUTHOR_REVIEW_REQUIRED: not submitted; code/data archive and author approvals remain separate.")


if __name__ == "__main__":
    main()
