"""Frozen DC2 runner; default bounds are the fresh confirmatory seeds 32..63.

The campaign is intentionally not run as part of protocol integration.  This
module exposes validation and atomic-writing helpers used by the smoke tests.
"""
from __future__ import annotations

import argparse, hashlib, json, os, subprocess, tempfile
from dataclasses import dataclass
from pathlib import Path

FAMILIES = ("ackley", "hartmann6", "hill", "levy", "rosenbrock")
ARMS = ("doe", "doe_unscreened", "spade")
P_GRID = (0.70, 0.30)
C_GRID = (1.0, 1.5, 2.0, 3.0)

@dataclass(frozen=True)
class Protocol:
    seed_start: int = 32
    seed_stop: int = 64
    families: tuple[str, ...] = FAMILIES
    arms: tuple[str, ...] = ARMS
    p_grid: tuple[float, ...] = P_GRID
    inflation_grid: tuple[float, ...] = C_GRID
    @property
    # A job is one family/seed campaign containing all three arms.
    def expected_jobs(self): return len(self.families) * (self.seed_stop - self.seed_start)
    @property
    def expected_rows(self): return self.expected_jobs * len(self.arms) * len(self.p_grid) * len(self.inflation_grid)

PROTOCOL = Protocol()
ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "SPADE-DOE-CERTIFICATE-CORRECTION-SPEC.md"

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def source_commit() -> str:
    try: return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError): return "UNKNOWN"

def source_dirty() -> bool:
    try: return bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    except (OSError, subprocess.CalledProcessError): return True

def cell_key(row):
    return (row["family"], int(row["seed"]), row["arm"], float(row["p_value"]), float(row["inflation_c"]))

def expected_cells(protocol=PROTOCOL):
    return {(f, s, a, p, c) for f in protocol.families for s in range(protocol.seed_start, protocol.seed_stop)
            for a in protocol.arms for p in protocol.p_grid for c in protocol.inflation_grid}

def validate_rows(rows, protocol=PROTOCOL):
    expected = expected_cells(protocol)
    seen = set()
    if len(rows) != len(expected): raise ValueError(f"row count {len(rows)} != {len(expected)}")
    for row in rows:
        key = cell_key(row)
        if key not in expected: raise ValueError(f"unexpected cell {key}")
        if key in seen: raise ValueError(f"duplicate cell {key}")
        seen.add(key)
        for name in ("regret", "p_value", "inflation_c"):
            value = float(row[name])
            if value != value or value in (float("inf"), float("-inf")): raise ValueError(f"non-finite {name}")
    if seen != expected: raise ValueError(f"missing {len(expected - seen)} cells")
    return True

def validate_artifact(artifact, *, require_complete=True, protocol=PROTOCOL, runner_path=None):
    if require_complete and artifact.get("status") != "COMPLETE": raise ValueError("artifact is not COMPLETE")
    if artifact.get("seed_start") != protocol.seed_start or artifact.get("seed_stop") != protocol.seed_stop:
        raise ValueError("seed bounds do not match frozen protocol")
    if artifact.get("spec_sha256") != sha256(SPEC): raise ValueError("spec digest mismatch")
    if runner_path is not None and artifact.get("runner_sha256") != sha256(Path(runner_path)):
        raise ValueError("runner digest mismatch")
    validate_rows(artifact.get("rows", []), protocol)
    return True

def atomic_write(path: Path, artifact: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as out: json.dump(artifact, out, sort_keys=True, separators=(",", ":")); out.flush(); os.fsync(out.fileno())
        os.replace(tmp, path)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise

def empty_artifact():
    return {"status":"PARTIAL", "source_commit":source_commit(), "source_dirty":source_dirty(),
            "seed_start":PROTOCOL.seed_start, "seed_stop":PROTOCOL.seed_stop,
            "spec_sha256":sha256(SPEC), "runner_sha256":sha256(Path(__file__)), "rows":[]}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--seed-start", type=int, default=32); ap.add_argument("--seed-stop", type=int, default=64)
    ap.add_argument("--out", type=Path, default=ROOT / "results" / "dc2-sweep.json"); ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    if (a.seed_start, a.seed_stop) != (32, 64): raise SystemExit("DC2 is frozen to seeds 32..63")
    artifact = empty_artifact()
    atomic_write(a.out, artifact)
    raise SystemExit("DC2 protocol frozen; no experiment launched. Use a reviewed execution decision to run it.")

if __name__ == "__main__": main()
