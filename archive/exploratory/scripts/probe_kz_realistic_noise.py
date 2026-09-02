"""KZ probe: does plate-2 targeting survive real cell-manufacturing noise?
Gate frozen in docs/SPADE-REALISTIC-NOISE-SPEC.md at a3b8647 before this ran."""
import sys, importlib.util, warnings, json, torch, time
warnings.filterwarnings("ignore"); torch.set_num_threads(1); sys.path.insert(0,"src")
def _mod(n,f):
    s=importlib.util.spec_from_file_location(n,"scripts/"+f)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
KV=_mod("kv","run_kv_plate2_certificate.py")
from boec.designspace import tau_quantile
from boec.norms import sobol_grid
from boec.replay import unit_bounds
from boec.surrogate import build_gp
P=KV.p8(); p2=P.p2()
FAMS=["ackley","hartmann6","levy","rosenbrock"]
SEEDS=range(int(sys.argv[1]) if len(sys.argv)>1 else 12)
SIGMAS=(0.25,0.68)           # committed control, and Hall/Ogle's median CV
ARMS=("versionb","versionb_random")
CS=(1.0,1.5,2.0)
grid=sobol_grid(P.DIM,p2.GRID_N,seed=p2.GRID_SEED)
X_sub=sobol_grid(P.DIM,p2.SUBSET_N,seed=p2.GRID_SEED)
rows=[]; t0=time.time()
for sig in SIGMAS:
    P.SIGMA=sig                                   # rebind, as run_ku did for TQ.FAMILIES
    tau_by={}
    for f in FAMS:
        with torch.no_grad():
            t=P.evaluator_for(f,f,0).truth(grid).reshape(-1).double()
        tau_by[f]={p:float(tau_quantile(t,p)) for p in (0.30,0.10)}
    for f in FAMS:
        for s in SEEDS:
            ev=P.evaluator_for(f,f,s)
            with torch.no_grad(): truth=ev.truth(X_sub).reshape(-1).double()
            for arm in ARMS:
                X,Y,Yvar,_=KV.build(f,arm,s)
                m=build_gp(X,Y,Yvar,unit_bounds(P.DIM))
                with torch.no_grad():
                    post=m.posterior(X_sub); mean=post.mean.reshape(-1,1).double()
                    cov=post.mvn.covariance_matrix.double()+1e-8*torch.eye(len(X_sub),dtype=torch.double)
                    L=torch.linalg.cholesky(cov)
                    g=torch.Generator().manual_seed(s)
                    z=torch.randn(len(X_sub),P.N_DRAWS,generator=g,dtype=torch.double)
                    for c in CS:
                        draws=(mean+c*L@z).T
                        for p,tau in tau_by[f].items():
                            r={"family":f,"seed":s,"arm":arm,"sigma":sig,"c":c,"p":p}
                            r.update(p2.vorobev_columns(draws,truth,tau,p2.ALPHAS))
                            rows.append(r)
                        del draws
                del m
        print(f"  sigma={sig} {f} done ({time.time()-t0:.0f}s)",flush=True)
json.dump(rows,open("results/probe-kz-realistic-noise.json","w"))
print("rows",len(rows))
