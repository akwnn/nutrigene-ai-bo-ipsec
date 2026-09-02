import sys, warnings, torch, importlib.util
warnings.filterwarnings("ignore"); torch.set_num_threads(1); sys.path.insert(0,"src")
from boec.surrogate import build_gp
from boec.meanmarg import mean_marginalised_covariance
from boec.topk import certified_topk
from boec.vorobev import conservative_estimate
def load(name,path):
    sp=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m); return m
for label,mod,c_star,lo,hi,unit in [
    ("in-house iPSC-EC (CD31+ %)","scripts/run_real_ipsc_certification.py",0.712,10.0,60.0,"%"),
    ("published Hall & Ogle ECM","scripts/certify_hall_ogle.py",0.526,0.2,2.0,"")]:
    M=load("m",mod); X,Y,Yvar=M.load(); d=X.shape[1]
    b=torch.stack([torch.zeros(d,dtype=torch.double),torch.ones(d,dtype=torch.double)])
    m=build_gp(X,Y,Yvar,b)
    cand=torch.rand(600,d,generator=torch.Generator().manual_seed(0),dtype=torch.double)
    with torch.no_grad(): mean=m.posterior(cand).mean.reshape(-1,1).double()
    cov=mean_marginalised_covariance(m,cand); cov=cov+1e-8*torch.eye(len(cand),dtype=torch.double)
    L=torch.linalg.cholesky(cov)
    z=torch.randn(len(cand),3000,generator=torch.Generator().manual_seed(0),dtype=torch.double)
    with torch.no_grad(): draws=(mean+c_star*L@z).T
    print(f"===== {label}  (c={c_star}) =====")
    print(f"  {'conf':>6}{'whole region':>15}{'finite set':>13}{'gain':>9}{'recipes':>9}")
    for a in (0.50,0.80,0.95,0.99):
        # region frontier
        l1,h1=lo,hi
        for _ in range(16):
            mid=(l1+h1)/2
            if float(conservative_estimate(draws,mid,a).double().mean())>=0.999: l1=mid
            else: h1=mid
        # finite-set frontier: highest tau where at least one recipe is certifiable
        l2,h2=lo,hi
        for _ in range(16):
            mid=(l2+h2)/2
            if len(certified_topk(draws,mid,a))>=1: l2=mid
            else: h2=mid
        n=len(certified_topk(draws,l2,a))
        print(f"  {a:>6.2f}{l1:>14.2f}{unit}{l2:>12.2f}{unit}{l2-l1:>+9.2f}{n:>9}")
    print()
