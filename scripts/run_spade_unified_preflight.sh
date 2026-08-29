#!/usr/bin/env bash
# Preflight before any REGISTERED SPADE gate worker.
# Exit 0 only if tree is clean (planning ignored), digests match, safeguards pass.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${ROOT}/.venv/bin/python"

echo "== unified SPADE preflight =="
echo "commit=$(git rev-parse --short HEAD)"

"$PY" - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, "scripts")
import run_spade_development as r
commit, dirty = r.git_state(Path("."))
if dirty:
    print("FAIL: worktree dirty for REGISTERED (non-.planning changes)")
    sys.exit(1)
print("git_clean ok", commit[:12])
assert r.PRODUCT_ARM_ID == "spade-o32-certificate_targeted"
assert len(r.DEVELOPMENT_ARM_IDS) == 5, r.DEVELOPMENT_ARM_IDS
assert r.OPENINGS == (32,)
print("arm_grid ok", r.DEVELOPMENT_ARM_IDS)
PY

"$PY" - <<'PY'
import hashlib, json, yaml
from pathlib import Path
cfg = yaml.safe_load(Path("configs/experiment/spade-joint.yaml").read_text())
p = cfg["protocol"]
digest = hashlib.sha256(
    json.dumps(p, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
).hexdigest()
want = cfg["digests"]["protocol_payload_sha256"]
if digest != want:
    print("FAIL: protocol digest drift", digest, "!=", want)
    raise SystemExit(1)
assert p["development"]["arms_per_family"] == 5
assert p["spade_candidates"]["count"] == 3
assert p["spade_candidates"]["product_arm"] == "spade-o32-certificate_targeted"
assert p["spade_candidates"]["certificate_rho"] == 0.95
assert p["spade_candidates"]["certificate_targeted_batch_schedule"] == [32, 8, 8]
print("protocol ok", digest[:16])
man = json.loads(Path("results/spade-lockbox-generator-manifest.json").read_text())
if man["digests"]["protocol_payload_sha256"] != digest:
    print("FAIL: generator manifest protocol mismatch")
    raise SystemExit(1)
print("generator_manifest ok")
PY

echo "== safeguards =="
"$ROOT/scripts/run_spade_safeguard_tests.sh"
echo "PREFLIGHT PASS"
