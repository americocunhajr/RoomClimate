"""RoomClimate v0.3: coupled two-node thermal and humidity model.
SI units; humidity ratio in kg water/kg dry air. Synthetic design days.
"""
from dataclasses import dataclass
from pathlib import Path
import argparse
import csv
import math
import numpy as np
from roomclimate import Room, SCENARIOS, RHO_AIR, CP_AIR, H_FG, W_TO_BTUH
from roomclimate_transient import ThermalSystem, Model, weather, CAPACITIES, HOUR

P_ATM = 101325.0
EPS = .62198


def saturation_pressure(t):
    """Magnus approximation over liquid water, near ordinary room temperatures."""
    return 610.94 * math.exp(17.625*t/(t+243.04))


def humidity_ratio(t, rh, p=P_ATM):
    pv = rh*saturation_pressure(t)
    if not 0 <= pv < p:
        raise ValueError('Invalid vapor partial pressure')
    return EPS*pv/(p-pv)


def relative_humidity(t, w, p=P_ATM):
    return p*w/(EPS+w)/saturation_pressure(t)


@dataclass(frozen=True)
class MoistureModel:
    coil_temperature: float = 10.0  # effective apparatus dew point, assumed
    rh_limit: float = .65  # illustrative comfort criterion, not a standard
    pressure: float = P_ATM

    def __post_init__(self):
        if not 0 <= self.coil_temperature <= 20 or not 0 < self.rh_limit <= 1 or self.pressure <= 0:
            raise ValueError('Invalid coil temperature, RH limit or pressure')


class HygroSystem(ThermalSystem):
    def __init__(self, room, scenario, model=Model(), moisture=MoistureModel()):
        super().__init__(room, scenario, model)
        self.hygro = moisture
        self.dry_mass = RHO_AIR*room.volume
        self.w_coil = humidity_ratio(moisture.coil_temperature,1.,moisture.pressure)
        if moisture.coil_temperature >= scenario.t_set:
            raise ValueError('Coil must be colder than setpoint')

    def outdoor_humidity(self, hour):
        # Preserve scenario humidity ratio unless limited by saturation at lower T.
        te = self.forcing(hour)[0]
        return min(self.s.w_out,humidity_ratio(te,.99,self.hygro.pressure))

    def cooling(self,t,w,capacity,ac_on):
        """Idealized ADP-based split; nominal total is an upper bound.
        No airflow or compressor map: assumes enough airflow to reach that bound.
        Thermostat acts on sensible cooling, with latent removal proportional to runtime.
        """
        if not ac_on or capacity <= 0 or t <= self.s.t_set:
            return 0.,0.
        dh_s = CP_AIR*max(0.,t-self.hygro.coil_temperature)
        dh_l = H_FG*max(0.,w-self.w_coil)
        shr = dh_s/(dh_s+dh_l)
        q_total = min(capacity/W_TO_BTUH,self.m.kp*(t-self.s.t_set)/shr)
        return q_total*shr,q_total*(1-shr)

    def fluxes(self,hour,y,capacity,occupied,ac_on):
        t,tm,w = y
        # Reuse v0.2 opaque, solar and internal fluxes; its direct-air
        # infiltration coefficient is a thermal conductance [W/K].
        _,qb,qa,qm,qx,_ = super().fluxes(hour,(t,tm),0,occupied,False)
        te = self.forcing(hour)[0]
        qd = (self.g_glass+self.g_inf)*(te-t)
        qs,ql = self.cooling(t,w,capacity,ac_on)
        vapor_in = self.g_inf/CP_AIR*(self.outdoor_humidity(hour)-w)
        vapor_gen = self.s.internal_latent/H_FG if occupied else 0.
        vapor_removed = ql/H_FG
        return qd,qb,qa,qm,qx,qs,ql,vapor_in,vapor_gen,vapor_removed

    def rhs(self,time,y,capacity,occupied,ac_on):
        qd,qb,qa,qm,qx,qs,ql,vi,vg,vr = self.fluxes(time/HOUR,y,capacity,occupied,ac_on)
        return np.array([(qd+qa+qx-qs)/self.ca,(qb+qm-qx)/self.m.mass_capacity,
                         (vi+vg-vr)/self.dry_mass])

    def warmup(self):
        state = np.array([self.s.t_adj,self.s.t_adj,self.outdoor_humidity(0)])
        for n in range(1,61):
            _,y = self.day(state,0,sample_minutes=60)
            end=y[-1]
            if max(abs(end[:2]-state[:2]))<.001 and abs(end[2]-state[2])<1e-7:
                return end,n
            state=end
        raise RuntimeError('Periodic warmup did not converge')

    def metrics(self,hours,y,capacity):
        out = super().metrics(hours,y,capacity)
        active=(hours>=self.m.assessment_start)&(hours<=self.m.assessment_end)
        rh=np.array([relative_humidity(t,w,self.hygro.pressure) for t,_,w in y])
        out.update(peak_rh_pct=100*float(max(rh[active])),
                   end_rh_pct=100*float(np.interp(self.m.assessment_end,hours,rh)),
                   meets_rh=bool(max(rh[active])<=self.hygro.rh_limit),
                   supersaturation=bool(max(rh)>1.0001))
        out['meets_both']=bool(out['meets'] and out['meets_rh'] and not out['supersaturation'])
        return out


