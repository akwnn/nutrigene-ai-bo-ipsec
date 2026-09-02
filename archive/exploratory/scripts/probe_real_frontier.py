import sys, warnings, torch
warnings.filterwarnings("ignore"); torch.set_num_threads(1); sys.path.insert(0,"src")
import importlib.util
spec=importlib.util.spec_from_file_location("r","scripts/run_real_ipsc_certification.py")
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
from boec.surrogate import build_gp
from boec.meanmarg import mean_marginalised_covariance
from boec.vorobev import conservative_estimate
X,Y,Yvar=m.load()
b=torch.tensor([[0.,0.],[1.,1.]],dtype=torch.double)
gp=build_gp(X,Y,Yvar,b)
g=torch.linspace(0,1,101,dtype=torch.double)
cand=torch.cartesian_prod(torch.tensor([0.,1.],dtype=torch.double),g)
with torch.no_grad():
    post=gp.posterior(cand); mean=post.mean.reshape(-1,1)
    cov=mean_marginalised_covariance(gp,cand)+1e-8*torch.eye(len(cand),dtype=torch.double)
    L=torch.linalg.cholesky(cov)
    gen=torch.Generator().manual_seed(0)
    z=torch.randn(len(cand),4000,generator=gen,dtype=torch.double)
print("HIGHEST CD31+ spec certifiable over the WHOLE FN/VTN x 0.5-20 ug/mL box")
print(f"{'c':>5}{'a=0.50':>9}{'a=0.80':>9}{'a=0.95':>9}{'a=0.99':>9}", flush=True)
for c in (1.0,1.5,2.0,3.0):
    with torch.no_grad(): draws=(mean + c*L@z).T
    row=f"{c:>5}"
    for a in (0.5,0.8,0.95,0.99):
        lo,hi=10.0,50.0
        for _ in range(24):                      # bisect on the certifiable frontier
            mid=(lo+hi)/2
            ce=conservative_estimate(draws,mid,a)
            if float(ce.double().mean())>=0.999: lo=mid
            else: hi=mid
        row+=f"{(f'{lo:.1f}%' if lo>10.05 else 'none'):>9}"
    print(row, flush=True)
