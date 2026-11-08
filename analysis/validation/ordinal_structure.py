"""Exploratory polychoric/ULS structure sensitivity, NOT robust ordinal CFA.

Two-step marginal thresholds and bivariate-normal pair likelihoods; deterministic
Gauss-Legendre quadrature. Standardized factor loadings fit the off-diagonal
correlations by ULS. No chi-square/RMSEA/p-values: asymptotic weight matrix and
robust corrections are not estimated. No new observations are generated.
"""
from pathlib import Path
import json, hashlib
import numpy as np
import pandas as pd
from scipy.special import ndtr, ndtri
from scipy.optimize import minimize_scalar, least_squares
from numpy.polynomial.legendre import leggauss
from check_arithmetic import ROOT, load, htmt, ITEMS

OUT=Path(__file__).resolve().parent
TRI=np.triu_indices(10,1)

def thresholds(x):
    counts=np.bincount(x.astype(int),minlength=8)[1:8]
    assert (counts>0).all(), 'Empty marginal category requires explicit handling'
    return np.r_[-10.,ndtri(np.cumsum(counts)[:-1]/len(x)),10.]

def setup(tx,ty,nodes):
    nodes0,weights=leggauss(nodes)
    half=(tx[1:]-tx[:-1])/2
    x=(tx[1:]+tx[:-1])[:,None]/2+half[:,None]*nodes0
    w=half[:,None]*weights*np.exp(-x*x/2)/np.sqrt(2*np.pi)
    def probs(rho):
        c=ndtr((ty[None,None,:]-rho*x[:,:,None])/np.sqrt(1-rho*rho))
        return np.sum(w[:,:,None]*np.diff(c,axis=2),axis=1)
    return probs

def pair(x,y,nodes=64):
    tx,ty=thresholds(x),thresholds(y)
    table=np.zeros((7,7),int); np.add.at(table,(x.astype(int)-1,y.astype(int)-1),1)
    probs=setup(tx,ty,nodes)
    expected=np.outer(table.sum(axis=1),table.sum(axis=0))/len(x)**2
    assert np.max(abs(probs(0)-expected))<1e-10
    def loss(rho): return -np.sum(table*np.log(np.maximum(probs(rho),1e-300)))
    fit=minimize_scalar(loss,bounds=(-.98,.98),method='bounded',options={'xatol':1e-9})
    assert fit.success and abs(fit.x)<.97999
    p=probs(fit.x); assert abs(p.sum()-1)<1e-10 and p.min()>=-1e-15
    return float(fit.x), int((table==0).sum())

def implied(v,two):
    r=np.outer(v[:10],v[:10])
    if two:
        r[:5,5:]*=v[10]; r[5:,:5]*=v[10]
    np.fill_diagonal(r,1.)
    return r

def factor(r,two):
    def fun(v): return (implied(v,two)-r)[TRI]
    fits=[]
    for start in (.5,.75,.9):
        x=np.repeat(start,11 if two else 10)
        f=least_squares(fun,x,bounds=(.00001,.99999),xtol=1e-12,ftol=1e-12,gtol=1e-12,max_nfev=3000)
        assert f.success
        fits.append(f)
    f=min(fits,key=lambda a:np.sum(a.fun*a.fun)); residual=implied(f.x,two)-r
    idx=np.argmax(abs(residual[TRI])); i,j=TRI[0][idx],TRI[1][idx]
    return dict(offdiag_rms=float(np.sqrt(np.mean(f.fun*f.fun))),max_abs_residual=float(abs(residual[i,j])),
                largest_residual_pair=f'{ITEMS[i]} / {ITEMS[j]}',factor_correlation=float(f.x[10]) if two else 1.,
                min_uniqueness=float((1-f.x[:10]**2).min()),max_start_objective_difference=float(np.ptp([np.sum(a.fun*a.fun) for a in fits])),
                loadings=f.x[:10].tolist())

def main():
    d=load(); output=[]; pairs=[]; checks=[]
    for sample,z in [('E1',d[d.study==1]),('E2',d[d.study==2]),('pooled',d)]:
        x=z[ITEMS].to_numpy(); pearson=np.corrcoef(x.T); poly=np.eye(10)
        for i,j in zip(*TRI):
            rho,empty=pair(x[:,i],x[:,j],64)
            refined,_=pair(x[:,i],x[:,j],128)
            swapped,_=pair(x[:,j],x[:,i],128)
            assert abs(rho-refined)<1e-5 and abs(refined-swapped)<1e-5
            poly[i,j]=poly[j,i]=refined
            pairs.append(dict(sample=sample,item1=ITEMS[i],item2=ITEMS[j],pearson=pearson[i,j],polychoric=refined,empty_cells_of_49=empty,
                              quadrature_change=abs(rho-refined),exchange_change=abs(refined-swapped)))
        eigen=float(np.linalg.eigvalsh(poly).min()); assert eigen>0, 'Do not silently repair non-PD matrix'
        checks.append(dict(sample=sample,n=len(x),min_polychoric_eigenvalue=eigen,htmt_pearson=htmt(pearson),htmt_polychoric=htmt(poly)))
        for method,r in [('pearson',pearson),('polychoric',poly)]:
            pd.DataFrame(r,index=ITEMS,columns=ITEMS).to_csv(OUT/f'{sample}_{method}_correlations.csv')
            for two in (False,True):
                f=factor(r,two); loadings=f.pop('loadings')
                output.append(dict(sample=sample,correlations=method,model='two_factor' if two else 'one_factor',n=len(x),**f))
                pd.DataFrame({'item':ITEMS,'loading':loadings,'uniqueness':1-np.array(loadings)**2}).to_csv(OUT/f'{sample}_{method}_{"two" if two else "one"}_loadings.csv',index=False)
        print(sample,checks[-1],flush=True)
    table=pd.DataFrame(output); table.to_csv(OUT/'ordinal_structure.csv',index=False)
    pd.DataFrame(pairs).to_csv(OUT/'polychoric_pairs.csv',index=False)
    meta=dict(method='Two-step pairwise polychoric estimates and standardized off-diagonal ULS; no inferential fit indices',
              samples=checks,quadrature_nodes=[64,128],max_quadrature_change=max(p['quadrature_change'] for p in pairs),
              max_exchange_change=max(p['exchange_change'] for p in pairs),threshold_tail_cutoff=10,
              assumptions=['Ordered responses arise by thresholding bivariate-normal latent responses','Local independence within the one/two-factor approximations','Participant rows treated as independent within released study'],
              limitations=['Not WLSMV/ULSMV: no robust chi-square, RMSEA, parameter CI or invariance test','Pooled marginal correlation is not a multigroup invariance test','Sparse pairwise cells are counted; no category merging or PD repair','Same-data structure sensitivity, not a new validation population','Additional analysis chosen after inspecting continuous CFA; exploratory'],
              input_sha256={f'experiment{i}.sav.csv':hashlib.sha256((ROOT/f'data/raw/beyond_voice/experiment{i}.sav.csv').read_bytes()).hexdigest() for i in (1,2)})
    (OUT/'ordinal_metadata.json').write_text(json.dumps(meta,indent=2)); print(table.to_string(index=False))

if __name__=='__main__': main()