def self_test():
    sys=HygroSystem(Room(),SCENARIOS[1]); y=np.array([25.,30.,.015])
    assert abs(relative_humidity(21,humidity_ratio(21,.6))-.6)<1e-12
    qd,qb,qa,qm,qx,qs,ql,vi,vg,vr=sys.fluxes(15,y,18000,True,True)
    d=sys.rhs(15*HOUR,y,18000,True,True)
    assert np.isclose(sys.ca*d[0]+sys.m.mass_capacity*d[1],qd+qb+qa+qm-qs)
    assert np.isclose(sys.dry_mass*d[2],vi+vg-vr)
    assert np.isclose(qs+ql,18000/W_TO_BTUH)
    assert np.isclose(qd,(sys.g_glass+sys.g_inf)*(weather(15,sys.s)[0]-y[0]))
    assert sys.cooling(25,.005,18000,True)[1]==0
    assert sys.cooling(20,.015,18000,True)==(0.,0.)
    assert sys.cooling(25,.015,0,True)==(0.,0.)
    assert sys.cooling(25,.015,18000,False)==(0.,0.)
    assert sys.cooling(25,.02,18000,True)[0]<qs
    init,_=sys.warmup(); h,a=sys.day(init,18000); h2,b=sys.day(init,18000,rtol=1e-9,max_step=30.)
    err_t=float(np.max(abs(a[:,:2]-b[:,:2])));err_w=float(np.max(abs(a[:,2]-b[:,2])))
    assert np.array_equal(h,h2) and err_t<.01 and err_w<1e-5
    assert np.min(a[:,2])>=0
    return err_t,err_w


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=Path('results_v03'));args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    err=self_test();print('Tests passed; refinement max T and w errors:',err)
    summary=[];series=[]
    for s in SCENARIOS:
        sys=HygroSystem(Room(),s);init,n=sys.warmup()
        for cap in CAPACITIES:
            h,y=sys.day(init,cap);m=sys.metrics(h,y,cap)
            summary.append(dict(scenario=s.name,capacity_btuh=cap,**m))
            print(s.name,cap,round(m['peak_c'],2),round(m['peak_rh_pct'],2),m['meets_both'], 'supersat',m['supersaturation'])
            for hour,(t,tm,w) in zip(h,y):
                qs,ql=sys.cooling(t,w,cap,sys.m.ac_start<=hour<sys.m.ac_end)
                series.append(dict(scenario=s.name,capacity_btuh=cap,hour=hour,air_c=t,mass_c=tm,humidity_ratio=w,
                    rh_pct=100*relative_humidity(t,w,sys.hygro.pressure),external_c=weather(hour,s)[0],
                    external_humidity_ratio=sys.outdoor_humidity(hour),cooling_sensible_w=qs,cooling_latent_w=ql,condensate_kg_h=ql/H_FG*HOUR))
    for name,rows in [('summary',summary),('timeseries',series)]:
        with (args.out/f'{name}.csv').open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

if __name__=='__main__':
    main()
