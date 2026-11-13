'use strict';
function shiftLoad(values,energy,cap){
  if(values.length<2 || values.some(v=>!Number.isFinite(v)||v<0)||![energy,cap].every(Number.isFinite)||energy<0||cap<0)throw new Error('Invalid scenario');
  const n=values.length,order=values.map((v,i)=>i).sort((a,b)=>values[a]-values[b]||a-b),count=Math.max(1,Math.floor(n/3));
  const sources=order.slice(-count),dests=order.slice(0,count),result=[...values],removed=Array(n).fill(0),added=Array(n).fill(0);let remaining=energy;
  while(remaining>1e-9){
    const src=sources.filter(i=>removed[i]<Math.min(cap,values[i])-1e-9),dst=dests.filter(i=>added[i]<cap-1e-9);if(!src.length||!dst.length)break;
    const i=src.reduce((a,b)=>result[b]>result[a]?b:a),j=dst.reduce((a,b)=>result[b]<result[a]?b:a);if(result[i]<=result[j]+1e-9)break;
    const move=Math.min(remaining,.1,cap-removed[i],values[i]-removed[i],cap-added[j],(result[i]-result[j])/2);if(move<=1e-9)break;
    result[i]-=move;result[j]+=move;removed[i]+=move;added[j]+=move;remaining-=move;
  }
  return {shifted:result,moved:removed.reduce((a,b)=>a+b,0),peakBefore:Math.max(...values),peakAfter:Math.max(...result),energyDifference:result.reduce((a,b)=>a+b,0)-values.reduce((a,b)=>a+b,0)};
}
if(typeof module!=='undefined')module.exports={shiftLoad};
if(typeof document!=='undefined'){
document.addEventListener('DOMContentLoaded',()=>{
  if(!window.GRID_DATA){document.querySelector('main').innerHTML='<p class="error">Study data could not load. Rebuild with python run.py, or open brief.html.</p>';return;}
  const D=window.GRID_DATA,R=D.results,P=R.primary_2025,fmt=(n,d=1)=>Number(n).toLocaleString('en-CA',{minimumFractionDigits:d,maximumFractionDigits:d}),$=s=>document.querySelector(s);
  const labels={forecast:'Weather + load model',weekly_naive:'Same hour, seven days earlier',two_day_naive:'Same hour, two days earlier',mean_2_and_7_day:'Mean of two- and seven-day profiles'};
  function cards(where,items){$(where).innerHTML=items.map((x,i)=>`<div class="kpi ${i===0?'highlight':''}"><span class="label">${x[0]}</span><span class="number">${x[1]}<span class="unit">${x[2]||''}</span></span><span class="sub">${x[3]||''}</span></div>`).join('');}
  document.querySelectorAll('.tabs button').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('.tabs button').forEach(x=>{x.classList.toggle('active',x===b);x.setAttribute('aria-selected',String(x===b));});document.querySelectorAll('.view').forEach(s=>s.hidden=s.id!==b.dataset.tab);}));
  $('#snapshot-stamp').textContent=`Built ${new Date(D.run.completed_at_utc).toLocaleString('en-CA',{timeZone:'America/Halifax',dateStyle:'medium',timeStyle:'short'})} Atlantic`;
  $('#coverage').textContent=fmt(P.forecast.interval_coverage_pct)+'%';
  const grouped=new Map();D.points.forEach(p=>{const day=p.local.slice(0,10);if(!grouped.has(day))grouped.set(day,[]);grouped.get(day).push(p);});
  const days=[...grouped.keys()].sort().reverse();
  $('#day-select').innerHTML=`<option value="latest">${D.latestMeta.target_day} · latest snapshot</option>`+days.map(d=>`<option value="${d}">${d} · backtest</option>`).join('');
  function profile(points,shifted){
    const w=1050,h=300,l=50,r=18,t=20,b=40,low=Math.max(0,Math.floor(Math.min(...points.map(p=>p.lo))/25)*25),high=Math.ceil(Math.max(...points.map(p=>p.hi))/25)*25;
    const times=points.map(p=>Date.parse(p.utc)),span=Math.max(3600000,times.at(-1)-times[0]);
    const x=i=>l+(times[i]-times[0])*(w-l-r)/span,y=v=>h-b-(v-low)*(h-b-t)/(high-low||1);
    const path=vals=>{let s='',pen=false;vals.forEach((v,i)=>{if(v===null||!Number.isFinite(v)){pen=false;return;}if(i&&times[i]-times[i-1]>3600000)pen=false;s+=`${pen?'L':'M'}${x(i).toFixed(2)},${y(v).toFixed(2)} `;pen=true;});return s;};
    let svg=`<svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg"><title>PEI hourly electricity demand and simulated load shifting</title>`;
    for(let i=0;i<=4;i++){const v=low+(high-low)*i/4;svg+=`<line x1="${l}" y1="${y(v)}" x2="${w-r}" y2="${y(v)}" stroke="#e7ece3"/><text x="${l-10}" y="${y(v)+4}" text-anchor="end">${fmt(v,0)}</text>`;}
    svg+='<text x="5" y="12">MW</text>';
    const groups=[];points.forEach((p,i)=>{if(!i||times[i]-times[i-1]>3600000)groups.push([]);groups.at(-1).push(i);});
    groups.forEach(g=>{const polygon=g.map(i=>`${x(i)},${y(points[i].hi)}`).concat([...g].reverse().map(i=>`${x(i)},${y(points[i].lo)}`)).join(' ');svg+=`<polygon points="${polygon}" fill="#dce9df" opacity=".85"/>`;});
    svg+=`<path d="${path(points.map(p=>p.y))}" stroke="#829186" stroke-width="2" fill="none"/><path d="${path(points.map(p=>p.p))}" stroke="#087f75" stroke-width="2.7" fill="none"/><path d="${path(shifted)}" stroke="#d97732" stroke-width="2" stroke-dasharray="6 4" fill="none"/>`;
    points.forEach((p,i)=>{if(i%3===0||i===points.length-1)svg+=`<text x="${x(i)}" y="${h-12}" text-anchor="middle">${p.local.slice(11,16)}</text>`;svg+=`<circle cx="${x(i)}" cy="${y(p.p)}" r="5" fill="transparent"><title>${p.local}: forecast ${fmt(p.p)} MW; observed ${p.y===null?'unavailable':fmt(p.y)+' MW'}</title></circle>`;});
    $('#profile-chart').innerHTML=svg+'</svg>';
  }
  function update(){const latest=$('#day-select').value==='latest',points=latest?D.latest:grouped.get($('#day-select').value);const energy=+$('#energy').value,cap=+$('#cap').value;
    $('#energy-value').textContent=`${energy} MWh`;$('#cap-value').textContent=`${cap} MW`;
    const sim=shiftLoad(points.map(p=>p.p),energy,cap),peak=points.reduce((a,b)=>a.p>b.p?a:b),valid=points.filter(p=>p.y!==null);
    cards('#forecast-kpis',[["Forecast peak",fmt(peak.p),'MW',`${peak.local.slice(11,16)} Atlantic`],["Available observed hours",String(valid.length),'',`${points.length} displayed forecast hours`],["Interval at predicted peak",`${fmt(peak.lo,0)}–${fmt(peak.hi,0)}`,'MW','Nominal 90%; inspect test coverage'],["Simulated peak change",fmt(sim.peakBefore-sim.peakAfter),'MW','Assumed flexible load; not verified savings']]);
    const complete=latest||points.length===D.expectedHours[$('#day-select').value];
    $('#day-note').textContent=(latest?`Reconstructed snapshot · issue ${D.latestMeta.origin_local} · `:'Quarterly walk-forward backtest · ')+`Forecasts issued at 18:00 Atlantic the preceding day.${complete?'':' Partial eligible day: scenario covers displayed hours only.'}`;
    $('#scenario-result').innerHTML=`<strong>${fmt(sim.moved)} MWh</strong> moved of ${energy} MWh requested.<br>Peak: ${fmt(sim.peakBefore)} → ${fmt(sim.peakAfter)} MW.<br><span class="small">Energy balance: ${fmt(Math.abs(sim.energyDifference),6)} MWh difference. Source and destination hours are disjoint. No modeled losses, comfort or equipment constraints.</span>`;
    profile(points,sim.shifted);
  }
  $('#day-select').addEventListener('change',update);$('#energy').addEventListener('input',update);$('#cap').addEventListener('input',update);update();
  cards('#performance-kpis',[["MAE reduction vs best baseline",fmt(R.primary_mae_improvement_pct),'%','Locked 2025 test'],["Model hourly MAE",fmt(P.forecast.mae_mw,2),'MW','Mean absolute error'],["Eligible 2025 hours",fmt(P.forecast.n,0),'',`${fmt(D.eligibility.primary_test.coverage_pct)}% of calendar hours`],["2026 extension MAE",fmt(R.extension_2026.forecast.mae_mw,2),'MW','Separate later-period results']]);
  $('#comparison-chart').innerHTML=Object.keys(labels).map(k=>`<div class="bar-row"><div class="bar-label"><span>${labels[k]}</span><b>${fmt(P[k].mae_mw,2)}</b></div><div class="bar-track"><div class="bar-fill ${k==='forecast'?'champion':''}" style="width:${100*P[k].mae_mw/25}%"></div></div></div>`).join('');
  $('#peak-results').innerHTML=`<div class="peak-grid"><div class="peak-cell"><b>${fmt(P.forecast.peak_precision*100)}%</b>precision</div><div class="peak-cell"><b>${fmt(P.forecast.peak_recall*100)}%</b>recall</div><div class="peak-cell"><b>${P.forecast.fp}</b>false alerts</div><div class="peak-cell"><b>${P.forecast.fn}</b>missed high-load hours</div></div>`;
  $('#fold-table').innerHTML=R.folds.map(f=>`<tr class="${f.test_first_day.startsWith('2026')?'extension':''}"><td>${f.test_first_day} → ${f.test_end_exclusive}*</td><td>${fmt(f.test_n,0)}</td><td>${fmt(f.metrics.forecast.mae_mw,2)} MW</td><td>${fmt(f.metrics.mean_2_and_7_day.mae_mw,2)} MW</td><td>${fmt(f.metrics.forecast.interval_coverage_pct)}%</td></tr>`).join('');
  const boot=R.primary_paired_bootstrap;$('#bootstrap-note').textContent=`Average daily MAE improvement: ${fmt(boot.daily_mean_mae_gain_mw,2)} MW. The approximate 95% interval is ${fmt(boot.ci95_mw[0],2)}–${fmt(boot.ci95_mw[1],2)} MW. Positive values favour the model over the strongest simple baseline.`;
  $('#worst-days').innerHTML=Object.entries(R.worst_days).slice(0,3).map(([d,v])=>`<div class="worst-day"><span>${d}</span><b>${fmt(v,2)} MW MAE</b></div>`).join('');
  cards('#audit-kpis',[["Source readings",fmt(D.audit.source_rows,0),'','Community-maintained archive'],["Quarantined readings",fmt(D.audit.rejected_rows,0),'','Invalid, ambiguous or potentially stale'],["2025 evaluation coverage",fmt(D.eligibility.primary_test.coverage_pct),'%','No interpolated targets'],["2026 evaluation coverage",fmt(D.eligibility.extension_test.coverage_pct),'%','Missing periods excluded explicitly']]);
  $('#load-range').textContent=`Downloaded archive: ${D.audit.first_source_wall_time} to ${D.audit.last_source_wall_time} (source wall time).`;
  $('#exclusions').textContent=Object.entries(D.audit.reasons).map(([r,n])=>`${r.replaceAll('_',' ')}: ${fmt(n,0)}`).join(' · ')+'.';
});}
