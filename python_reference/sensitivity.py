"""Replicated scrambled Sobol designs and Jansen estimators, fixed synthetic day."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path
import numpy as np
from scipy.stats import qmc, triang
from roomclimate import Room, SCENARIOS
from roomclimate_transient import Model
from roomclimate_humidity import HygroSystem, MoistureModel
from roomclimate_mc import write_csv

NAMES=('u_roof','solar_factor','ach','mass_capacity','internal_sensible','coil_temperature')
OUTPUTS=('peak_c','degree_hours','peak_rh_pct')

def transform(u):
    """Independent marginals agreed in v0.4; rows in the unit hypercube."""
    u=np.asarray(u,dtype=float)
    if u.shape[-1]!=6 or np.any(~np.isfinite(u)) or np.any((u<0)|(u>1)):
        raise ValueError('Expected unit-cube coordinates with six columns')
    return np.stack([.8+2.7*u[...,0],triang.ppf(u[...,1],.5,loc=.35,scale=.2),
        .2*10**u[...,2],.6e6*4**u[...,3],
        triang.ppf(u[...,4],.4,loc=445,scale=250),8+6*u[...,5]],axis=-1)

def evaluate(task):
    x,capacity,climate=task
    p=dict(zip(NAMES,map(float,x)))
    model=Model(mass_capacity=p.pop('mass_capacity'))
    moisture=MoistureModel(coil_temperature=p.pop('coil_temperature'))
    system=HygroSystem(Room(),replace(SCENARIOS[climate],**p),model,moisture)
    initial,_=system.warmup()
    h,y=system.day(initial,capacity,rtol=1e-6,max_step=240.)
    m=system.metrics(h,y,capacity)
    return [m[k] for k in OUTPUTS]

def jansen(a,b,ab):
    """AB_i is A with column i from B; arrays (n, outputs), (d,n,outputs)."""
    var=np.var(np.concatenate((a,b),axis=0),axis=0,ddof=1)
    denom=np.where(var>1e-14,2*var,np.nan)
    first=1-np.mean((b[None,:,:]-ab)**2,axis=1)/denom
    total=np.mean((a[None,:,:]-ab)**2,axis=1)/denom
    return first,total,var

def design(m,seed):
    d=len(NAMES); u=qmc.Sobol(2*d,scramble=True,seed=seed).random_base2(m)
    a,b=u[:,:d],u[:,d:]; blocks=[a,b]
    for i in range(d):
        ab=a.copy();ab[:,i]=b[:,i];blocks.append(ab)
    return transform(np.concatenate(blocks))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--m',type=int,default=5);p.add_argument('--replicates',type=int,default=4)
    p.add_argument('--seed',type=int,default=20261126);p.add_argument('--workers',type=int,default=4)
    p.add_argument('--capacity',type=float,default=12000);p.add_argument('--climate',type=int,choices=[0,1,2],default=1)
    p.add_argument('--out',type=Path,default=Path('results_sobol'));args=p.parse_args()
    if args.m<1 or args.replicates<1 or args.capacity<0: p.error('invalid design or capacity')
    n=2**args.m; detail=[]; raw=[]
    seeds=np.random.SeedSequence(args.seed).generate_state(args.replicates)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for r,seed in enumerate(seeds):
            x=design(args.m,int(seed)); tasks=((row,args.capacity,args.climate) for row in x)
            vals=np.asarray(list(pool.map(evaluate,tasks,chunksize=2))).reshape(8,n,len(OUTPUTS))
            f,t,v=jansen(vals[0],vals[1],vals[2:])
            for i,name in enumerate(NAMES):
                for j,out in enumerate(OUTPUTS):
                    detail.append(dict(replicate=r,parameter=name,output=out,first=f[i,j],total=t[i,j],variance=v[j]))
            for k,(row,val) in enumerate(zip(x,vals.reshape(-1,len(OUTPUTS)))):
                raw.append(dict(replicate=r,block=k//n,row=k%n,**dict(zip(NAMES,row)),**dict(zip(OUTPUTS,val))))
            print(f'Replicate {r+1}/{args.replicates} complete',flush=True)
    summary=[]
    for name in NAMES:
        for out in OUTPUTS:
            rows=[x for x in detail if x['parameter']==name and x['output']==out]
            item=dict(parameter=name,output=out,n_base=n,replicates=args.replicates)
            for key in ('first','total'):
                values=np.array([x[key] for x in rows]);item[key+'_mean']=float(np.mean(values));item[key+'_sd']=float(np.std(values,ddof=1)) if len(values)>1 else float('nan')
            summary.append(item)
    args.out.mkdir(parents=True,exist_ok=True)
    for name,rows in [('indices',summary),('replicates',detail),('evaluations',raw)]:write_csv(args.out/(name+'.csv'),rows)
    (args.out/'settings.txt').write_text(str(vars(args))+'\n')
    for x in summary:
        if x['output']=='peak_c':print(x['parameter'],round(x['first_mean'],3),round(x['total_mean'],3),round(x['total_sd'],3))

if __name__=='__main__': main()
