"""RoomClimate v0.2: two-node transient sensible heat model (SI).
Run: python roomclimate_transient.py --out results
Requires NumPy and SciPy; imports the v0.1 module roomclimate.py.
"""
from dataclasses import dataclass, replace
from pathlib import Path
import argparse
import csv
import numpy as np
from scipy.integrate import solve_ivp
from roomclimate import (Room, Scenario, SCENARIOS, RHO_AIR, CP_AIR,
                         W_TO_BTUH, thermal_load)

HOUR = 3600.0
CAPACITIES = (0, 7500, 9000, 12000, 18000, 24000)
# Synthetic local-clock profiles; piecewise linear, not weather observations.
HOURS = np.arange(0, 25, 2, dtype=float)
OUT = np.array([.40,.30,.20,.10,.30,.60,.85,.98,1,.83,.65,.50,.40])
ADJ = np.array([.50,.40,.30,.25,.30,.45,.65,.85,1,.95,.80,.65,.50])
ROOF = np.array([0,0,0,0,.10,.45,.80,1,.90,.45,.05,0,0])
WALL = np.array([0,0,0,0,0,.05,.20,.70,1,.55,0,0,0])
SUN = np.array([0,0,0,0,0,.03,.12,.65,1,.15,0,0,0])

@dataclass(frozen=True)
class Model:
    mass_capacity: float = 1.2e6  # J/K; effective solids, assumed
    exterior_resistance_fraction: float = .75  # fraction of opaque R outside mass node
    solar_convective: float = .20
    internal_convective: float = .60
    shr: float = .80  # fixed sensible heat ratio; not a humidity prediction
    kp: float = 12000.0  # W/K, proportional thermostat
    ac_start: float = 10.0
    ac_end: float = 18.0
    assessment_start: float = 13.0
    assessment_end: float = 18.0
    tolerance: float = .5

    def __post_init__(self):
        if self.mass_capacity <= 0 or self.kp <= 0 or self.tolerance < 0:
            raise ValueError('Invalid capacity, thermostat or tolerance')
        if not 0 < self.exterior_resistance_fraction < 1 or not 0 < self.shr <= 1:
            raise ValueError('Invalid resistance split or SHR')
        if not all(0 <= x <= 1 for x in (self.solar_convective, self.internal_convective)):
            raise ValueError('Invalid convective fraction')
        if not 0 <= self.ac_start < self.ac_end <= 24 or not 0 <= self.assessment_start < self.assessment_end <= 24:
            raise ValueError('Invalid time window')


def weather(hour, s):
    """Synthetic forcing anchored to v0.1 scenario peak inputs."""
    def p(values):
        return float(np.interp(hour, HOURS, values))
    te = s.t_out - 8*(1-p(OUT))
    ta = s.t_adj - 5*(1-p(ADJ))
    # Solar excess scaled to attain the prescribed sol-air temperature at its peak.
    te14 = s.t_out - 8*(1-OUT[7])
    tr = te + (s.t_roof_sol-te14)*p(ROOF)
    tw = te + (s.t_wall_sol-s.t_out)*p(WALL)
    tf = s.t_floor_adj - 2*(1-p(ADJ))
    return te, ta, tr, tw, tf, s.irradiance*p(SUN)


