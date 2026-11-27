"""Hourly meteorological blocks, local standard time (UTC-3), historical or test CSV.
No silent synthetic fallback. Radiation columns are instantaneous W/m².
"""
import argparse, csv, json, hashlib
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlencode
from dataclasses import replace
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from roomclimate import Room, SCENARIOS
from roomclimate_transient import Model, CAPACITIES
from roomclimate_humidity import HygroSystem, MoistureModel, humidity_ratio
from roomclimate_mc import sample_parameters, summarize, write_csv

COLUMNS=('timestamp','temperature_c','dewpoint_c','ghi_wm2','facade_wm2')
FIELDS=('temperature_2m','dew_point_2m','shortwave_radiation_instant','global_tilted_irradiance_instant')
API='https://archive-api.open-meteo.com/v1/archive'

def fetch(path,start,end,latitude=-22.91,longitude=-43.17,azimuth=270.):
    """ERA5 reanalysis, UTC input shifted to Rio standard time; azimuth clockwise from N."""
    if not -90<=latitude<=90 or not -180<=longitude<=180 or not 0<=azimuth<360 or end<start:
        raise ValueError('Invalid location, azimuth or dates')
    # Extra UTC day guarantees the entire final local day. API azimuth: 0 south, +90 west.
    query=dict(latitude=latitude,longitude=longitude,start_date=start.isoformat(),
               end_date=(end+timedelta(days=1)).isoformat(),hourly=','.join(FIELDS),
               timezone='GMT',models='era5',tilt=90,azimuth=(azimuth%360)-180)
    url=API+'?'+urlencode(query)
    with urlopen(url,timeout=60) as response: data=json.load(response)
    h=data['hourly'];rows=[]
    for i,ts in enumerate(h['time']):
        local=datetime.fromisoformat(ts)-timedelta(hours=3)
        if start<=local.date()<=end:
            values=[h[field][i] for field in FIELDS]
            if any(v is None for v in values): raise ValueError('Missing weather data at '+ts)
            rows.append(dict(zip(COLUMNS,[local.isoformat(timespec='minutes'),*values])))
    if len(rows)!=24*((end-start).days+1):raise ValueError('Unexpected length of hourly archive')
    path.parent.mkdir(parents=True,exist_ok=True);write_csv(path,rows)
    meta=dict(source='Open-Meteo ERA5 reanalysis',request=url,local_time='UTC-03:00',
              retrieved_grid_latitude=data.get('latitude'),retrieved_grid_longitude=data.get('longitude'),
              facade_azimuth_from_north_deg=azimuth,units=data.get('hourly_units'),
              attribution='Weather data by Open-Meteo.com; ERA5, Copernicus Climate Change Service')
    path.with_suffix('.metadata.json').write_text(json.dumps(meta,indent=2))
    return path

class WeatherArchive:
    def __init__(self,path,roof_abs=.6,wall_abs=.6,h_ext=20.,adj_offset=0.,floor_offset=0.):
        if not (0<=roof_abs<=1 and 0<=wall_abs<=1 and h_ext>0):raise ValueError('Invalid surface parameters')
        with Path(path).open(newline='') as f: rows=list(csv.DictReader(f))
        if not rows:raise ValueError('Empty archive')
        self.times=[datetime.fromisoformat(r['timestamp']) for r in rows]
        if any(t.tzinfo is not None or t.minute or t.second or t.microsecond for t in self.times):
            raise ValueError('Expected naive local standard time, whole hours')
        if any(b-a!=timedelta(hours=1) for a,b in zip(self.times,self.times[1:])):
            raise ValueError('Hourly timestamps must be consecutive and unique')
        te,dp,ghi,fac=np.array([[float(r[k]) for k in COLUMNS[1:]] for r in rows]).T
        if not np.all(np.isfinite([te,dp,ghi,fac])) or np.any(dp>te+.15) or np.any(ghi<0) or np.any(fac<0):
            raise ValueError('Invalid temperature, dew point or irradiance')
        def smooth(tau):
            v=np.empty_like(te);v[0]=te[0];a=np.exp(-1/tau)
            for i in range(1,len(v)):v[i]=a*v[i-1]+(1-a)*te[i]
            return v
        # Adjacent rooms/floor are unmeasured: simple low-pass boundary surrogates.
        self.values=np.column_stack([te,smooth(24)+adj_offset,te+roof_abs*ghi/h_ext,
              te+wall_abs*fac/h_ext,smooth(48)+floor_offset,fac,
              [humidity_ratio(min(t,d),1.) for t,d in zip(te,dp)]])
        self.index={t.date():i for i,t in enumerate(self.times) if t.hour==0}
    def eligible(self,warmup_days=3,months=(12,1,2),min_peak_outdoor=None):
        if warmup_days<1 or not months or any(m<1 or m>12 for m in months):raise ValueError('Invalid warmup or months')
        return [d for d,i in self.index.items() if d.month in months and i>=24*warmup_days and i+24<len(self.times)
                and (min_peak_outdoor is None or np.max(self.values[i:i+24,0])>=min_peak_outdoor)]
    def day(self,d):
        i=self.index[d]
        if i+24>=len(self.times):raise ValueError('Missing following midnight')
        return self.values[i:i+25]

