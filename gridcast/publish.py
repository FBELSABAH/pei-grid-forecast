"""Generate the browser application, evidence figure and readable decision brief."""
from __future__ import annotations
import html
import json
import shutil
from pathlib import Path
import numpy as np
import pandas as pd
from .data import ROOT,TZ,write_json
from .features import target_hours

def points(frame):
    return [{"utc":t.isoformat(),"local":pd.Timestamp(r.target_local).isoformat(),"p":round(float(r.forecast),6),
        "y":round(float(r.actual),6) if pd.notna(r.actual) else None,
        "lo":round(float(r.lower),6),"hi":round(float(r.upper),6)} for t,r in frame.iterrows()]

def brief_text(results,audit,eligibility):
    p=results["primary_2025"];m=p["forecast"];b=p[results["primary_best_baseline"]];e=results["extension_2026"]["forecast"]
    return f"""# PEI Grid Forecast - decision brief

**Independent educational research | Faris Elsabah | Snapshot: {audit['last_source_wall_time']} Atlantic source wall time**

## Decision and recommendation

The model is a promising candidate for a small, prospectively logged forecasting pilot. It is not ready to control electricity equipment or support cost-saving claims. Start by having a utility or energy-software practitioner review the target definition, data latency and failure periods.

## What was measured

At 18:00 Atlantic, predict the following local day's hourly mean sampled on-island load. The electricity archive contains {audit['source_rows']:,} observations from November 2012 onward. Feature development starts in 2021 to match the weather archive. Select among four candidates using January-June 2024 only; calibrate uncertainty on separate earlier observations; refit quarterly without tuning on the 2025-26 test.

## Main result: locked 2025 test

- {m['n']:,} identical scored hours across all methods: {eligibility['primary_test']['coverage_pct']:.1f}% of the calendar year.
- Model MAE: **{m['mae_mw']:.2f} MW**, versus **{b['mae_mw']:.2f} MW** for the strongest simple baseline (mean of two- and seven-day profiles): **{results['primary_mae_improvement_pct']:.1f}% lower error**.
- Weekly-naive MAE: {p['weekly_naive']['mae_mw']:.2f} MW. RMSE: {m['rmse_mw']:.2f} MW. Weighted absolute percentage error: {m['wape_pct']:.2f}%. Bias: {m['bias_mw']:.2f} MW (underprediction).
- Nominal 90% intervals covered **{m['interval_coverage_pct']:.1f}%**, below their nominal target.
- High-load precision: {m['peak_precision']*100:.1f}%; recall: {m['peak_recall']*100:.1f}%. Thresholds use training-load percentiles, not utility capacity.
- Separate 2026 extension: {e['n']:,} hours, **{e['mae_mw']:.2f} MW MAE**; {eligibility['extension_test']['coverage_pct']:.1f}% calendar coverage.

## Where to investigate

Inspect underprediction, interval undercoverage, high-load misses and the largest-error days before a pilot. Compare prospective performance with the same baselines. Ask a practitioner whether the chosen issue time and province-wide signal match an actual planning decision. The load-shifting tool illustrates energy-conserving scenarios only; flexible capacity is assumed.

## What the data cannot establish

The archive is community-maintained, not settlement-meter data. Source wall time is assumed historically Atlantic; the current Unix timestamp supports this but does not prove every historical timestamp. We quarantine ambiguous DST observations, nonpositive values and four-hour flat runs; require three samples spanning 30 minutes per hour; never interpolate targets. Electricity release vintages are unavailable, so the assumed one-hour latency buffer cannot establish historical publication availability. Weather uses older fixed-48h GFS forecasts, not future observed weather or exact latest issue runs. No stakeholder adoption, actual savings, emissions reduction, operating-limit prediction or utility endorsement has been demonstrated.

## Sources and reproducibility

- Peter Rukavina / Reinvented electricity archive: https://energy.reinvented.net/
- Government of PEI indicator definitions: https://www.princeedwardisland.ca/en/feature/renewable-energy-indicators
- Open-Meteo GFS forecast archive: https://open-meteo.com/en/docs/previous-runs-api (weather data CC BY 4.0; API terms apply separately).
- See protocol.json, reports/results.json, reports/backtest_predictions.csv and reports/run_manifest.json for exact methods, all predictions and fingerprints. Raw source snapshots are not redistributed in Git; electricity archive reuse terms were not explicitly stated on the source landing page.
"""

