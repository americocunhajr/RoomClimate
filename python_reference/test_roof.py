import unittest, tempfile
from dataclasses import replace
from pathlib import Path
from datetime import date
import numpy as np
from roof import Roof, RoofSystem, HistoricalRoofSystem, WeatherArchive
from roomclimate import Room, SCENARIOS, H_FG
from roomclimate_transient import HOUR
from test_v041 import synthetic_fixture

class Tests(unittest.TestCase):
    def test_roof_resistance(self):
        for s in SCENARIOS:
            sys=RoofSystem(Room(),s)
            self.assertAlmostEqual(1/(1/sys.g_er+1/sys.g_ra),s.u_roof*sys.room.floor_area)
        with self.assertRaises(ValueError): RoofSystem(Room(),replace(SCENARIOS[1],u_roof=10))
        with self.assertRaises(ValueError): Roof(thickness=0)
        self.assertEqual(RoofSystem(Room(),replace(SCENARIOS[1],u_roof=0)).g_er,0)
    def test_energy_and_water_balance(self):
        sys=RoofSystem(Room(),SCENARIOS[1]); y=[25,30,32,.013]
        q=sys.fluxes(15,y,18000,True,True); d=sys.rhs(15*HOUR,y,18000,True,True)
        total=sys.ca*d[0]+sys.m.mass_capacity*d[1]+sys.cr*d[2]
        self.assertAlmostEqual(total,sum(q[k] for k in ('direct','boundary_mass','boundary_roof','gains_air','gains_mass','gains_roof'))-q['sensible_cooling'])
        self.assertAlmostEqual(sys.dry_mass*d[3],q['vapor_in']+q['vapor_gen']-q['vapor_removed'])
        self.assertAlmostEqual(q['latent_cooling'],H_FG*q['vapor_removed'])
        self.assertAlmostEqual(q['gains_air']+q['gains_mass']+q['gains_roof'],sys.room.window_area*sys.s.solar_factor*sys.forcing(15)[5]+sys.s.internal_sensible)
    def test_equilibrium(self):
        s=replace(SCENARIOS[1],irradiance=0,internal_sensible=0,internal_latent=0,w_out=.009)
        sys=RoofSystem(Room(),s);sys.forcing=lambda h:[25,25,25,25,25,0]
        np.testing.assert_allclose(sys.rhs(0,[25,25,25,.009],0,False,False),0,atol=1e-14)
    def test_integration(self):
        sys=RoofSystem(Room(),SCENARIOS[1]);init,n=sys.warmup()
        h,y=sys.day(init,18000);h2,y2=sys.day(init,18000,rtol=1e-9,max_step=30.)
        np.testing.assert_array_equal(h,h2)
        et=float(np.max(abs(y[:,:3]-y2[:,:3])));ew=float(np.max(abs(y[:,3]-y2[:,3])))
        print('Refinement:',et,ew,'periodic warmup days:',n)
        self.assertLess(et,.01);self.assertLess(ew,1e-5);self.assertGreaterEqual(np.min(y[:,3]),0)
        _,free=sys.day(init,0);self.assertLessEqual(np.max(y[:,0]-free[:,0]),1e-6)
    def test_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'synthetic.csv';synthetic_fixture(p)
            sys=HistoricalRoofSystem(WeatherArchive(p),Room(),SCENARIOS[1]);init=sys.warm_block(date(2024,1,4),3)
            self.assertEqual(len(init),4);h,y=sys.day(init,18000);self.assertTrue(np.all(np.isfinite(y)))
            self.assertEqual(y.shape[1],4);self.assertIn('peak_roof_c',sys.metrics(h,y,18000))
if __name__=='__main__': unittest.main()
