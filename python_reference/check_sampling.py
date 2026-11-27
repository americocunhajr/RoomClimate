"""Check temporal sampling on cases closest to the decision thresholds."""
import argparse,csv
from pathlib import Path
from roof_mc import system,periodic_initial,draw

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('file',type=Path);p.add_argument('--seed',type=int,default=20261126);a=p.parse_args()
    rows=list(csv.DictReader(a.file.open()));params=draw(1,a.seed).keys()
    for climate in sorted(set(int(r['climate']) for r in rows)):
        for cap in (9000,12000,18000,24000):
            group=[r for r in rows if int(r['climate'])==climate and int(r['capacity_btuh'])==cap]
            if not group: continue
            select={r['sample']:r for r in (min(group,key=lambda r:abs(float(r['peak_c'])-21.5)),min(group,key=lambda r:abs(float(r['peak_rh_pct'])-65)))}
            for r in select.values():
                s=system(climate,{k:float(r[k]) for k in params});z=periodic_initial(s);h,y=s.day(z,cap,sample_minutes=1,rtol=1e-8,max_step=60.)
                m=s.metrics(h,y,cap)
                print(climate,cap,r['sample'],f"delta_T={m['peak_c']-float(r['peak_c']):.6g}",f"delta_RH={m['peak_rh_pct']-float(r['peak_rh_pct']):.6g}",f"joint_changed={str(m['meets_both'])!=r['meets_both']}")
if __name__=='__main__': main()
