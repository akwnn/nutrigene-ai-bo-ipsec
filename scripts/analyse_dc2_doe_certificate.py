"""Fail-closed adjudicator for a completed, provenance-valid DC2 artifact."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from run_dc2_doe_certificate import PROTOCOL, validate_artifact

def analyse(path: Path):
    artifact = json.loads(path.read_text())
    validate_artifact(artifact, runner_path=Path(__file__).with_name("run_dc2_doe_certificate.py"))
    print(f"VALID DC2 artifact: {len(artifact['rows'])} rows; seeds {PROTOCOL.seed_start}..{PROTOCOL.seed_stop-1}")
    return artifact

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("artifact", type=Path); a = ap.parse_args()
    try: analyse(a.artifact)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr); return 2
    return 0

if __name__ == "__main__": sys.exit(main())
