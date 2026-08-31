import json, subprocess, sys
from boec.ec_benchmark import *
def test_ec_families_and_replicate_are_deterministic():
    f=registered_ec_families()[0]; c=ECBenchmarkConfig(grid_count=32)
    a=run_ec_replicate(f,config=c,seed=4); b=run_ec_replicate(f,config=c,seed=4)
    assert a==b and a.spade_rounds==3 and a.doe_rounds==5
def test_ec_runner_emits_matched_budget_json(tmp_path):
    out=tmp_path/'ec.json'; subprocess.run([sys.executable,'scripts/run_ec_spade_doe_benchmark.py','--out',str(out),'--replicates','1','--grid-count','16'],check=True)
    d=json.loads(out.read_text()); assert d['schema']=='boec-spade-ec-doe-benchmark-v1'; assert len(d['rows'])==3
    assert all(r['spade_rounds']==3 and r['doe_rounds']==5 for r in d['rows'])
