"""Reassemble `results/p6-families.json` from its shards.

The single file is **103.8 MB** and GitHub refuses anything over 100 MB, so the 96,000 rows
are stored as eight `(family, dim)` shards plus a metadata file carrying `provenance`,
`config`, `cell_separation` and `gate_failures`.

`load()` returns exactly the dict the single file held. Verified at split time: the row
sets are identical and the non-row payload hashes equal.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "results" / "p6-families.meta.json"
SHARDS = ROOT / "results" / "p6-families"


def load() -> dict:
    """The full `p6-families.json` payload, reassembled."""
    meta = json.loads(META.read_text())
    rows = []
    for name in sorted(meta["shards"]):
        rows.extend(json.loads((SHARDS / name).read_text()))
    if len(rows) != meta["n_rows"]:
        raise ValueError(f"expected {meta['n_rows']} rows, reassembled {len(rows)}")
    payload = {k: v for k, v in meta.items()
               if k not in ("shards", "n_rows", "shard_dir", "note")}
    payload["rows"] = rows
    return payload


if __name__ == "__main__":
    d = load()
    print(f"{len(d['rows'])} rows · keys {sorted(d)} · "
          f"gate_failures {len(d.get('gate_failures', []))}")
