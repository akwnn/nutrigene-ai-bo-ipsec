"""KY probe: does hyperparameter mixing break levy/rosenbrock saturation?
Gate frozen in docs/SPADE-HYPERMIX-SPEC.md at 94775ae before this ran."""
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
from boec.hypermix import hyperparameter_ensemble, mixture_draws
P=KV.p8(); p2=P.p2()
FAMS=["levy","rosenbrock","ackley","hartmann6"]
SEEDS=range(int(sys.argv[1]) if len(sys.argv)>1 else 6)
CS=(1.0,2.0,4.0)
grid=sobol_grid(P.DIM,p2.GRID_N,seed=p2.GRID_SEED)
X_sub=sobol_grid(P.DIM,p2.SUBSET_N,seed=p2.GRID_SEED)
tau_by={}
for f in FAMS:
    with torch.no_grad():
        t=P.evaluator_for(f,f,0).truth(grid).reshape(-1).double()
    tau_by[f]={p:float(tau_quantile(t,p)) for p in (0.30,0.10)}
rows=[]; t0=time.time()
for f in FAMS:
    for s in SEEDS:
        ev=P.evaluator_for(f,f,s)
        X,Y,Yvar,_=KV.build(f,"versionb",s)
        with torch.no_grad(): truth=ev.truth(X_sub).reshape(-1).double()
        b=unit_bounds(P.DIM)
        single=build_gp(X,Y,Yvar,b)
        models,w=hyperparameter_ensemble(X,Y,Yvar,b,n_models=5,seed=s)
        with torch.no_grad():
            post=single.posterior(X_sub); mean=post.mean.reshape(-1,1).double()
            cov=post.mvn.covariance_matrix.double()+1e-8*torch.eye(len(X_sub),dtype=torch.double)
            L=torch.linalg.cholesky(cov)
            g=torch.Generator().manual_seed(s)
            z=torch.randn(len(X_sub),P.N_DRAWS,generator=g,dtype=torch.double)
        for c in CS:
            with torch.no_grad(): d_single=(mean+c*L@z).T
            d_mix=mixture_draws(models,w,X_sub,n_draws=P.N_DRAWS,seed=s,inflation=c)
            for label,d in (("single",d_single),("mixture",d_mix)):
                with torch.no_grad():
                    for p,tau in tau_by[f].items():
                        r={"family":f,"seed":s,"model":label,"c":c,"p":p,
                           "n_eff_models":int((w>0).sum())}
                        r.update(p2.vorobev_columns(d,truth,tau,p2.ALPHAS))
                        rows.append(r)
            del d_single,d_mix
        del single,models
    print(f"  {f} done ({time.time()-t0:.0f}s)",flush=True)
json.dump(rows,open("results/probe-hypermix-6seed.json","w"))
print("rows",len(rows))
