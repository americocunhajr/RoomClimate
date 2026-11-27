import unittest
import numpy as np
from roof_mc import draw, system, periodic_initial

class Tests(unittest.TestCase):
    def test_nested_draws(self):
        a=draw(16,123); b=draw(32,123)
        for k in a: np.testing.assert_array_equal(a[k],b[k][:16])
    def test_positive_resistance(self):
        a=draw(10000,321)
        self.assertGreater(min(a['additional_r']),0)
        self.assertGreater(min(a['thickness']),0)
        self.assertLess(max(a['solar_factor']),1)
    def test_physical_equivalence(self):
        a=draw(16,123)
        for i in range(16):
            p={k:v[i] for k,v in a.items()};s=system(1,p)
            self.assertAlmostEqual(1/(1/s.g_er+1/s.g_ra),p['u_roof']*s.room.floor_area)
            self.assertAlmostEqual(s.cr,s.room.floor_area*p['thickness']*p['density']*p['specific_heat'])
    def test_initial(self):
        p={k:v[0] for k,v in draw(1,123).items()};s=system(1,p);z=periodic_initial(s)
        _,y=s.day(z,0,rtol=1e-9,max_step=60.)
        err=abs(y[-1]-z)
        print('Periodic closure:',err)
        self.assertLess(max(err[:3]),1e-4);self.assertLess(err[3],1e-7)
        old,n=s.warmup();self.assertLess(max(abs(old[:3]-z[:3])),.01)
    def test_refinement(self):
        p={k:v[0] for k,v in draw(1,123).items()};s=system(2,p);z=periodic_initial(s)
        h,a=s.day(z,18000,rtol=1e-6,max_step=300.);h2,b=s.day(z,18000,rtol=1e-9,max_step=30.)
        np.testing.assert_array_equal(h,h2);err=abs(a-b).max(axis=0)
        print('Refinement:',err)
        self.assertLess(max(err[:3]),.01);self.assertLess(err[3],1e-5)
if __name__=='__main__': unittest.main()
