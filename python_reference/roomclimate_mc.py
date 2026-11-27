"""Monte Carlo conditional on a fixed synthetic design day (no weather probabilities)."""
import argparse
import csv
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path
import math
import numpy as np
from roomclimate_humidity import HygroSystem, MoistureModel
from roomclimate_transient import Model, CAPACITIES
from roomclimate import Room, SCENARIOS


def sample_parameters(n, seed):
    if n < 1:
        raise ValueError('n must be positive')
    rng = np.random.default_rng(seed)
    def loguniform(a,b):
        return np.exp(rng.uniform(np.log(a),np.log(b),n))
    return dict(u_roof=rng.uniform(.8,3.5,n),
                solar_factor=rng.triangular(.35,.45,.55,n),
                ach=loguniform(.2,2), mass_capacity=loguniform(.6e6,2.4e6),
                internal_sensible=rng.triangular(445,545,695,n),
                coil_temperature=rng.uniform(8,14,n))


def simulate(task):
    index, climate, parameters = task
    p = dict(parameters)
    model=Model(mass_capacity=p.pop('mass_capacity'))
    moisture=MoistureModel(coil_temperature=p.pop('coil_temperature'))
    system=HygroSystem(Room(),replace(SCENARIOS[climate], **p),model,moisture)
    initial,_=system.warmup()
    rows=[]
    for capacity in CAPACITIES:
        h,y=system.day(initial,capacity,rtol=1e-6,max_step=240.)
        metrics=system.metrics(h,y,capacity)
        rows.append(dict(sample=index,capacity_btuh=capacity,**parameters,**metrics))
    return rows


def wilson(k,n):
    z=1.959963984540054; p=k/n; d=1+z*z/n
    c=(p+z*z/(2*n))/d
    r=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return max(0,c-r),min(1,c+r)


def summarize(rows):
    output=[]
    for capacity in CAPACITIES:
        group=[r for r in rows if r['capacity_btuh']==capacity]; n=len(group)
        item=dict(capacity_btuh=capacity,n=n)
        for key in ('meets','meets_rh','meets_both'):
            k=sum(r[key] for r in group); lo,hi=wilson(k,n)
            item.update({key+'_count':k,key+'_fraction':k/n,key+'_ci_low':lo,key+'_ci_high':hi})
        item['supersaturation_count']=sum(r['supersaturation'] for r in group)
        for key in ('peak_c','peak_rh_pct'):
            for q,v in zip((5,50,95),np.percentile([r[key] for r in group],[5,50,95])):
                item[f'{key}_p{q}']=v
        output.append(item)
    return output


def write_csv(path,rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--n',type=int,default=64); a.add_argument('--seed',type=int,default=20261126)
    a.add_argument('--climate',type=int,choices=[0,1,2],default=1)
    a.add_argument('--workers',type=int,default=4); a.add_argument('--out',type=Path,default=Path('results_mc'))
    args=a.parse_args(); p=sample_parameters(args.n,args.seed)
    assert all(np.array_equal(v,sample_parameters(args.n,args.seed)[k]) for k,v in p.items())
    tasks=[(i,args.climate,{k:float(v[i]) for k,v in p.items()}) for i in range(args.n)]
    rows=[]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for i,result in enumerate(pool.map(simulate,tasks),1):
            rows.extend(result)
            if i%8==0 or i==args.n: print(f'{i}/{args.n}',flush=True)
    args.out.mkdir(parents=True,exist_ok=True)
    summary=summarize(rows)
    write_csv(args.out/'samples.csv',rows);write_csv(args.out/'summary.csv',summary)
    (args.out/'settings.txt').write_text(f'n={args.n}\nseed={args.seed}\nclimate_index={args.climate}\n')
    for r in summary: print(r['capacity_btuh'],r['meets_count'],r['meets_both_count'],r['peak_c_p50'],r['peak_c_p95'])

if __name__=='__main__':main()
