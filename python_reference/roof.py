"""RoomClimate v0.4.2: separate roof thermal mass. State [Ta,Tm,Tr,w], SI."""
from dataclasses import dataclass, replace
from datetime import timedelta
from pathlib import Path
import argparse
import numpy as np
from roomclimate import Room, SCENARIOS, CP_AIR, H_FG
from roomclimate_transient import Model, HOUR, CAPACITIES
from roomclimate_humidity import HygroSystem, MoistureModel, relative_humidity
from historical import HistoricalSystem, WeatherArchive
from roomclimate_mc import write_csv

@dataclass(frozen=True)
class Roof:
    thickness: float = .15
    density: float = 2300.
    specific_heat: float = 880.
    conductivity: float = 1.7
    interior_film_r: float = .10
    solar_fraction: float = .05 # fraction of nonconvective window gains
    internal_fraction: float = .20 # fraction of nonconvective internal gains
    def __post_init__(self):
        if not all(np.isfinite(v) and v>0 for v in (self.thickness,self.density,self.specific_heat,self.conductivity,self.interior_film_r)):
            raise ValueError('Roof properties must be finite and positive')
        if not all(0<=v<=1 for v in (self.solar_fraction,self.internal_fraction)):
            raise ValueError('Radiant fractions must be in [0,1]')
    @property
    def r_inside(self):
        return self.interior_film_r+self.thickness/(2*self.conductivity)

class RoofSystem(HygroSystem):
    def __init__(self, room, scenario, model=Model(), moisture=MoistureModel(), roof=Roof()):
        super().__init__(room,scenario,model,moisture)
        self.roof=roof
        self.cr=room.floor_area*roof.thickness*roof.density*roof.specific_heat
        self.g_ra=room.floor_area/roof.r_inside
        if scenario.u_roof>0:
            r_out=1/scenario.u_roof-roof.r_inside
            if r_out<=0: raise ValueError('Incompatible roof U and interior resistance')
            self.g_er=room.floor_area/r_out
        else: self.g_er=0.
        self.g_other_ext=self.g_ext[[0,2,3]]
        self.g_other_air=float(sum(self.gb[[0,2,3]]))/(1-model.exterior_resistance_fraction)
        if self.g_other_air<=0: raise ValueError('Non-roof mass needs a conductive path')
    def fluxes(self,hour,y,capacity,occupied,ac_on):
        t,tm,tr,w=y
        te,ta,ts,tw,tf,ir=self.forcing(hour)
        solar=self.room.window_area*self.s.solar_factor*ir
        internal=self.s.internal_sensible if occupied else 0.
        sa=self.m.solar_convective*solar; ia=self.m.internal_convective*internal
        sr=(1-self.m.solar_convective)*solar; it=(1-self.m.internal_convective)*internal
        qr=self.roof.solar_fraction*sr+self.roof.internal_fraction*it
        qs,ql=self.cooling(t,w,capacity,ac_on)
        return dict(direct=(self.g_glass+self.g_inf)*(te-t),
                    boundary_mass=float(self.g_other_ext @ (np.array([ta,tw,tf])-tm)),
                    boundary_roof=self.g_er*(ts-tr), gains_air=sa+ia,
                    gains_mass=sr+it-qr,gains_roof=qr,
                    mass_to_air=self.g_other_air*(tm-t),roof_to_air=self.g_ra*(tr-t),
                    sensible_cooling=qs,latent_cooling=ql,
                    vapor_in=self.g_inf/CP_AIR*(self.outdoor_humidity(hour)-w),
                    vapor_gen=self.s.internal_latent/H_FG if occupied else 0.,vapor_removed=ql/H_FG)
    def rhs(self,time,y,capacity,occupied,ac_on):
        q=self.fluxes(time/HOUR,y,capacity,occupied,ac_on)
        return np.array([(q['direct']+q['gains_air']+q['mass_to_air']+q['roof_to_air']-q['sensible_cooling'])/self.ca,
            (q['boundary_mass']+q['gains_mass']-q['mass_to_air'])/self.m.mass_capacity,
            (q['boundary_roof']+q['gains_roof']-q['roof_to_air'])/self.cr,
            (q['vapor_in']+q['vapor_gen']-q['vapor_removed'])/self.dry_mass])
    def warmup(self):
        state=np.array([self.s.t_adj]*3+[self.outdoor_humidity(0)])
        for n in range(1,181):
            _,y=self.day(state,0,sample_minutes=60)
            end=y[-1]
            if np.max(abs(end[:3]-state[:3]))<.001 and abs(end[3]-state[3])<1e-7: return end,n
            state=end
        raise RuntimeError('Roof periodic warmup did not converge')
    def metrics(self,hours,y,capacity):
        out=HygroSystem.metrics(self,hours,y[:,[0,1,3]],capacity)
        active=(hours>=self.m.assessment_start)&(hours<=self.m.assessment_end)
        out.update(peak_roof_c=float(max(y[active,2])),daily_peak_roof_c=float(max(y[:,2])))
        return out

class HistoricalRoofSystem(RoofSystem):
    def __init__(self,archive,*args,**kwargs):
        super().__init__(*args,**kwargs); self.archive=archive;self.profile=None
    select_day=HistoricalSystem.select_day
    forcing_knots=HistoricalSystem.forcing_knots
    at=HistoricalSystem.at
    forcing=HistoricalSystem.forcing
    outdoor_humidity=HistoricalSystem.outdoor_humidity
    def warm_block(self,d,warmup_days):
        if warmup_days<1: raise ValueError('Need preceding days')
        self.select_day(d-timedelta(days=warmup_days));v=self.at(0)
        state=np.array([v[1]]*3+[v[6]])
        for j in range(warmup_days,0,-1):
            self.select_day(d-timedelta(days=j));_,y=self.day(state,0,sample_minutes=60,rtol=1e-6,max_step=240.)
            state=y[-1]
        self.select_day(d);return state

def compare(out):
    out.mkdir(parents=True,exist_ok=True); summary=[];series=[]
    for s in SCENARIOS:
        room=Room();new=RoofSystem(room,s)
        systems=[('v041',HygroSystem(room,s)),('aggregate_equal_capacity',HygroSystem(room,s,replace(Model(),mass_capacity=Model().mass_capacity+new.cr))),('explicit_roof',new)]
        for name,sys in systems:
            initial,n=sys.warmup()
            for cap in CAPACITIES:
                h,y=sys.day(initial,cap);metrics=sys.metrics(h,y,cap)
                row=dict(scenario=s.name,model=name,capacity_btuh=cap,warmup_days=n,**metrics)
                row.setdefault('peak_roof_c',None);row.setdefault('daily_peak_roof_c',None);summary.append(row)
                for hour,state in zip(h,y):
                    t,tm,w=state[0],state[1],state[-1];tr=state[2] if len(state)==4 else None
                    series.append(dict(scenario=s.name,model=name,capacity_btuh=cap,hour=hour,air_c=t,mass_c=tm,roof_c=tr,
                        rh_pct=100*relative_humidity(t,w),outdoor_c=sys.forcing(hour)[0],roof_sol_air_c=sys.forcing(hour)[2]))
                print(s.name,name,cap,round(metrics['peak_c'],2),round(metrics['peak_rh_pct'],1),metrics['meets_both'],flush=True)
    write_csv(out/'summary.csv',summary);write_csv(out/'timeseries.csv',series)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=Path('results_roof'));compare(p.parse_args().out)