class HistoricalSystem(HygroSystem):
    def __init__(self,archive,*args,**kwargs):
        super().__init__(*args,**kwargs);self.archive=archive;self.profile=None
    def select_day(self,d):self.profile=self.archive.day(d)
    def forcing_knots(self):return list(range(25))
    def at(self,h):
        if self.profile is None:raise RuntimeError('Select day first')
        h=float(np.clip(h,0,24));i=min(int(h),23);f=h-i
        return (1-f)*self.profile[i]+f*self.profile[i+1]
    def forcing(self,h):return self.at(h)[:6]
    def outdoor_humidity(self,h):return float(self.at(h)[6])
    def warm_block(self,d,warmup_days):
        """Preceding consecutive days, free-running; not repeated target day."""
        self.select_day(d-timedelta(days=warmup_days));v=self.at(0)
        state=np.array([v[1],v[1],v[6]])
        for j in range(warmup_days,0,-1):
            self.select_day(d-timedelta(days=j));_,y=self.day(state,0,sample_minutes=60,rtol=1e-6,max_step=240.)
            state=y[-1]
        self.select_day(d);return state

_ARCHIVE=None

def init_worker(path,roof_abs,wall_abs,h_ext,adj_offset,floor_offset):
    global _ARCHIVE
    _ARCHIVE=WeatherArchive(path,roof_abs,wall_abs,h_ext,adj_offset,floor_offset)

def simulate(task):
    index,d,p,warmup,caps=task
    p=dict(p); model=Model(mass_capacity=p.pop('mass_capacity'));moisture=MoistureModel(coil_temperature=p.pop('coil_temperature'))
    sys=HistoricalSystem(_ARCHIVE,Room(),replace(SCENARIOS[1],**p),model,moisture)
    initial=sys.warm_block(d,warmup);rows=[]
    for cap in caps:
        h,y=sys.day(initial,cap,rtol=1e-6,max_step=240.)
        rows.append(dict(sample=index,date=d.isoformat(),capacity_btuh=cap,**task[2],**sys.metrics(h,y,cap)))
    return rows

def run(args):
    settings=(args.csv,args.roof_abs,args.wall_abs,args.h_ext,args.adj_offset,args.floor_offset)
    archive=WeatherArchive(*settings);days=archive.eligible(args.warmup,tuple(args.months),args.min_peak_outdoor)
    if not days:raise ValueError('No eligible days with complete preceding weather and following midnight')
    p=sample_parameters(args.n,args.seed)
    rng=np.random.default_rng(np.random.SeedSequence([args.seed,1]));chosen=rng.choice(days,args.n,replace=True)
    tasks=[(i,d,{k:float(v[i]) for k,v in p.items()},args.warmup,CAPACITIES) for i,d in enumerate(chosen)]
    with ProcessPoolExecutor(max_workers=args.workers,initializer=init_worker,initargs=settings) as pool:
        rows=[row for group in pool.map(simulate,tasks) for row in group]
    args.out.mkdir(parents=True,exist_ok=True);write_csv(args.out/'samples.csv',rows);write_csv(args.out/'summary.csv',summarize(rows))
    (args.out/'settings.json').write_text(json.dumps(dict(**vars(args),eligible_days=len(days),csv_sha256=hashlib.sha256(args.csv.read_bytes()).hexdigest(),
        interpretation='Conditional on empirical archive, independent uncertain physical inputs, initially free-running; not annual reliability'),default=str,indent=2))
    print(f'{len(days)} eligible dates, {len(rows)} model runs. Output: {args.out}')

def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='cmd',required=True)
    f=sub.add_parser('fetch');f.add_argument('--csv',type=Path,required=True);f.add_argument('--start',type=date.fromisoformat,required=True);f.add_argument('--end',type=date.fromisoformat,required=True)
    f.add_argument('--latitude',type=float,default=-22.91);f.add_argument('--longitude',type=float,default=-43.17);f.add_argument('--azimuth',type=float,default=270)
    r=sub.add_parser('run');r.add_argument('--csv',type=Path,required=True);r.add_argument('--out',type=Path,default=Path('results_historical'))
    r.add_argument('--n',type=int,default=128);r.add_argument('--seed',type=int,default=20261126);r.add_argument('--workers',type=int,default=4);r.add_argument('--warmup',type=int,default=3);r.add_argument('--months',nargs='+',type=int,default=[12,1,2]);r.add_argument('--min-peak-outdoor',type=float,default=None)
    for name,val in [('roof-abs',.6),('wall-abs',.6),('h-ext',20.),('adj-offset',0.),('floor-offset',0.)]:r.add_argument('--'+name,type=float,default=val)
    a=p.parse_args()
    if a.cmd=='fetch':fetch(a.csv,a.start,a.end,a.latitude,a.longitude,a.azimuth)
    else:run(a)

if __name__=='__main__':main()
