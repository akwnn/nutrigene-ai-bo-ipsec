"""Matched-budget synthetic EC-differentiation SPADE versus DOE benchmark.

The benchmark is deliberately model-only: EC identity/differentiation score is a
bounded response over six formulation/process factors.  Both arms receive the
same 48 wells; SPADE uses a 32-well Sobol opening followed by two adaptive
8-well batches, while DOE uses one 48-well Sobol design.  Truth is used only for
scoring, never for campaign decisions.
"""
from __future__ import annotations
import hashlib, json
from dataclasses import dataclass
import torch
from torch import Tensor
from boec.seedbook import derive_seed
from boec.surrogate import build_gp

@dataclass(frozen=True)
class ECFamily:
    name: str
    centers: tuple[tuple[float,...], ...]
    widths: tuple[float,...]
    threshold: float = .55
    dimension: int = 6

@dataclass(frozen=True)
class ECBenchmarkConfig:
    dimension: int = 6; budget: int = 48; opening: int = 32; batch: int = 8
    grid_count: int = 2048; replicates: int = 25; sigma: float = .03
    threshold: float = .55
    @property
    def digest(self):
        return hashlib.sha256(json.dumps(self.__dict__,sort_keys=True).encode()).hexdigest()

@dataclass(frozen=True)
class ECRow:
    family: str; seed: int; spade_regret: float; doe_regret: float
    spade_region_iou: float; doe_region_iou: float; spade_rounds: int; doe_rounds: int
    def as_dict(self): return self.__dict__.copy()

def registered_ec_families(dimension=6):
    return (ECFamily('ec_broad',((.28,.62,.42),), (7.,)),
            ECFamily('ec_narrow',((.68,.35,.55),), (18.,)),
            ECFamily('ec_multimodal',((.28,.62,.42),(.72,.35,.58)), (12.,10.)))

def evaluate_ec(family: ECFamily, X: Tensor) -> Tensor:
    a=X[:,:3].double(); out=torch.zeros(len(X),dtype=torch.double)
    for c,w in zip(family.centers,family.widths):
        cc=torch.tensor(c,dtype=torch.double,device=X.device)
        out=torch.maximum(out,torch.exp(-w*(a-cc).square().sum(1)))
    return out

def _fit_predict(X,Y,grid):
    b=torch.stack((torch.zeros(X.shape[1]),torch.ones(X.shape[1])))
    m=build_gp(X,Y[:,None],torch.full((len(X),1),1e-4,dtype=torch.double),b,fit=True,fit_restarts=1)
    return m.posterior(grid).mean.squeeze(-1)

def run_ec_replicate(family, *, config=ECBenchmarkConfig(), seed=0):
    sob=torch.quasirandom.SobolEngine(config.dimension,scramble=True,seed=derive_seed(seed,'ec-grid')%(2**32))
    pts=sob.draw(config.budget+config.grid_count).double(); grid=pts[config.budget:]
    truth=evaluate_ec(family,grid); mask=truth>=config.threshold; optimum=float(truth.max())
    opening=pts[:config.opening]; y=evaluate_ec(family,opening)+config.sigma*torch.randn(len(opening),generator=torch.Generator().manual_seed(derive_seed(seed,'noise')))
    adaptive=[]; rounds=1
    for r in range(2):
        cand=pts[config.budget//2 + r*0:config.budget] if False else torch.quasirandom.SobolEngine(config.dimension,scramble=True,seed=derive_seed(seed,'cand',r)%(2**32)).draw(512).double()
        pred=_fit_predict(opening,y,cand); chosen=cand[torch.topk(pred,config.batch).indices]; adaptive.append(chosen)
        opening=torch.cat((opening,chosen)); y=torch.cat((y,evaluate_ec(family,chosen)+config.sigma*torch.randn(config.batch,generator=torch.Generator().manual_seed(derive_seed(seed,'noise',r+1)))))
        rounds+=1
    # Sequential DOE/RSM comparator: 32-well opening plus four adaptive
    # four-well confirmation batches, using exactly the same 48-well budget.
    doe=pts[:config.opening].clone(); dy=evaluate_ec(family,doe)+config.sigma*torch.randn(len(doe),generator=torch.Generator().manual_seed(derive_seed(seed,'doe-noise')))
    for r in range(4):
        cand=torch.quasirandom.SobolEngine(config.dimension,scramble=True,seed=derive_seed(seed,'doe-cand',r)%(2**32)).draw(512).double()
        pred=_fit_predict(doe,dy,cand); chosen=cand[torch.topk(pred,config.batch//2).indices]
        doe=torch.cat((doe,chosen)); dy=torch.cat((dy,evaluate_ec(family,chosen)+config.sigma*torch.randn(len(chosen),generator=torch.Generator().manual_seed(derive_seed(seed,'doe-noise',r+1)))))
    sp_pred=_fit_predict(opening,y,grid); do_pred=_fit_predict(doe,dy,grid)
    sp_mask=sp_pred>=config.threshold; do_mask=do_pred>=config.threshold
    def iou(x): return float((x&mask).sum()/((x|mask).sum().clamp_min(1)))
    return ECRow(family.name,seed,optimum-float(sp_pred.max()),optimum-float(do_pred.max()),iou(sp_mask),iou(do_mask),rounds,5)

def aggregate_ec(rows):
    if not rows: raise ValueError('rows must be non-empty')
    def mean(k): return float(sum(getattr(r,k) for r in rows)/len(rows))
    return {'family':rows[0].family,'replicate_count':len(rows),'spade_regret_mean':mean('spade_regret'),'doe_regret_mean':mean('doe_regret'),'spade_region_iou_mean':mean('spade_region_iou'),'doe_region_iou_mean':mean('doe_region_iou'),'spade_rounds':mean('spade_rounds'),'doe_rounds':mean('doe_rounds')}
