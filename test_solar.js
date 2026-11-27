'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),R=require('./web/core'),S=require('./web/solar');
const close=(a,b,t=1e-8)=>assert(Math.abs(a-b)<t,`${a} != ${b}`);
const c={...R.base(),mode:'geometry'};
for(const h of [0,6,12,18,24]){const s=S.position(c.date,h,c.lat,c.lon,c.utcOffset);close(s.east*s.east+s.north*s.north+s.up*s.up,1);}
const equinox=S.position('2025-03-20',12,0,0,0);assert(equinox.altitude>87);
const noon=S.position(c.date,12,c.lat,c.lon,c.utcOffset);assert(noon.altitude>85);
const a=S.position(c.date,9,c.lat,c.lon,c.utcOffset),b=S.position(c.date,16,c.lat,c.lon,c.utcOffset);assert(a.east>0&&b.east<0);
close(S.plane({east:1,north:0,up:0.1},{dni:700,dhi:100,ghi:400},90,90,.2),790);close(S.plane({east:1,north:0,up:.1},{dni:700,dhi:100,ghi:400},270,90,.2),90);
assert.equal(S.plane({up:-.1},{dni:700,dhi:100,ghi:400},0),0);
assert.equal(S.azimuth(c,'right'),270);const e={...c,northAz:0};assert(R.forcing(c,16)[5]>R.forcing(e,16)[5]);assert(R.forcing(e,9)[5]>R.forcing(c,9)[5]);
const shaded={...c,windows:c.windows.map(w=>({...w,shade:0}))};close(R.forcing(shaded,16)[5],0);
const multi={...c,extraWalls:['top'],windows:[...c.windows,{wall:'top',pos:0,width:1,height:1,sill:1,g:.5,shade:.7}]};R.validate(multi);close(R.system(multi).Aw,6);close(R.system(multi).Af,14.3);assert.throws(()=>R.validate({...multi,extraWalls:[]}));
const results=R.simulate(c),fine=R.simulate(c,R.caps,2);let err=0;for(let i=0;i<results.results.length;i++){const r=results.results[i],q=fine.results[i];assert.equal(r.pass,q.pass);for(let j=0;j<r.rows.length;j++)for(let k=1;k<4;k++)err=Math.max(err,Math.abs(r.rows[j][k]-q.rows[j][k]));}assert(err<.01);
console.log('Geometry, cardinal directions, incidence, shading, multi-facade, refinement: OK. Max temperature error:',err);
// Synthetic hourly fixture: explicit marker, not actual weather. Include time padding.
const h={...c,mode:'historical'},start=Date.parse('2025-01-07T00:00:00Z')/1000,time=Array.from({length:240},(_,i)=>start+3600*i),names=['temperature_2m','dew_point_2m','shortwave_radiation','direct_normal_irradiance','diffuse_radiation'];
const raw={latitude:h.lat,longitude:h.lon,roomclimate_fixture:true,hourly_units:{time:'unixtime',...Object.fromEntries(names.map((k,i)=>[k,i<2?'°C':'W/m²']))},hourly:{time}};
for(const [i,k] of names.entries())raw.hourly[k]=time.map(t=>{const local=new Date((t+h.utcOffset*3600)*1000),hour=local.getUTCHours(),date=local.toISOString().slice(0,10),solar=S.clear(S.position(date,hour-.5,h.lat,h.lon,h.utcOffset),h);return [28+5*Math.cos((hour-15)*Math.PI/12),19,solar.ghi,solar.dni,solar.dhi][i];});
fs.mkdirSync('fixtures',{recursive:true});fs.writeFileSync('fixtures/synthetic_weather.json',JSON.stringify(raw));h.weather=S.normalize(raw,h);S.checkWeather(h.weather,h);assert.equal(S.met(h,12).te,raw.hourly.temperature_2m[time.indexOf(Date.parse('2025-01-15T15:00:00Z')/1000)]);assert.throws(()=>S.checkWeather(h.weather,{...h,date:'2025-01-16'}));assert.throws(()=>S.checkWeather({...h.weather,time:h.weather.time.slice(0,50)},h));assert.throws(()=>S.normalize({...raw,latitude:0},h));const hist=R.simulate(h,[0,12000,18000]);assert.equal(hist.days,7);assert(hist.results.every(r=>Number.isFinite(r.peak)));assert(hist.results[2].peak<=hist.results[1].peak);console.log('Synthetic import, timezone, missing data, seven-day history: OK.');
const history=R.simulate({...h,warmDays:3},[18000]);console.log('Warmup sensitivity (synthetic fixture, 3 vs 7 days):',Math.abs(history.results[0].peak-hist.results[2].peak));
console.log('Synthetic geometry results:',JSON.stringify(results.results.map(r=>({cap:r.cap,peak:r.peak,humidity:r.humidity,pass:r.pass}))));
