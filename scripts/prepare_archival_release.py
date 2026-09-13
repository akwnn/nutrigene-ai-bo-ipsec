"""Prepare a hash-verified LOCAL DRAFT, never upload or grant a license.

Only the publication evidence allowlist and synthetic research code are selected.
This is not a Git backup, full-history replay environment, or journal upload bundle.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ORACLES = "data/oracles/biphasic-hill-v8+82f6db7c8f77"
REQUIRED_FILES = tuple(sorted({
    "LICENSE", "LICENSE-CONTENT.md",
    ".planning/debug/replay-claim-impact.md",
    "README.md", "pyproject.toml", "requirements.txt", "requirements-publication.txt",
    "docs/FINDINGS-SPADE-FINAL.md", "docs/SPADE-FINAL-SPEC.md",
    "docs/superpowers/specs/2026-08-25-spade-joint-protocol-design.md",
    "docs/superpowers/specs/2026-08-25-spade-lockbox-power-design.md",
    ".github/workflows/spade-distributed.yml",
    "results/paper-figures/build-manifest.json",
    "results/paper-figures/plos/build-manifest.json",
    "results/publication-tables/publication-tables.json",
    "results/spade-selected-protocol.json", "results/spade-development-analysis.json",
    "results/spade-lockbox-generator-manifest.json",
    *[f"configs/experiment/{name}.yaml" for name in ("e2", "e4", "spade-joint")],
    *[f"manuscript/SPADE-PLOS-ONE{suffix}" for suffix in (
        ".md", ".docx", ".docx.manifest.json", "-submission.docx",
        "-submission.docx.manifest.json", "-cover-letter.md", "-cover-letter.docx",
        "-cover-letter.docx.manifest.json")],
    *[f"results/paper-figures/plos/fig{i}.{ext}" for i in range(1, 5)
      for ext in ("pdf", "svg", "png", "tiff", "data.json", "alt.txt", "caption.txt", "description.txt")],
    *[f"results/publication-tables/table-spade-{name}.{ext}"
      for name in ("comparison", "kill-ledger", "prospective-calibration") for ext in ("csv", "md")],
    *[f"results/final-spade-{name}.json" for name in (
        "c1", "c2", "c3", "c4", "s1", "s2", "s3", "certificate", "feasibility",
        "kill-ledger", "manifest", "regret-pareto",
        "primary-C1", "primary-C2", "primary-C3", "primary-C4", "primary-S1", "primary-S2", "primary-S3")],
    *[f"results/{name}.json" for name in (
        "fix1-analysis", "fix1-terminal-rule", "step0-oracle-best", "p7-murphy",
        "p8-certificate-families", "p8-predictions", "e2-grid", "q42-families",
        "q52-budget-to-target", "q59-hartmann-no-screen", "k6-designspace-spread",
        "d20-rescore", "k6-designspace", "k6b-conservative-spread", "k1-replay-gate", "versionb")],
    *[f"results/spade-development-{family}-000-050.jsonl.gz{suffix}"
      for family in ("hill", "ackley", "hartmann6", "levy", "rosenbrock")
      for suffix in ("", ".manifest.json", ".resume.json", ".sha256")],
    *[f"{ORACLES}/{name}" for name in (
        "instances_d6.parquet", "instances_d8.parquet", "audit_d6.json", "audit_d8.json")],
}))
EXCLUDED_TERMS = ("lab", "published", "hall_ogle", "digitize")
TEXT_SUFFIXES = {".py", ".md", ".json", ".txt", ".yaml", ".yml", ".toml", ".svg", ".csv", ".mplstyle"}


def validate_path(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if (not name or "\\" in name or path.is_absolute() or name != path.as_posix()
            or any(part in (".", "..") for part in path.parts)):
        raise ValueError(f"unsafe archive path: {name}")
    if name in REQUIRED_FILES:
        return path
    if any(part.startswith(".") or part == "__pycache__" or part.endswith(".egg-info") for part in path.parts):
        raise ValueError(f"excluded runtime/private path: {name}")
    if any(re.search(rf"(^|[/_]){term}([/_.]|$)", name.lower()) for term in EXCLUDED_TERMS):
        raise ValueError(f"excluded non-synthetic material: {name}")
    source = name.startswith(("src/boec/", "scripts/", "tests/")) and path.suffix in (".py", ".mplstyle")
    oracle = name.startswith(ORACLES + "/sidecars/") and path.suffix == ".json"
    if not (source or oracle):
        raise ValueError(f"not in publication archive allowlist: {name}")
    return path


def checked_source(root: Path, name: str) -> Path:
    path = validate_path(name)
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"symlink forbidden: {name}")
    if not current.is_file():
        raise FileNotFoundError(name)
    return current


def select_files(root: Path) -> list[str]:
    selected = set(REQUIRED_FILES)
    for name in selected:
        checked_source(root, name)
    for directory, pattern in (("src/boec", "*.py"), ("src/boec", "*.mplstyle"),
                               ("scripts", "*.py"), ("tests", "*.py"), (ORACLES + "/sidecars", "*.json")):
        for path in (root / directory).rglob(pattern):
            name = path.relative_to(root).as_posix()
            try:
                validate_path(name)
            except ValueError:
                continue
            checked_source(root, name)
            selected.add(name)
    return sorted(selected)


def _git_provenance(root: Path) -> dict:
    def git(*args):
        try:
            return subprocess.run(["git", "-C", str(root), *args], check=True,
                                  capture_output=True, text=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return None
    head = git("rev-parse", "HEAD")
    status = git("status", "--porcelain", "--untracked-files=all")
    return {"head": head, "working_tree_dirty": bool(status) if status is not None else None,
            "snapshot_basis": "live allowlisted bytes, including uncommitted and untracked files; per-file hashes govern"}


def _license_metadata(payload: dict[str, bytes]) -> dict:
    names = {"LICENSE", "LICENSE-CONTENT.md"}
    included = names.intersection(payload)
    if not included:
        return {"granted": False, "decisions_required": [
            "Include both approved license declarations before distributing this snapshot."]}
    if included != names:
        raise ValueError("incomplete license declarations")
    holders = ["Alana Wai Han Kwan", "Joseph Yung"]
    markers = {
        "LICENSE": ["MIT License", "Permission is hereby granted, free of charge",
                    'THE SOFTWARE IS PROVIDED "AS IS"', *holders],
        "LICENSE-CONTENT.md": ["https://creativecommons.org/licenses/by/4.0/",
                               "CC BY 4.0", *holders],
    }
    for name, required in markers.items():
        content = payload[name].decode("utf-8")
        if any(marker not in content for marker in required):
            raise ValueError(f"unrecognized license declaration: {name}")
    return {"granted": True, "software": "MIT", "research_materials": "CC-BY-4.0",
            "copyright_holders": holders, "decisions_required": [],
            "scope_notice": "LICENSE-CONTENT.md; third-party and unreleased private materials are excluded."}


def write_archive(root: Path, output: Path, paths: list[str]) -> dict:
    if output.exists():
        raise FileExistsError(output)
    root = root.resolve()
    names = sorted(set(paths))
    payload = {name: checked_source(root, name).read_bytes() for name in names}
    manifest = {
        "schema": "spade-local-archive-v1",
        "status": "LOCAL_DRAFT_NOT_FOR_PUBLIC_DEPOSIT",
        "scientific_state": {"development": "NO_SELECTION", "lockbox": "FROZEN_UNOPENED"},
        "license": _license_metadata(payload),
        "provenance": _git_provenance(root),
        "scope": "Publication evidence and non-lab scientific source snapshot, not a complete historical repository.",
        "excluded": ["private data/lab and lab-specific code", "external/published third-party data",
                     "unselected exploratory results/docs", "Git history and worktrees", "environments, caches and fonts",
                     "journal upload ZIPs", "lockbox outcomes and power artifacts"],
        "limitations": [
            "Eight historical replay gates remain failing; exact tests and reference bytes are not relaxed or replaced.",
            "The historical replay audit records prior observations, not a fresh campaign execution.",
            "A later explicit acquisition sampler seed adds divergence from legacy RNG behavior; legacy behavior alone does not recover historical adaptive references.",
            "Full-suite historical Git-blob tests cannot run from this Git-free snapshot; other historical tests may require omitted exploratory evidence.",
            "Some legacy tests invoke .venv/bin/python. Publication figure layout needs a legitimately installed Arial font.",
            "Figure rebuild Git/time metadata can differ outside the original working tree.",
            "Author details and declarations are deferred; this archive is not approval to submit or upload.",
            "Preexisting machine paths are flagged by filename only and preserved as provenance; review before public deposit.",
        ],
        "verification_commands": [
            "python scripts/validate_final_spade_release.py",
            "python -m pytest -q tests/test_publication_bundle.py tests/test_manuscript_docx.py tests/test_paper_figure_builders.py tests/test_paper_figure_layout.py tests/test_publication_tables.py tests/test_submission_package.py",
        ],
        "preexisting_local_path_files": [name for name, data in payload.items()
            if Path(name).suffix in TEXT_SUFFIXES and re.search(rb"/(?:Users|home)/[^/\s]+/", data)],
        "files": {name: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                  for name, data in payload.items()},
    }
    # Do not infer a scientific state if an included governing artifact contradicts it.
    for name, expected in (("results/spade-selected-protocol.json", "NO_SELECTION"),
                           ("results/spade-lockbox-generator-manifest.json", "FROZEN_UNOPENED")):
        if name in payload and json.loads(payload[name])["status"] != expected:
            raise ValueError(f"scientific state changed: {name}")
    payload["archive-manifest.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "x", compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for name, data in sorted(payload.items()):
            info = ZipInfo(name, date_time=(2026, 9, 11, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, data)
    return manifest


def verify_and_extract(archive_path: Path, destination: Path) -> dict:
    if destination.exists():
        raise FileExistsError(destination)
    with ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("duplicate archive members")
        manifest = json.loads(archive.read("archive-manifest.json"))
        if set(names) != set(manifest["files"]) | {"archive-manifest.json"}:
            raise ValueError("archive inventory mismatch")
        for name, record in manifest["files"].items():
            validate_path(name)
            info = archive.getinfo(name)
            if stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError(f"symlink forbidden: {name}")
            data = archive.read(name)
            if hashlib.sha256(data).hexdigest() != record["sha256"] or len(data) != record["bytes"]:
                raise ValueError(f"archive hash/size mismatch: {name}")
        destination.mkdir(parents=True)
        for name in names:
            path = destination / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(archive.read(name))
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    manifest = write_archive(root, args.output, select_files(root))
    print(json.dumps({"archive": str(args.output), "files": len(manifest["files"]),
                      "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
                      "status": manifest["status"],
                      "preexisting_local_path_files": manifest["preexisting_local_path_files"]}, indent=2))


if __name__ == "__main__":
    main()
