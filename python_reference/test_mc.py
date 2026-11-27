import unittest
from dataclasses import replace
import numpy as np
from roomclimate_mc import sample_parameters, wilson
from roomclimate import Room, SCENARIOS
from roomclimate_transient import Model
from roomclimate_humidity import HygroSystem, MoistureModel

class Tests(unittest.TestCase):
    def test_support_and_seed(self):
        p=sample_parameters(10000,123)
        bounds=dict(u_roof=(.8,3.5),solar_factor=(.35,.55),ach=(.2,2),
                    mass_capacity=(.6e6,2.4e6),internal_sensible=(445,695),coil_temperature=(8,14))
        for k,(lo,hi) in bounds.items():
            self.assertTrue(np.all((p[k]>=lo)&(p[k]<=hi)))
            np.testing.assert_array_equal(p[k],sample_parameters(10000,123)[k])
        self.assertAlmostEqual(np.mean(np.log(p['ach'])),np.log(.2*2)/2,delta=.03)
        self.assertAlmostEqual(np.mean(p['solar_factor']),.45,delta=.002)
    def test_wilson(self):
        self.assertAlmostEqual(wilson(0,100)[0],0.)
        self.assertAlmostEqual(wilson(100,100)[1],1.)
        self.assertLess(wilson(100,100)[0],1.)
    def test_refinement(self):
        p={k:float(v[0]) for k,v in sample_parameters(1,20261126).items()}
        system=HygroSystem(Room(),replace(SCENARIOS[1],**{k:v for k,v in p.items() if k not in ('mass_capacity','coil_temperature')}),Model(mass_capacity=p['mass_capacity']),MoistureModel(coil_temperature=p['coil_temperature']))
        initial,_=system.warmup()
        for cap in (12000,18000):
            h,y=system.day(initial,cap,rtol=1e-6,max_step=240.)
            h2,y2=system.day(initial,cap,rtol=1e-9,max_step=30.)
            np.testing.assert_array_equal(h,h2)
            err_t=np.max(abs(y[:,:2]-y2[:,:2])); err_w=np.max(abs(y[:,2]-y2[:,2])); print('cap, T error, w error:',cap,err_t,err_w)
            self.assertLess(err_t,.01);self.assertLess(err_w,1e-5)
if __name__=='__main__':unittest.main()
