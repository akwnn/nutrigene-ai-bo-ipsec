"""The file index: every committed lab file, what it is, and whether it still matches
the checksum it was committed under.

This is the backbone of the "read everything" half of the pipeline. 302 files exist;
12 are optimizer input. The index is what lets the other 290 be *used* -- as gating
references, comparability controls, provenance, and QC -- instead of merely stored.

Modality is derived from the path and extension rather than read from the roles CSV,
so that a file appearing on disk without a roles entry is still classified and still
shows up as an anomaly rather than silently vanishing from the index.
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Literal

Modality = Literal[
    "flow_events",       # .fcs -- the acquisitions themselves
    "flow_sidecar",      # .xit / ExpSummaryForAPI.xml -- CytExpert experiment state
    "microscopy_image",  # .jpeg / .tif
    "microscopy_sidecar",# .metadata -- Leica acquisition JSON
    "plate_reader",      # .xlsx
    "protocol",          # .docx
    "index",             # README.md / MANIFEST.sha256 / the overlay CSVs
    "unknown",
]

#: Files that are the sort itself rather than data being sorted. They are indexed but
#: excluded from role-coverage assertions, because the overlay cannot catalogue itself
#: without a chicken-and-egg problem the first time it is generated.
OVERLAY_FILES = frozenset(
    {
        "BO-PURPOSE.md",
        "bo_file_roles.csv",
        "bo_primary_conditions.csv",
        "bo_morphology_conditions.csv",
        "GATE.md",
    }
)


def classify(rel_path: str) -> Modality:
    """Path -> modality. Extension first, then directory, because ``ExpSummaryForAPI.xml``
    and a Leica ``.metadata`` are both sidecars but belong to different instruments."""
    p = rel_path.lower()
    name = p.rsplit("/", 1)[-1]
    if p.endswith(".fcs"):
        return "flow_events"
    if p.endswith(".xit") or name == "expsummaryforapi.xml":
        return "flow_sidecar"
    if p.endswith(".metadata"):
        return "microscopy_sidecar"
    if p.endswith((".jpeg", ".jpg", ".tif", ".tiff", ".png")):
        return "microscopy_image"
    if p.endswith((".xlsx", ".xls", ".csv")) and p.startswith("plate-reader/"):
        return "plate_reader"
    if p.endswith(".docx"):
        return "protocol"
    if name in {"readme.md", "manifest.sha256"} or name in {f.lower() for f in OVERLAY_FILES}:
        return "index"
    return "unknown"


@dataclass(frozen=True)
class LabFile:
    """One committed file under ``data/lab``.

    ``sha256`` is the value computed now; ``sha256_manifest`` is what ``MANIFEST.sha256``
    recorded at commit time. They are kept as separate fields rather than collapsed to a
    boolean so that a mismatch can name both values in the report.
    """

    path: str
    modality: Modality
    bytes: int
    sha256: str
    role: str | None = None
    why: str | None = None
    sha256_manifest: str | None = None
    bytes_manifest: int | None = None

    @property
    def checksum_ok(self) -> bool | None:
        """``None`` when the manifest has no entry -- absence of evidence, not a failure."""
        if self.sha256_manifest is None:
            return None
        return self.sha256 == self.sha256_manifest

    @property
    def is_overlay(self) -> bool:
        return self.path.rsplit("/", 1)[-1] in OVERLAY_FILES


def walk_lab(lab_root: Path) -> Iterator[Path]:
    """Every regular file under ``lab_root``, excluding the derived tree.

    ``derived/`` is this pipeline's own output. Indexing it would make the index a
    function of its own previous run.
    """
    lab_root = Path(lab_root)
    for p in sorted(lab_root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(lab_root).as_posix()
        if rel.startswith("derived/") or p.name == ".DS_Store":
            continue
        yield p


def sha256_of(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    return h.hexdigest()


def load_roles(roles_csv: Path) -> dict[str, dict[str, str]]:
    """``bo_file_roles.csv`` keyed by path."""
    with Path(roles_csv).open(encoding="utf-8") as fh:
        return {r["path"]: r for r in csv.DictReader(fh)}


def load_manifest(manifest_path: Path) -> dict[str, tuple[str, int]]:
    """``MANIFEST.sha256`` -> ``{path: (sha256, bytes)}``.

    Format is ``<hash><spaces><size><spaces><path>``, and paths contain spaces
    (``well 1.fcs``, ``Leica_2026-08-04 fib 0-5.jpeg``), so the split is bounded to
    two rather than greedy.
    """
    out: dict[str, tuple[str, int]] = {}
    with Path(manifest_path).open(encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            parts = line.split(None, 2)
            if len(parts) != 3:
                continue
            digest, size, path = parts
            out[path] = (digest, int(size))
    return out


def build_file_index(
    lab_root: Path,
    *,
    verify: bool = True,
) -> list[LabFile]:
    """Index every file under ``lab_root``.

    Args:
        lab_root: ``data/lab``.
        verify: compute SHA-256 for each file. ``False`` skips the ~267 MB of hashing
            when the caller only needs paths and roles; ``sha256`` is then ``""``.
    """
    lab_root = Path(lab_root)
    roles = load_roles(lab_root / "bo_file_roles.csv") if (lab_root / "bo_file_roles.csv").exists() else {}
    manifest = load_manifest(lab_root / "MANIFEST.sha256") if (lab_root / "MANIFEST.sha256").exists() else {}

    files: list[LabFile] = []
    for p in walk_lab(lab_root):
        rel = p.relative_to(lab_root).as_posix()
        role_row = roles.get(rel)
        man = manifest.get(rel)
        files.append(
            LabFile(
                path=rel,
                modality=classify(rel),
                bytes=p.stat().st_size,
                sha256=sha256_of(p) if verify else "",
                role=role_row["role"] if role_row else None,
                why=role_row.get("why") if role_row else None,
                sha256_manifest=man[0] if man else None,
                bytes_manifest=man[1] if man else None,
            )
        )
    return files


@dataclass
class ChecksumReport:
    """Outcome of re-hashing the committed tree."""

    checked: int
    ok: int
    mismatched: list[str] = field(default_factory=list)
    unmanifested: list[str] = field(default_factory=list)
    missing_on_disk: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.mismatched and not self.missing_on_disk


def verify_checksums(files: list[LabFile], manifest: dict[str, tuple[str, int]]) -> ChecksumReport:
    """Compare a computed index against ``MANIFEST.sha256``.

    Overlay files are expected to be unmanifested -- they were written after the drop
    was committed -- so they are reported separately rather than as failures.
    """
    rep = ChecksumReport(checked=len(files), ok=0)
    seen = set()
    for f in files:
        seen.add(f.path)
        if f.sha256_manifest is None:
            rep.unmanifested.append(f.path)
            continue
        if f.checksum_ok:
            rep.ok += 1
        else:
            rep.mismatched.append(f.path)
    rep.missing_on_disk = sorted(set(manifest) - seen)
    return rep
