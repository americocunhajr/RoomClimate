"""Roof Monte Carlo with physical material constraints; synthetic climate scenarios."""
import argparse
from dataclasses import replace
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from roof import Roof, RoofSystem
from roomclimate import Room, SCENARIOS
from roomclimate_transient import Model, CAPACITIES
from roomclimate_humidity import MoistureModel
from roomclimate_mc import summarize, write_csv


def draw(n,seed):
    if n<1: raise ValueError('n must be positive')
    u=np.random.default_rng(seed).random((n,10))
    def un(i,a,b): return a+(b-a)*u[:,i]
    def log(i,a,b): return a*(b/a)**u[:,i]
    def tri(i,a,m,b):
        x=u[:,i]; return np.where(x<(m-a)/(b-a),a+np.sqrt(x*(b-a)*(m-a)),b-np.sqrt((1-x)*(b-a)*(b-m)))
    p=dict(u_roof=un(0,.8,3.5),solar_factor=tri(1,.35,.45,.55),ach=log(2,.2,2),mass_capacity=log(3,.6e6,2.4e6),internal_sensible=tri(4,445,545,695),coil_temperature=un(5,8,14),thickness=un(6,.10,.20),density=tri(7,2200,2300,2500),specific_heat=tri(8,800,880,1000),conductivity=tri(9,1.4,1.7,2.1))
    p['additional_r']=1/p['u_roof']-.10-.04-p['thickness']/p['conductivity']
    if min(p['additional_r'])<0: raise ValueError('Incompatible roof')
    return p


def system(climate,p):
    p=dict(p); p.pop('additional_r')
    r=Roof(**{k:p.pop(k) for k in ('thickness','density','specific_heat','conductivity')})
    m=Model(mass_capacity=p.pop('mass_capacity')); h=MoistureModel(coil_temperature=p.pop('coil_temperature'))
    return RoofSystem(Room(),replace(SCENARIOS[climate],**p),m,h,r)


def periodic_initial(s):
    # Free-running ODE is affine with constant Jacobian. Its exact day map is
    # x(24h)=exp(A*24h)x(0)+b. Calculate b using the existing LSODA integrator.
    from scipy.linalg import expm
    z=np.zeros(4); b=s.rhs(0,z,0,False,False)
    A=np.column_stack([s.rhs(0,e,0,False,False)-b for e in np.eye(4)])
    _,y=s.day(z,0,sample_minutes=60,rtol=1e-8,max_step=300.)
    return np.linalg.solve(np.eye(4)-expm(A*86400),y[-1])


def simulate(task):
    i,climate,p=task;s=system(climate,p);init=periodic_initial(s);rows=[]
    for cap in CAPACITIES:
        h,y=s.day(init,cap,sample_minutes=5,rtol=1e-6,max_step=300.)
        rows.append(dict(sample=i,climate=climate,capacity_btuh=cap,**p,roof_capacity=s.cr,**s.metrics(h,y,cap)))
    return rows


def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--n',type=int,default=128);a.add_argument('--seed',type=int,default=20261126);a.add_argument('--workers',type=int,default=4);a.add_argument('--climates',type=int,nargs='+',choices=[0,1,2],default=[0,1,2]);a.add_argument('--out',type=Path,default=Path('results_roof_mc'));args=a.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    p=draw(args.n,args.seed);allrows=[];summary=[];convergence=[]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for climate in args.climates:
            tasks=[(i,climate,{k:float(v[i]) for k,v in p.items()}) for i in range(args.n)]
            rows=[]
            for i,res in enumerate(pool.map(simulate,tasks),1):
                rows+=res
                if i%16==0: print(climate,i,flush=True)
            allrows+=rows;summary.extend(dict(climate=climate,**r) for r in summarize(rows))
            for n in sorted(set([k for k in (16,32,64,128,256,512) if k<=args.n]+[args.n])): convergence.extend(dict(climate=climate,**r) for r in summarize([r for r in rows if r['sample']<n]))
            write_csv(args.out/'samples.csv',allrows);write_csv(args.out/'summary.csv',summary);write_csv(args.out/'convergence.csv',convergence)
    (args.out/'settings.txt').write_text(f'n={args.n}\nseed={args.seed}\nclimate=synthetic {args.climates}\n')
if __name__=='__main__': main()
