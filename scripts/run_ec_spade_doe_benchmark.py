#!/usr/bin/env python3
"""Run the registered matched-budget EC differentiation benchmark."""
import argparse, json
from pathlib import Path
from boec.ec_benchmark import ECBenchmarkConfig, aggregate_ec, registered_ec_families, run_ec_replicate
def main():
    p=argparse.ArgumentParser(); p.add_argument('--out',required=True,type=Path); p.add_argument('--replicates',type=int,default=25); p.add_argument('--grid-count',type=int,default=2048)
    a=p.parse_args(); cfg=ECBenchmarkConfig(replicates=a.replicates,grid_count=a.grid_count)
    rows=[]
    for fam in registered_ec_families(cfg.dimension):
        rows += [run_ec_replicate(fam,config=cfg,seed=i) for i in range(a.replicates)]
    out={'schema':'boec-spade-ec-doe-benchmark-v1','protocol_digest':cfg.digest,'protocol':cfg.__dict__,'families':[f.name for f in registered_ec_families(cfg.dimension)],'rows':[r.as_dict() for r in rows],'aggregate':{f.name:aggregate_ec([r for r in rows if r.family==f.name]) for f in registered_ec_families(cfg.dimension)}}
    a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(out,sort_keys=True,indent=2)+'\n')
if __name__=='__main__': main()
