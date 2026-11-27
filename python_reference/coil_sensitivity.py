"""Reproduce the sensitivity of temperature and humidity to coil ADP."""
import argparse
import csv
from pathlib import Path
from roomclimate_humidity import HygroSystem, MoistureModel, Room, SCENARIOS


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=Path('results_v03'))
    args=parser.parse_args(); args.out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for s in SCENARIOS:
        initial,_=HygroSystem(Room(),s).warmup()
        for tc in (8.,10.,12.,14.):
            sys=HygroSystem(Room(),s,moisture=MoistureModel(coil_temperature=tc))
            for cap in (12000,18000,24000):
                h,y=sys.day(initial,cap)
                rows.append(dict(scenario=s.name,coil_c=tc,capacity_btuh=cap,**sys.metrics(h,y,cap)))
    with (args.out/'coil_sensitivity.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

if __name__=='__main__':
    main()
