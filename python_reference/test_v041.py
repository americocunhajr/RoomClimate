import csv, io, json, tempfile, unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch
import numpy as np
from scipy.stats import qmc
from historical import WeatherArchive, HistoricalSystem, fetch, FIELDS, COLUMNS
from roomclimate import Room, SCENARIOS
from roomclimate_humidity import humidity_ratio, relative_humidity
from sensitivity import transform, jansen, design
from roomclimate_mc import write_csv


def synthetic_fixture(path):
    """Deliberately synthetic test data, not Rio historical data."""
    start=datetime(2024,1,1); rows=[]
    for i in range(24*7):
        t=start+timedelta(hours=i);h=t.hour;d=i//24
        te=27+4*np.cos((h-15)*np.pi/12)+.3*d
        ghi=800*max(0,np.sin((h-6)*np.pi/12))
        fac=600*max(0,np.sin((h-12)*np.pi/6)) if 12<=h<=18 else 0
        rows.append(dict(zip(COLUMNS,[t.isoformat(timespec='minutes'),te,20+.1*d,ghi,fac])))
    write_csv(path,rows)

class Tests(unittest.TestCase):
    def test_design_and_transform(self):
        a=transform(np.array([[0]*6,[1]*6]));np.testing.assert_allclose(a,[[.8,.35,.2,.6e6,445,8],[3.5,.55,2,2.4e6,695,14]])
        x=design(4,123).reshape(8,16,6)
        np.testing.assert_array_equal(x,design(4,123).reshape(8,16,6))
        for i in range(6):
            np.testing.assert_array_equal(x[2+i,:,i],x[1,:,i]);np.testing.assert_array_equal(np.delete(x[2+i],i,axis=1),np.delete(x[0],i,axis=1))
    def test_jansen_additive(self):
        u=qmc.Sobol(4,scramble=True,seed=1).random_base2(13);a,b=u[:,:2],u[:,2:]
        f=lambda z:(z[:,0]+2*z[:,1])[:,None]
        ab=[]
        for i in range(2):
            c=a.copy();c[:,i]=b[:,i];ab.append(f(c))
        first,total,_=jansen(f(a),f(b),np.array(ab))
        np.testing.assert_allclose(first[:,0],[.2,.8],atol=.002);np.testing.assert_allclose(total[:,0],[.2,.8],atol=.002)
        first,total,_=jansen(np.ones((8,1)),np.ones((8,1)),np.ones((2,8,1)))
        self.assertTrue(np.isnan(first).all() and np.isnan(total).all())
    def test_archive_and_integration(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'synthetic.csv';synthetic_fixture(path);arc=WeatherArchive(path)
            days=arc.eligible(3);self.assertEqual(days,[date(2024,1,i) for i in (4,5,6)])
            np.testing.assert_equal(arc.day(days[0])[-1],arc.day(days[1])[0])
            sys=HistoricalSystem(arc,Room(),SCENARIOS[1]);initial=sys.warm_block(days[0],3)
            te,ta,tr,tw,tf,fac=sys.forcing(15);self.assertAlmostEqual(tr,te+(.6/20)*800*np.sin(9*np.pi/12))
            self.assertAlmostEqual(sys.outdoor_humidity(15),humidity_ratio(20.3,1.))
            self.assertAlmostEqual(sys.fluxes(15,[25,29,.012],18000,True,True)[0],(sys.g_glass+sys.g_inf)*(te-25))
            h,y=sys.day(initial,18000,rtol=1e-6,max_step=240.);h2,y2=sys.day(initial,18000,rtol=1e-9,max_step=30.)
            np.testing.assert_array_equal(h,h2);self.assertLess(np.max(abs(y[:,:2]-y2[:,:2])),.01);self.assertLess(np.max(abs(y[:,2]-y2[:,2])),1e-5)
            print('Historical fixture refinement:',np.max(abs(y[:,:2]-y2[:,:2])),np.max(abs(y[:,2]-y2[:,2])))
            lines=path.read_text().splitlines();path.write_text('\n'.join(lines[:4]+lines[5:])+'\n')
            with self.assertRaises(ValueError):WeatherArchive(path)
    def test_fetch_mock(self):
        # Simulate the API transport, not the actual API service or actual weather.
        times=[(datetime(2024,1,1)+timedelta(hours=i)).isoformat(timespec='minutes') for i in range(48)]
        data={'hourly':{'time':times,**{f:[v]*48 for f,v in zip(FIELDS,[30,20,0,0])}},'latitude':-22.9,'longitude':-43.2}
        with tempfile.TemporaryDirectory() as tmp,patch('historical.urlopen',return_value=io.BytesIO(json.dumps(data).encode())) as req:
            path=Path(tmp)/'weather.csv';fetch(path,date(2024,1,1),date(2024,1,1));self.assertIn('azimuth=90.0',req.call_args.args[0]);self.assertIn('models=era5',req.call_args.args[0])
            arc=WeatherArchive(path);self.assertEqual(len(arc.times),24);self.assertEqual(arc.times[0],datetime(2024,1,1))
            self.assertTrue(path.with_suffix('.metadata.json').exists())

if __name__=='__main__':unittest.main()