def figure(predictions,results):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.labelcolor':'#193e3a','text.color':'#193e3a'})
    fig,axes=plt.subplots(1,2,figsize=(12,4),gridspec_kw={'width_ratios':[1,1.8]})
    p=results['primary_2025'];names=['Model','2-/7-day mean','Two-day naive','Weekly naive'];keys=['forecast','mean_2_and_7_day','two_day_naive','weekly_naive']
    vals=[p[k]['mae_mw'] for k in keys]
    axes[0].barh(names,vals,color=['#087f75','#b9cbbf','#b9cbbf','#b9cbbf']);axes[0].invert_yaxis();axes[0].set_xlabel('Hourly MAE (MW) - lower is better');axes[0].set_xlim(0,max(vals)*1.2)
    for i,v in enumerate(vals):axes[0].text(v+.3,i,f'{v:.2f}',va='center',fontsize=9)
    axes[0].set_title(f"Locked 2025 test | {p['forecast']['n']:,} eligible hours",loc='left',fontsize=11)
    # Fixed illustrative week, chosen by calendar before plotting, not lowest error.
    week=predictions[(predictions.day>='2025-01-13')&(predictions.day<'2025-01-20')]
    x=week.index.tz_convert(TZ)
    axes[1].fill_between(x,week.lower,week.upper,color='#dce9df',label='Nominal 90% interval')
    axes[1].plot(x,week.actual,color='#7e8c80',linewidth=1,label='Observed')
    axes[1].plot(x,week.forecast,color='#087f75',linewidth=1.3,label='Forecast')
    axes[1].set_title('Example week: 13-19 January 2025',loc='left',fontsize=11);axes[1].set_ylabel('Mean sampled load (MW)');axes[1].legend(loc='upper left',fontsize=8,frameon=False)
    import matplotlib.dates as mdates
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter('%b %d',tz=TZ))
    fig.suptitle('PEI Grid Forecast | chronological backtest, no interpolated targets',fontsize=13,x=.05,ha='left')
    fig.tight_layout();fig.savefig(ROOT/'reports/evidence.png',dpi=180,bbox_inches='tight');plt.close(fig)

def publish(predictions,latest,results,audit,eligibility):
    dist=ROOT/'dist';dist.mkdir(exist_ok=True)
    for name in ['index.html','style.css','app.js']:shutil.copyfile(ROOT/'web'/name,dist/name)
    manifest=json.loads((ROOT/'reports/run_manifest.json').read_text())
    meta=json.loads((ROOT/'reports/latest_metadata.json').read_text())
    meta['origin_local']=str(pd.Timestamp(meta['origin_utc']).tz_convert(TZ))
    payload={'results':results,'audit':audit,'eligibility':{k:v for k,v in eligibility.items() if k!='excluded_origin_days'},
             'run':manifest,'points':points(predictions),'latest':points(latest),'latestMeta':meta,
             'expectedHours':{day:len(target_hours(day)) for day in predictions.day.unique()}}
    (dist/'data.js').write_text('window.GRID_DATA = '+json.dumps(payload,allow_nan=False,default=str,separators=(',',':'))+';\n')
    brief=brief_text(results,audit,eligibility);(ROOT/'reports/decision_brief.md').write_text(brief)
    # A deliberately simple no-JavaScript reading and printing version.
    lines=[]
    for line in brief.splitlines():
        line=html.escape(line)
        if line.startswith('### '):lines.append('<h3>'+line[4:]+'</h3>')
        elif line.startswith('## '):lines.append('<h2>'+line[3:]+'</h2>')
        elif line.startswith('# '):lines.append('<h1>'+line[2:]+'</h1>')
        elif line.startswith('- '):lines.append('<p>'+line[2:]+'</p>')
        elif line:lines.append('<p>'+line.replace('**','')+'</p>')
    (dist/'brief.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>PEI Grid Forecast - decision brief</title><link rel="stylesheet" href="style.css"><main style="max-width:900px;padding-top:40px"><a href="index.html">Back to the application</a>'+''.join(lines)+'<p><a href="decision_brief.pdf">Download the one-page PDF brief</a></p></main></html>')
    for name in ['results.json','data_audit.json','backtest_predictions.csv','folds.csv','run_manifest.json']:shutil.copyfile(ROOT/'reports'/name,dist/name)
    shutil.copyfile(ROOT/'protocol.json',dist/'protocol.json')
    figure(predictions,results)
    shutil.copyfile(ROOT/'reports/evidence.png',dist/'evidence.png')
    # The PDF is generated by a separate command so the project also works without PDF tools.
    pdf=ROOT/'reports/decision_brief.pdf'
    if pdf.exists():shutil.copyfile(pdf,dist/pdf.name)

if __name__=='__main__':
    p=pd.read_csv(ROOT/'reports/backtest_predictions.csv',index_col=0,parse_dates=[0]);p.index=pd.to_datetime(p.index,utc=True)
    latest=pd.read_csv(ROOT/'reports/latest_forecast.csv',index_col=0,parse_dates=[0]);latest.index=pd.to_datetime(latest.index,utc=True)
    read=lambda f:json.loads((ROOT/'reports'/f).read_text())
    publish(p,latest,read('results.json'),read('data_audit.json'),read('eligibility.json'))
