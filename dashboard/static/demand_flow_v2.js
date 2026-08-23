window.__SIMBA_DEMAND_FLOW_BUILD="v2.1-hard-overwrite";

(() => {
"use strict";

const SDF = {
  mode: "current",
  metric: "kva",
  horizon: "30_minutes",
  data: null,
  refreshHandle: null
};

const H = {
  "30_minutes": {label:"30 min", hours:0.5},
  "2_hours": {label:"2 hrs", hours:2},
  "6_hours": {label:"6 hrs", hours:6},
  "24_hours": {label:"24 hrs", hours:24}
};

const n = v => {
  const x = Number(v);
  return Number.isFinite(x) ? x : null;
};
const pf = v => {
  const x = n(v);
  return x == null ? null : Math.max(0, Math.min(1, Math.abs(x)));
};
const esc = v => String(v ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmt = (v,d=1) => n(v)==null ? "—" : Number(v).toLocaleString(undefined,{minimumFractionDigits:d,maximumFractionDigits:d});
const kvarFrom = (kva,powerFactor) => {
  const s=n(kva), p=pf(powerFactor);
  return s==null || p==null ? null : s*Math.sqrt(Math.max(0,1-p*p));
};
const kwFrom = (kva,powerFactor) => {
  const s=n(kva), p=pf(powerFactor);
  return s==null || p==null ? null : s*p;
};

async function getJSON(url) {
  const r = await fetch(url,{cache:"no-store",headers:{"Accept":"application/json"}});
  if(!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  return r.json();
}
async function maybe(url) { try{return await getJSON(url);}catch(_){return null;} }

function list(payload) {
  if(!payload) return [];
  if(Array.isArray(payload)) return payload;
  for(const k of ["items","facilities","forecasts","results"]) if(Array.isArray(payload[k])) return payload[k];
  return [];
}
function latest(items,keyName="facility_id") {
  const m=new Map();
  for(const x of items||[]) {
    const id=String(x?.[keyName]??"").trim();
    if(!id) continue;
    const ts=Date.parse(x.timestamp||x.created_at||x.forecast_timestamp||0)||0;
    const old=m.get(id);
    const ots=old ? (Date.parse(old.timestamp||old.created_at||old.forecast_timestamp||0)||0) : -1;
    if(!old || ts>=ots) m.set(id,x);
  }
  return m;
}
function risk(v) {
  const s=String(v||"").toLowerCase();
  if(s.includes("critical")||s.includes("high")) return "high";
  if(s.includes("medium")||s.includes("moderate")) return "medium";
  return "low";
}
function pqId(x){return String(x?.facility_id??x?.facility??x?.id??"").trim();}
function pqHorizon(x,h){const q=x?.horizons?.[h]||x?.forecast?.[h]||x?.[h]||{};return q&&typeof q==="object"?q:{};}

async function load() {
  const [readingPayload,forecastPayload,simPayload,pqPayload] = await Promise.all([
    maybe("/api/meter-readings?limit=750"),
    maybe("/api/live-forecasts?limit=750"),
    maybe("/api/simulation/state"),
    maybe("/api/power-quality-forecasts?limit=750")
  ]);

  const readings=latest(list(readingPayload));
  const forecasts=latest(list(forecastPayload));

  const simRows=Array.isArray(simPayload?.facilities)?simPayload.facilities:[];
  const sim=new Map(simRows.map(x=>[String(x.facility_id||"").trim(),x]).filter(x=>x[0]));

  const pqMap=new Map();
  for(const x of list(pqPayload)){const id=pqId(x);if(id)pqMap.set(id,x);}

  // Canonical facility universe:
  // 1) simulator/operational state when available because that is the configured institution set;
  // 2) otherwise live readings;
  // 3) otherwise demand forecasts.
  // Power-quality data may enrich a canonical facility but can never add a 23rd facility.
  let ids=[];
  if(sim.size) ids=[...sim.keys()];
  else if(readings.size) ids=[...readings.keys()];
  else ids=[...forecasts.keys()];

  const rows=[];
  for(const id of ids){
    const r=readings.get(id)||{};
    const f=forecasts.get(id)||{};
    const s=sim.get(id)||{};
    const q=pqMap.get(id)||{};
    const name=s.facility_name||r.facility_name||f.facility_name||id;

    const currentKva=n(r.kva??r.demand_kva??s.controlled_kva??s.baseline_kva??f.current_kva);
    const currentKwh=n(r.kwh??r.energy_kwh??r.interval_kwh);
    const currentPf=pf(r.power_factor??r.pf??q.current_power_factor??q.power_factor);
    const currentKvar=n(r.kvar??r.reactive_power_kvar??r.kvarh) ?? kvarFrom(currentKva,currentPf);

    const fh=f?.horizons?.[SDF.horizon]||{};
    const futureKva=n(fh.forecast_kva??fh.kva??(SDF.horizon==="30_minutes"?f.forecast_kva:null));

    const qh=pqHorizon(q,SDF.horizon);
    const futurePf=pf(qh.forecast_power_factor??qh.power_factor??qh.pf??q.forecast_power_factor);
    const futureKvar=n(qh.forecast_kvar??qh.kvar??qh.reactive_power_kvar??q.forecast_kvar) ?? kvarFrom(futureKva,futurePf);
    const directKwh=n(fh.forecast_kwh??fh.kwh??fh.energy_kwh);
    const futureKwh=directKwh ?? (()=>{const kw=kwFrom(futureKva,futurePf);return kw==null?null:kw*H[SDF.horizon].hours;})();

    const limit=n(f.facility_limit_kva??s.limit_kva??s.facility_limit_kva);
    let rr=risk(fh.risk??f.risk??s.risk);
    const basis=SDF.mode==="future"?futureKva:currentKva;
    if(limit!=null&&basis!=null){
      const u=basis/Math.max(limit,1e-9);
      if(u>=.95) rr="high";
      else if(u>=.85&&rr!=="high") rr="medium";
    }

    rows.push({
      id,name,currentKva,currentKwh,currentPf,currentKvar,
      futureKva,futureKwh,futurePf,futureKvar,
      limit,risk:rr,
      timestamp:r.timestamp||f.timestamp||simPayload?.current_timestamp||null
    });
  }

  rows.sort((a,b)=>a.name.localeCompare(b.name));
  return {facilities:rows, sim:simPayload};
}

function valueOf(f){
  const future=SDF.mode==="future";
  switch(SDF.metric){
    case"kva":return{value:future?f.futureKva:f.currentKva,unit:"kVA",digits:1};
    case"kwh":return{value:future?f.futureKwh:f.currentKwh,unit:"kWh",digits:1};
    case"pf":return{value:future?f.futurePf:f.currentPf,unit:"PF",digits:3};
    case"reactive":return{value:future?f.futureKvar:f.currentKvar,unit:"kVAr",digits:1};
  }
  return{value:null,unit:"",digits:1};
}
function totalOf(fs){
  if(SDF.metric==="pf"){
    const vals=fs.map(f=>({p:n(SDF.mode==="future"?f.futurePf:f.currentPf),s:n(SDF.mode==="future"?f.futureKva:f.currentKva)})).filter(x=>x.p!=null&&x.s!=null&&x.s>0);
    const den=vals.reduce((a,x)=>a+x.s,0);
    return den?vals.reduce((a,x)=>a+x.p*x.s,0)/den:null;
  }
  let valid=false,total=0;
  for(const f of fs){const x=n(valueOf(f).value);if(x!=null){valid=true;total+=x;}}
  return valid?total:null;
}

function create() {
  if(document.getElementById("demand-flow")) return;
  const nav=document.querySelector("nav.tabs");
  const main=document.querySelector("main");
  if(!nav||!main) return;

  const btn=document.createElement("button");
  btn.className="tab";
  btn.dataset.tab="demand-flow";
  btn.textContent="Demand flow";
  const home=nav.querySelector(".tab");
  home?home.insertAdjacentElement("afterend",btn):nav.appendChild(btn);

  const panel=document.createElement("section");
  panel.id="demand-flow";
  panel.className="panel";
  panel.innerHTML=`
    <div class="sdf-shell">
      <div class="sdf-header">
        <div class="sdf-heading">
          <h1>Demand Flow Overview</h1>
          <p><span class="sdf-live"></span><span id="sdf-subtitle">Live institution demand across the configured facilities</span></p>
        </div>
        <div class="sdf-mode">
          <button class="active" data-sdf-mode="current">Current</button>
          <button data-sdf-mode="future">Future</button>
        </div>
      </div>
      <div class="sdf-content">
        <div class="sdf-map">
          <div class="sdf-stage" id="sdf-stage"></div>
          <div class="sdf-bottom">
            <div class="sdf-bottom-label">Display metric</div>
            <div class="sdf-metrics">
              <button class="active" data-sdf-metric="kva">kVA</button>
              <button data-sdf-metric="kwh">kWh</button>
              <button data-sdf-metric="pf">PF</button>
              <button data-sdf-metric="reactive">Reactive</button>
            </div>
          </div>
        </div>
        <aside id="sdf-forecast" class="sdf-forecast" hidden>
          <div class="sdf-forecast-title">Forecast horizon</div>
          <div class="sdf-horizons">
            <button class="active" data-sdf-h="30_minutes">30 min</button>
            <button data-sdf-h="2_hours">2 hrs</button>
            <button data-sdf-h="6_hours">6 hrs</button>
            <button data-sdf-h="24_hours">24 hrs</button>
          </div>
          <div class="sdf-note">Demand uses SIMBA's multi-horizon forecast. PF and reactive values use the power-quality forecast when available. No UI values are hard-coded.</div>
        </aside>
      </div>
      <div class="sdf-footer"><span id="sdf-left">Waiting for facility data…</span><span id="sdf-right"></span></div>
    </div>`;
  main.appendChild(panel);

  btn.addEventListener("click",()=>{
    document.querySelectorAll("nav.tabs .tab").forEach(x=>x.classList.toggle("active",x===btn));
    document.querySelectorAll("main > .panel").forEach(x=>x.classList.toggle("active",x===panel));
    refresh(true);
    window.scrollTo(0,0);
  });

  panel.querySelectorAll("[data-sdf-mode]").forEach(b=>b.addEventListener("click",()=>{
    SDF.mode=b.dataset.sdfMode;
    panel.querySelectorAll("[data-sdf-mode]").forEach(x=>x.classList.toggle("active",x===b));
    document.getElementById("sdf-forecast").hidden=SDF.mode!=="future";
    render();
  }));
  panel.querySelectorAll("[data-sdf-metric]").forEach(b=>b.addEventListener("click",()=>{
    SDF.metric=b.dataset.sdfMetric;
    panel.querySelectorAll("[data-sdf-metric]").forEach(x=>x.classList.toggle("active",x===b));
    render();
  }));
  panel.querySelectorAll("[data-sdf-h]").forEach(b=>b.addEventListener("click",()=>{
    SDF.horizon=b.dataset.sdfH;
    panel.querySelectorAll("[data-sdf-h]").forEach(x=>x.classList.toggle("active",x===b));
    refresh(true);
  }));
}

function layoutNodes(fs,w,h){
  // Compact rectangular perimeter distribution.
  // Keeps all cards fully visible and leaves an uncluttered central campus.
  const cardW=128, cardH=52, padX=76, padTop=46, padBottom=82;
  const usableW=Math.max(300,w-2*padX);
  const usableH=Math.max(300,h-padTop-padBottom);

  const count=fs.length;
  const topN=Math.ceil(count*.23);
  const rightN=Math.ceil(count*.27);
  const bottomN=Math.ceil(count*.23);
  const leftN=count-topN-rightN-bottomN;

  const pts=[];
  let idx=0;

  function distribute(n,side){
    for(let j=0;j<n&&idx<count;j++,idx++){
      let x,y;
      const t=(j+1)/(n+1);
      if(side==="top"){x=padX+t*usableW;y=padTop;}
      else if(side==="right"){x=w-padX;y=padTop+t*usableH;}
      else if(side==="bottom"){x=w-padX-t*usableW;y=h-padBottom;}
      else{x=padX;y=h-padBottom-t*usableH;}

      // Small deterministic offset gives the "unique distances" feel without clutter.
      const wobble=((idx*37)%5-2)*5;
      if(side==="top"||side==="bottom") y+=wobble;
      else x+=wobble;
      pts.push({f:fs[idx],x,y});
    }
  }

  distribute(topN,"top");
  distribute(rightN,"right");
  distribute(bottomN,"bottom");
  distribute(leftN,"left");
  return pts;
}

function render(){
  if(!SDF.data) return;
  const stage=document.getElementById("sdf-stage");
  if(!stage) return;
  const fs=SDF.data.facilities||[];

  if(!fs.length){
    stage.innerHTML=`<div class="sdf-error">No configured facility readings or forecasts are currently available.</div>`;
    return;
  }

  const w=stage.clientWidth||1000,h=stage.clientHeight||680;
  const cx=w/2,cy=h*.49;
  const nodes=layoutNodes(fs,w,h);

  let svg=`<svg class="sdf-svg" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">`;
  nodes.forEach((p,i)=>{
    const dx=p.x-cx,dy=p.y-cy;
    const len=Math.max(1,Math.hypot(dx,dy));
    const startR=104;
    const endPad=68;
    const sx=cx+dx/len*startR, sy=cy+dy/len*startR;
    const ex=p.x-dx/len*endPad, ey=p.y-dy/len*endPad;
    const id=`sdf-path-${i}`;
    const high=p.f.risk==="high";
    svg+=`<path id="${id}" class="sdf-line${high?" high":""}" d="M ${sx.toFixed(1)} ${sy.toFixed(1)} L ${ex.toFixed(1)} ${ey.toFixed(1)}"/>`;
    // Two pulses per connection, always centre -> facility.
    for(let k=0;k<2;k++){
      const dur=(2.2+(i%6)*.18).toFixed(2);
      const begin=(-((i%7)*.17+k*(Number(dur)/2))).toFixed(2);
      svg+=`<circle r="${high?3.8:2.8}" class="sdf-pulse${high?" high":""}"><animateMotion dur="${dur}s" begin="${begin}s" repeatCount="indefinite"><mpath href="#${id}"/></animateMotion></circle>`;
    }
  });
  svg+="</svg>";

  const unit=SDF.metric==="kva"?"kVA":SDF.metric==="kwh"?"kWh":SDF.metric==="pf"?"PF":"kVAr";
  const digits=SDF.metric==="pf"?3:1;
  const total=totalOf(fs);
  const totalLabel=SDF.metric==="kva"?"Total institution demand":SDF.metric==="kwh"?"Total institution energy":SDF.metric==="pf"?"Institution power factor":"Total reactive power";
  const context=SDF.mode==="future"?`${H[SDF.horizon].label} forecast`:"Live";

  let html=svg+`
    <div class="sdf-centre">
      <div class="sdf-centre-inner">
        <div class="sdf-campus">🏛️</div>
        <div class="sdf-total-label">${esc(totalLabel)}</div>
        <div class="sdf-total">${fmt(total,digits)}</div>
        <div class="sdf-total-unit">${esc(unit)}</div>
        <div class="sdf-total-sub">${esc(context)} · ${fs.length} facilities</div>
      </div>
    </div>`;

  nodes.forEach(({f,x,y})=>{
    const m=valueOf(f);
    html+=`
      <div class="sdf-node${f.risk==="high"?" high-risk":""}" style="left:${x.toFixed(1)}px !important;top:${y.toFixed(1)}px !important" title="${esc(f.name)}">
        <span class="sdf-node-icon">🏢</span>
        <span class="sdf-node-name">${esc(f.name)}</span>
        <span class="sdf-node-value">${fmt(m.value,m.digits)} ${esc(m.unit)}</span>
        <span class="sdf-node-risk">${f.risk==="high"?"HIGH RISK · ":""}${SDF.mode==="future"?esc(H[SDF.horizon].label+" forecast"):"current"}</span>
      </div>`;
  });

  stage.innerHTML=html;
  const high=fs.filter(x=>x.risk==="high").length;
  document.getElementById("sdf-left").innerHTML=`<strong>${high}</strong> high-risk · <strong>${fs.length}</strong> configured facilities`;
  document.getElementById("sdf-right").textContent=`Updated ${new Date().toLocaleTimeString()} · SIMBA-EMS live APIs`;
  document.getElementById("sdf-subtitle").textContent=SDF.mode==="future"
    ? `${H[SDF.horizon].label} institutional forecast`
    : "Live institution demand across the configured facilities";
}

async function refresh(showError=false){
  try{SDF.data=await load();render();}
  catch(e){
    if(showError){
      const s=document.getElementById("sdf-stage");
      if(s)s.innerHTML=`<div class="sdf-error">Demand Flow could not load: ${esc(e.message)}</div>`;
    }
  }
}

function init(){
  create();
  refresh(false);
  window.addEventListener("resize",()=>{if(document.getElementById("demand-flow")?.classList.contains("active"))render();});
  SDF.refreshHandle=setInterval(()=>{
    if(document.getElementById("demand-flow")?.classList.contains("active"))refresh(false);
  },4000);
}

if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init,{once:true});
else init();
})();
