'use strict';
// RoomClimate v0.5 — deterministic four-state RC + moisture model (SI).
const S=typeof module!=='undefined'?require('./solar.js'):Solar;
const RC=(()=>{
const B=3.412141633, rho=1.2, cp=1006, hfg=2.501e6, p=101325, eps=.62198;
const caps=[0,7500,9000,12000,18000,24000];
const scenarios=[
 {name:'Favorável',out:33,adj:28,roofSol:42,wallSol:35,floor:25,irr:450,g:.35,uRoof:.8,uPart:1.3,ach:.5,wOut:.017,internal:445},
 {name:'Intermediário',out:35,adj:30,roofSol:48,wallSol:41,floor:28,irr:600,g:.45,uRoof:2,uPart:1.6,ach:.75,wOut:.019,internal:545},
 {name:'Desfavorável',out:37,adj:32,roofSol:55,wallSol:46,floor:30,irr:750,g:.55,uRoof:3.5,uPart:2,ach:1,wOut:.021,internal:695}];
const profiles=[[.40,.30,.20,.10,.30,.60,.85,.98,1,.83,.65,.50,.40],[.50,.40,.30,.25,.30,.45,.65,.85,1,.95,.80,.65,.50],[0,0,0,0,.10,.45,.80,1,.90,.45,.05,0,0],[0,0,0,0,0,.05,.20,.70,1,.55,0,0,0],[0,0,0,0,0,.03,.12,.65,1,.15,0,0,0]];
function base(){return {...S.defaults(),width:3,length:4,height:2.9,facade:'right',windows:[{pos:.1,width:2.8,height:5/2.8,sill:1}],objects:[{kind:'Mesa',x:.35,y:1.1,w:.75,h:1.4},{kind:'Estante',x:2.8,y:2.5,w:.9,h:.4}],ac:{wall:'top',pos:.35},door:{pos:.1},...scenarios[1],uGlass:5.7,uWall:2,uFloor:1.5,latent:55,set:21,tol:.5,rhLimit:65,mass:1.2e6,thickness:.15,density:2300,heat:880,k:1.7,coil:10,acStart:10,acEnd:18,occStart:9,occEnd:18,evalStart:13,evalEnd:18};}
// Plan dimensions: x=length, y=width. right/left facade length is width.
function span(c,wall=c.facade){return ['left','right'].includes(wall)?c.width:c.length;}
function wallOf(c,w){return c.mode==='legacy'?c.facade:(w.wall||c.facade);}
function exterior(c){return [...new Set([c.facade,...(c.mode==='legacy'?[]:c.extraWalls||[])])];}
function validate(c){
 S.validate(c);if(c.mode!=='legacy'&&(!Array.isArray(c.extraWalls)||c.extraWalls.some(w=>!S.walls.includes(w))))throw Error('Fachadas inválidas.');
 const positive=['width','length','height','uRoof','mass','thickness','density','heat','k','tol'];
 const nonneg=['irr','uPart','uGlass','uWall','uFloor','ach','wOut','internal','latent'];
 for(const k of positive)if(!Number.isFinite(c[k])||c[k]<=0)throw Error('Parâmetro positivo inválido: '+k);
 for(const k of nonneg)if(!Number.isFinite(c[k])||c[k]<0)throw Error('Parâmetro não negativo inválido: '+k);
 for(const k of ['out','adj','roofSol','wallSol','floor','set','coil','g','rhLimit'])if(!Number.isFinite(c[k]))throw Error('Parâmetro inválido: '+k);
 if(c.width>30||c.length>30||c.height>10||c.width<1||c.length<1||c.height<1.5||c.set<15||c.set>30||c.coil<0||c.coil>=c.set||c.g<0||c.g>1||c.rhLimit<=0||c.rhLimit>100||c.wOut>.05||c.ach>20)throw Error('Parâmetro fora do domínio da interface.');
 for(const [a,b] of [['acStart','acEnd'],['occStart','occEnd'],['evalStart','evalEnd']])if(!Number.isFinite(c[a])||!Number.isFinite(c[b])||c[a]<0||c[b]>24||c[a]>=c[b]||Math.round(c[a]*12)!==c[a]*12||Math.round(c[b]*12)!==c[b]*12)throw Error('Horários inválidos (múltiplos de 5 min).');
 if(!['left','right','top','bottom'].includes(c.facade)||!Array.isArray(c.windows))throw Error('Fachada inválida');
 for(const w of c.windows)if(![w.pos,w.width,w.height,w.sill].every(Number.isFinite)||w.pos<0||w.width<=0||w.height<=0||w.sill<0||!exterior(c).includes(wallOf(c,w))||w.pos+w.width>span(c,wallOf(c,w))+1e-8|| (c.mode!=='legacy'&&[w.g,w.shade].some(v=>v!==undefined&&(!Number.isFinite(v)||v<0||v>1)))||w.sill+w.height>c.height+1e-8)throw Error('Janela fora da fachada.');
 for(let i=0;i<c.windows.length;i++)for(let j=0;j<i;j++){const a=c.windows[i],b=c.windows[j];if(wallOf(c,a)===wallOf(c,b)&&Math.min(a.pos+a.width,b.pos+b.width)>Math.max(a.pos,b.pos)+1e-8&&Math.min(a.sill+a.height,b.sill+b.height)>Math.max(a.sill,b.sill)+1e-8)throw Error('Janelas sobrepostas.');}
 if(!Array.isArray(c.objects)||!c.ac||!c.door||!['left','right','top','bottom'].includes(c.ac.wall)||!Number.isFinite(c.ac.pos)||!Number.isFinite(c.door.pos)||c.ac.pos<0||c.ac.pos>1||c.door.pos<0||c.door.pos>1)throw Error('Planta inválida.');
 for(const o of c.objects)if(!['Mesa','Estante','Armário','Outro'].includes(o.kind)||![o.x,o.y,o.w,o.h].every(Number.isFinite)||o.x<0||o.y<0||o.w<=0||o.h<=0||o.x+o.w>c.length+1e-8||o.y+o.h>c.width+1e-8)throw Error('Móvel fora da sala.');
 if(1/c.uRoof<.14+c.thickness/c.k)throw Error('Transmitância da laje incompatível com concreto e filmes térmicos.');
}
const sat=t=>610.94*Math.exp(17.625*t/(t+243.04));
const wAt=(t,r)=>{const v=r*sat(t);return eps*v/(p-v);};
const rh=(t,w)=>100*p*w/(eps+w)/sat(t);
function legacy(c,h){let i=Math.min(11,Math.max(0,Math.floor(h/2))), f=h/2-i; const a=profiles.map(v=>v[i]+f*(v[i+1]-v[i]));const te=c.out-8*(1-a[0]);return [te,c.adj-5*(1-a[1]),te+(c.roofSol-(c.out-.16))*a[2],te+(c.wallSol-c.out)*a[3],c.floor-2*(1-a[1]),c.irr*a[4]];}
function geometry(c,h,shift=0){const a=legacy(c,h),sun=S.position(c.date,h+(c.mode==='historical'?24*shift:0),c.lat,c.lon,c.utcOffset),met=c.mode==='historical'?S.met(c,h+24*shift):{...S.clear(sun,c),te:a[0],dew:null},te=met.te;
 const irr=Object.fromEntries(exterior(c).map(w=>[w,S.plane(sun,met,S.azimuth(c,w),90,c.albedo)]));let wallArea=0,wallFlux=0,solar=0;
 for(const w of exterior(c)){const A=span(c,w)*c.height-c.windows.filter(j=>wallOf(c,j)===w).reduce((v,j)=>v+j.width*j.height,0);wallArea+=A;wallFlux+=A*irr[w];}
 for(const j of c.windows)solar+=j.width*j.height*(j.g??c.g)*(j.shade??1)*irr[wallOf(c,j)];
 const roof=c.mode==='historical'?met.ghi:S.plane(sun,met,0,0,c.albedo),wallI=wallArea?wallFlux/wallArea:0,wout=met.dew===null?Math.min(c.wOut,wAt(te,.99)):wAt(Math.min(te,met.dew),1);
 // Adjacent and floor profiles remain empirical; shift relative to current outdoor forcing in historical mode.
 const delta=c.mode==='historical'?te-a[0]:0;
 return [te,a[1]+delta,te+c.roofAbs*roof/c.hExt,te+c.wallAbs*wallI/c.hExt,a[4]+delta,solar,wout,roof,wallI,sun.altitude,sun.azimuth];}
function forcing(c,h,shift=0){if(c.mode==='legacy'||!c.mode)return legacy(c,h);return geometry(c,h,shift);}
function forcingTable(c,shift){if(c.mode==='legacy'||!c.mode)return h=>{const a=legacy(c,h);return [...a.slice(0,5),a[5]*c.g*c.windows.reduce((v,j)=>v+j.width*j.height,0),Math.min(c.wOut,wAt(a[0],.99))];};const rows=Array.from({length:289},(_,i)=>geometry(c,i/12,shift));return h=>{const x=Math.max(0,Math.min(288,h*12)),i=Math.min(287,Math.floor(x)),f=x-i;return rows[i].map((v,j)=>v+f*(rows[i+1][j]-v));};}
function system(c,shift=0){validate(c); const drive=forcingTable(c,shift); const A=c.width*c.length,V=A*c.height,Aw=c.windows.reduce((s,w)=>s+w.width*w.height,0), extSpan=exterior(c).reduce((a,w)=>a+span(c,w),0),Af=extSpan*c.height-Aw, Ap=(2*(c.width+c.length)-extSpan)*c.height;
 const ca=rho*cp*V,cm=c.mass,cr=A*c.thickness*c.density*c.heat,dm=rho*V,gi=dm*cp*c.ach/3600,gg=c.uGlass*Aw;
 const gb=[c.uPart*Ap,c.uWall*Af,c.uFloor*A],ge=gb.map(v=>v/.75),ga=gb.reduce((a,b)=>a+b,0)/.25,ri=.10+c.thickness/(2*c.k),gr=A/ri,ger=A/(1/c.uRoof-ri),wc=wAt(c.coil,1);if(ga<=0)throw Error('Massa interna sem caminho condutivo.');
 const rate=Math.max((gi+gg+ga+gr)/ca,(ge.reduce((a,b)=>a+b,0)+ga)/cm,(ger+gr)/cr,gi/(cp*dm));
 function rhs(h,y,cap,occ,on){const [t,m,r,w]=y,[te,ta,ts,tw,tf,solar,wout]=drive(h),internal=occ?c.internal:0,qr=.05*.8*solar+.20*.4*internal;
 let qs=0,ql=0;if(on&&cap>0&&t>c.set){const ds=cp*Math.max(0,t-c.coil),dl=hfg*Math.max(0,w-wc),shr=ds/(ds+dl),q=Math.min(cap/B,12000*(t-c.set)/shr);qs=q*shr;ql=q*(1-shr);}
 const ma=ga*(m-t),ra=gr*(r-t);return [( (gi+gg)*(te-t)+.2*solar+.6*internal+ma+ra-qs)/ca,(ge[0]*(ta-m)+ge[1]*(tw-m)+ge[2]*(tf-m)+.8*solar+.4*internal-qr-ma)/cm,(ger*(ts-r)+qr-ra)/cr,(gi/cp*(wout-w)+(occ?c.latent/hfg:0)-ql/hfg)/dm];}
 return {c,A,V,Aw,Af,Ap,ca,cm,cr,dm,rate,rhs,drive};}
function day(s,initial,cap,stepScale=1,record=true){let y=initial.slice(),rows=record?[[0,...y,rh(y[0],y[3]),s.drive(0)[0]]]:null; const c=s.c;
 for(let j=0;j<288;j++){const h=j/12,mid=(j+.5)/12,occ=mid>=c.occStart&&mid<c.occEnd,on=cap>0&&mid>=c.acStart&&mid<c.acEnd;
 const rate=s.rate+(on?12000/s.ca+12000/(s.dm*cp):0),n=Math.ceil(300/Math.min(60,1/rate)*stepScale),dt=300/n;
 if(n>20000)throw Error('Passo muito pequeno: revise os parâmetros.');
 for(let k=0;k<n;k++){const t=h+k*dt/3600,add=(a,b,f)=>a.map((v,i)=>v+f*b[i]);const a=s.rhs(t,y,cap,occ,on),b=s.rhs(t+dt/7200,add(y,a,dt/2),cap,occ,on),d=s.rhs(t+dt/7200,add(y,b,dt/2),cap,occ,on),e=s.rhs(t+dt/3600,add(y,d,dt),cap,occ,on);y=y.map((v,i)=>v+dt/6*(a[i]+2*b[i]+2*d[i]+e[i]));}
 if(!y.every(Number.isFinite)||y[3]<-1e-8)throw Error('Integração inválida.');if(record)rows.push([(j+1)/12,...y,rh(y[0],y[3]),s.drive((j+1)/12)[0]]);}
 return {end:y,rows};}
function initial(s,scale=1){if(s.c.mode==='historical'){const c=s.c,first=system(c,-c.warmDays),d=first.drive(0);let y=[d[0],d[1],d[0],d[6]];for(let k=-c.warmDays;k<0;k++)y=day(k===-c.warmDays?first:system(c,k),y,0,scale,false).end;return {state:y,days:c.warmDays};}let y=[s.c.adj,s.c.adj,s.c.adj,s.drive(0)[6]];for(let i=1;i<=365;i++){const z=day(s,y,0,scale,false).end;if(z.every((v,j)=>Math.abs(v-y[j])<(j===3?1e-9:1e-5)))return {state:z,days:i};y=z;}throw Error('Inicialização periódica não convergiu.');}
function metrics(c,rows){const a=rows.filter(r=>r[0]>=c.evalStart-1e-9&&r[0]<=c.evalEnd+1e-9),peak=Math.max(...a.map(r=>r[1])),humidity=Math.max(...a.map(r=>r[5])),supersat=rows.some(r=>r[5]>100.01);return {peak,humidity,supersat,pass:peak<=c.set+c.tol&&humidity<=c.rhLimit&&!supersat};}
function simulate(c,capacities=caps,scale=1){const s=system(c),init=initial(s,scale);return {geometry:{area:s.A,volume:s.V,window:s.Aw},days:init.days,results:capacities.map(cap=>{const {rows}=day(s,init.state,cap,scale);return {cap,rows,...metrics(c,rows)};})};}
return {base,scenarios,caps,span,wallOf,exterior,validate,forcing,system,day,initial,simulate,rh,wAt};})();
if(typeof module!=='undefined')module.exports=RC;