class ThermalSystem:
    def __init__(self, room: Room, scenario: Scenario, model: Model):
        self.room, self.s, self.m = room, scenario, model
        thermal_load(room, scenario)  # reuse parameter validation
        self.ca = RHO_AIR*CP_AIR*room.volume
        self.g_inf = RHO_AIR*CP_AIR*room.volume*scenario.ach/HOUR
        self.g_glass = scenario.u_glass*room.window_area
        self.gb = np.array([scenario.u_partition*room.partition_area,
                            scenario.u_roof*room.floor_area,
                            scenario.u_wall*room.facade_area,
                            scenario.u_floor*room.floor_area])
        f = model.exterior_resistance_fraction
        self.g_ext = self.gb/f
        self.g_am = float(sum(self.gb))/(1-f)
        if self.g_am <= 0:
            raise ValueError('The aggregate opaque mass needs a conductive path')

    def forcing(self, hour):
        return weather(hour, self.s)

    def forcing_knots(self):
        return HOURS.tolist()

    def fluxes(self, hour, y, capacity, occupied, ac_on):
        t, tm = y
        s, m = self.s, self.m
        te, ta, tr, tw, tf, ir = self.forcing(hour)
        q_direct = (self.g_inf+self.g_glass)*(te-t)
        q_bound = float(self.g_ext @ (np.array([ta,tr,tw,tf])-tm))
        solar = self.room.window_area*s.solar_factor*ir
        internal = s.internal_sensible if occupied else 0.
        q_air = m.solar_convective*solar+m.internal_convective*internal
        q_mass = (1-m.solar_convective)*solar+(1-m.internal_convective)*internal
        q_exchange = self.g_am*(tm-t)
        q_ac = min(capacity/W_TO_BTUH*m.shr, max(0.,m.kp*(t-s.t_set))) if ac_on else 0.
        return q_direct, q_bound, q_air, q_mass, q_exchange, q_ac

    def rhs(self, time, y, capacity, occupied, ac_on):
        qd, qb, qa, qm, qx, qc = self.fluxes(time/HOUR,y,capacity,occupied,ac_on)
        return np.array([(qd+qa+qx-qc)/self.ca, (qb+qm-qx)/self.m.mass_capacity])

    def day(self, initial, capacity, sample_minutes=5, rtol=1e-7, max_step=120.):
        if capacity < 0 or sample_minutes <= 0 or max_step <= 0:
            raise ValueError('Invalid capacity or time step')
        # Restart exactly at schedule jumps and interpolation knots.
        edges = sorted(set(self.forcing_knots()+[9.,18.,self.m.ac_start,self.m.ac_end]))
        samples = np.unique(np.r_[np.arange(0,24,sample_minutes/60),24.,edges,
                                  self.m.assessment_start,self.m.assessment_end])
        state = np.asarray(initial,dtype=float)
        tt, yy = [], []
        for a,b in zip(edges[:-1],edges[1:]):
            mid = (a+b)/2
            occupied = 9 <= mid < 18
            ac_on = self.m.ac_start <= mid < self.m.ac_end
            grid = samples[(samples>a)&(samples<=b)]
            sol = solve_ivp(self.rhs, (a*HOUR,b*HOUR), state, method='LSODA',
                            args=(capacity,occupied,ac_on), t_eval=np.r_[a,grid]*HOUR,
                            rtol=rtol,atol=rtol*.01,max_step=max_step)
            if not sol.success:
                raise RuntimeError(sol.message)
            tt.extend(sol.t[1:]/HOUR); yy.extend(sol.y[:,1:].T)
            state = sol.y[:,-1]
        return np.r_[0.,tt], np.vstack([initial,yy])

    def warmup(self):
        """Periodic free-running initial state for a repeated synthetic day."""
        state = np.array([self.s.t_adj,self.s.t_adj],dtype=float)
        for n in range(1,61):
            _, y = self.day(state,0,sample_minutes=60)
            next_state = y[-1]
            if np.max(np.abs(next_state-state)) < .001:
                return next_state,n
            state = next_state
        raise RuntimeError('Periodic initial condition did not converge')

    def metrics(self, hours, y, capacity):
        m,s = self.m,self.s
        active = (hours>=m.assessment_start)&(hours<=m.assessment_end)
        temp = y[:,0]
        limit = s.t_set+m.tolerance
        excess = np.maximum(0,temp[active]-limit)
        # Include first crossing after switching on; no extrapolation.
        indices = np.flatnonzero((hours>=m.ac_start)&(hours<=m.ac_end)&(temp<=limit))
        reach = None
        if len(indices):
            i=indices[0]; reach=float(hours[i])
            if i and hours[i-1]>=m.ac_start and temp[i-1]>limit:
                reach=float(hours[i-1]+(hours[i]-hours[i-1])*(temp[i-1]-limit)/(temp[i-1]-temp[i]))
        peak = float(max(temp[active]))
        return dict(peak_c=peak, end_c=float(np.interp(m.assessment_end,hours,temp)),
                    degree_hours=float(np.trapezoid(excess,hours[active])),
                    minutes_to_target=None if reach is None else (reach-m.ac_start)*60,
                    meets=peak<=limit)


def self_test():
    sys = ThermalSystem(Room(),SCENARIOS[1],Model())
    # Conservation of energy: internal exchange cancels exactly.
    y=np.array([23.,29.]); qd,qb,qa,qm,qx,qc=sys.fluxes(15,y,18000,True,True)
    d=sys.rhs(15*HOUR,y,18000,True,True)
    assert np.isclose(np.array([sys.ca,sys.m.mass_capacity])@d,qd+qb+qa+qm-qc)
    # Equivalent steady opaque conduction with zero absorbed radiation.
    t=21.; bounds=np.array([30.,48.,41.,28.]); tm=(sys.g_ext@bounds+sys.g_am*t)/(sum(sys.g_ext)+sys.g_am)
    assert np.isclose(sys.g_am*(tm-t),sys.gb@(bounds-t))
    assert sys.fluxes(15,[20.,29.],18000,True,True)[-1]==0
    assert np.isclose(sys.fluxes(15,[30.,29.],18000,True,True)[-1],18000/W_TO_BTUH*sys.m.shr)
    init,_=sys.warmup()
    h,y=sys.day(init,18000); h2,y2=sys.day(init,18000,rtol=1e-9,max_step=30.)
    err=float(np.max(np.abs(y-y2))); assert err<.01,err
    _,free=sys.day(init,0); assert np.all(y[:,0]<=free[:,0]+1e-4)
    return err


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=Path('results'))
    args=parser.parse_args(); args.out.mkdir(parents=True,exist_ok=True)
    err=self_test(); print(f'Testes OK; refinamento temporal: diferença máxima {err:.6f} °C')
    series=[]; summary=[]
    for s in SCENARIOS:
        sys=ThermalSystem(Room(),s,Model()); initial,n=sys.warmup()
        print(f'\n{s.name}: início {initial[0]:.2f} °C; warmup {n} dias')
        for cap in CAPACITIES:
            h,y=sys.day(initial,cap); metrics=sys.metrics(h,y,cap)
            summary.append(dict(scenario=s.name,capacity_btuh=cap,**metrics))
            print(f'{cap:5d} BTU/h: pico {metrics["peak_c"]:.2f} °C; 18h {metrics["end_c"]:.2f} °C; atende {metrics["meets"]}')
            for hour,(t,tm) in zip(h,y):
                q=sys.fluxes(hour,(t,tm),cap,9<=hour<18,sys.m.ac_start<=hour<sys.m.ac_end)[-1]
                series.append(dict(scenario=s.name,capacity_btuh=cap,hour=hour,air_c=t,mass_c=tm,external_c=weather(hour,s)[0],cooling_sensible_w=q))
    for name,rows in [('summary',summary),('timeseries',series)]:
        with (args.out/f'{name}.csv').open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

if __name__=='__main__':
    main()
