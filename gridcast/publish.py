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
    rev=results['revision'];v=rev['primary_2025'];w=rev['comparisons'][0]
    feb=next(x for x in eligibility['monthly'] if x['month']=='2025-02')
    return f"""# PEI Grid Forecast - professor review brief

**Faris Elsabah | Independent educational research | Revised 16 November 2026 | Frozen source through {audit['last_source_wall_time']} Atlantic wall time**

## Research question
At 18:00 Atlantic, predict the following local day's hourly mean sampled PEI load using historical load, calendar information and archived fixed-48h GFS temperature forecasts. This is a forecasting/regression study, not causal inference or a utility operating tool.

## Fair benchmark comparison
All methods use the same {m['n']:,} eligible 2025 hours ({eligibility['primary_test']['coverage_pct']:.2f}% of the year). Fixed candidate selection used January-June 2024. The original quarterly method remains the reference; the new monthly method is an exploratory retrospective revision after the original test results were inspected.

| Method | 2025 MAE (MW) | RMSE (MW) |
|---|---:|---:|
| Original quarterly gradient boosting | {m['mae_mw']:.2f} | {m['rmse_mw']:.2f} |
| Ridge linear regression, alpha=100 | {p['ridge_linear']['mae_mw']:.2f} | {p['ridge_linear']['rmse_mw']:.2f} |
| Mean of two-/seven-day profiles | {p['mean_2_and_7_day']['mae_mw']:.2f} | {p['mean_2_and_7_day']['rmse_mw']:.2f} |
| Two-day naive | {p['two_day_naive']['mae_mw']:.2f} | {p['two_day_naive']['rmse_mw']:.2f} |
| Weekly naive | {p['weekly_naive']['mae_mw']:.2f} | {p['weekly_naive']['rmse_mw']:.2f} |
| Monthly boosting revision (exploratory) | {v['mae_mw']:.2f} | {v['rmse_mw']:.2f} |

Ridge is a regularized linear benchmark, with training-only scaling and the same features, quarterly training windows and target hours as the original boosting method. It is not ordinary least squares or an inferential coefficient analysis. Original boosting has {100*(1-m['mae_mw']/p['ridge_linear']['mae_mw']):.1f}% lower MAE than ridge and {results['primary_mae_improvement_pct']:.1f}% lower than the strongest simple baseline.

## Winter investigation: improved, not solved
The original model left the most recent 180 days out of point-model fitting to reserve a calibration window. The revision refits monthly using recent available labels; intervals use signed errors from earlier monthly forecasts, restricted to the prior 365 days. This jointly changes refit frequency, training recency and calibration, so the comparison cannot isolate their individual effects.

January-March 2025: MAE {w['original']['mae_mw']:.2f} -> {w['monthly_revision']['mae_mw']:.2f} MW; nominal-90% interval coverage {w['original']['interval_coverage_pct']:.1f}% -> {w['monthly_revision']['interval_coverage_pct']:.1f}%; mean width {w['original']['interval_mean_width_mw']:.2f} -> {w['monthly_revision']['interval_mean_width_mw']:.2f} MW; interval score {w['original']['interval_score_90_mw']:.2f} -> {w['monthly_revision']['interval_score_90_mw']:.2f} MW (lower is better). Annual revised coverage is {v['interval_coverage_pct']:.1f}% versus {m['interval_coverage_pct']:.1f}%, with narrower average width ({v['interval_mean_width_mw']:.2f} versus {m['interval_mean_width_mw']:.2f} MW). Winter undercoverage remains; do not claim calibration is fixed. In the 2026 January-March extension, revised MAE improves slightly but RMSE and high-load recall worsen; all monthly results are retained.

## Corrections and uncertainty
A raw-data flatline rule previously used a run's future end to reject earlier readings. It now flags a reading only after four hours of observed repetition, resets across gaps over 30 minutes, and never backdates rejection. An end-to-end raw-future-mutation test verifies input-prefix invariance. Correcting this defect did not change the original 2025/26 scored predictions in this snapshot. The first four hours of a freeze remain undetectable by this rule.

February 2025 has only {feb['eligible_hours']}/{feb['calendar_hours']} hours ({feb['coverage_pct']:.1f}%) eligible. Excluded periods are not imputed or represented by these scores. Error autocorrelation at lag 1 is {results['residual_diagnostics']['lag_correlation']['1']:.3f}; hours are not independent trials. Seven-, 14- and 28-day block bootstrap sensitivity is reported for unweighted daily MAE gains, not the hourly percentage improvement. No naive regression p-values are reported.

## Review request and next step
Review the linear benchmark's specification, temporal validation and treatment of seasonal uncertainty/missingness. The revision is a candidate for future validation, not evidence from a newly untouched holdout. Record forecasts before outcomes arrive before making operational claims. Historical publication vintages and timezone are not fully verified; one-hour load latency is assumed; Charlottetown weather is a single-point proxy. No measured savings, deployment, endorsement or causal attribution is claimed.

## Sources and reproducibility
Electricity: Peter Rukavina / Reinvented, https://energy.reinvented.net/ (provincial indicators). Weather: Open-Meteo GFS, https://open-meteo.com/en/docs/previous-runs-api (CC BY 4.0; API terms separate). Raw snapshots remain out of Git. Protocol v2, archived v1, every prediction, monthly eligibility, revision fold cutoffs and source/output hashes accompany the repository: https://github.com/FBELSABAH/pei-grid-forecast.
"""

def figure(predictions,results):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.labelcolor':'#193e3a','text.color':'#193e3a'})
    fig,axes=plt.subplots(1,2,figsize=(12,4),gridspec_kw={'width_ratios':[1,1.8]})
    p=results['primary_2025'];names=['Original boosting','Ridge linear','2-/7-day mean','Two-day naive','Weekly naive'];keys=['forecast','ridge_linear','mean_2_and_7_day','two_day_naive','weekly_naive']
    vals=[p[k]['mae_mw'] for k in keys]
    axes[0].barh(names,vals,color=['#087f75','#d4a46a','#b9cbbf','#b9cbbf','#b9cbbf']);axes[0].invert_yaxis();axes[0].set_xlabel('Hourly MAE (MW) - lower is better');axes[0].set_xlim(0,max(vals)*1.2)
    for i,v in enumerate(vals):axes[0].text(v+.3,i,f'{v:.2f}',va='center',fontsize=9)
    axes[0].set_title(f"2025 reanalysis | {p['forecast']['n']:,} eligible hours",loc='left',fontsize=11)
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
    original=results['monthly'][:12];revision=results['revision']['monthly'][:12]
    eligibility=json.loads((ROOT/'reports/eligibility.json').read_text())['monthly'][:12]
    fig,axes=plt.subplots(2,2,figsize=(11,7))
    x=np.arange(1,13)
    for ax,key,label in [(axes[0,0],'mae_mw','Hourly MAE (MW)'),(axes[0,1],'interval_coverage_pct','Interval coverage (%)'),(axes[1,0],'interval_mean_width_mw','Mean interval width (MW)')]:
        ax.plot(x,[m['forecast'][key] for m in original],'-o',color='#687e76',label='Original quarterly',markersize=4)
        ax.plot(x,[m[key] for m in revision],'-o',color='#087f75',label='Monthly revision (exploratory)',markersize=4)
        ax.set_ylabel(label);ax.set_xticks(x);ax.grid(axis='y',alpha=.2)
    axes[0,0].legend(fontsize=8,frameon=False)
    axes[0,1].axhline(90,linestyle='--',color='#b56c33',label='Nominal 90%');axes[0,1].set_ylim(40,102)
    axes[1,1].bar(x,[m['coverage_pct'] for m in eligibility],color=['#b56c33' if m['coverage_pct']<80 else '#b9cbbf' for m in eligibility])
    axes[1,1].set_ylabel('Eligible / calendar hours (%)');axes[1,1].set_xticks(x);axes[1,1].set_ylim(0,105)
    feb=eligibility[1]['coverage_pct']
    axes[1,1].text(2,min(100,feb+5),f'February: {feb:.1f}%',ha='center',fontsize=8)
    for ax in axes.flat:ax.set_xlabel('2025 calendar month')
    fig.suptitle('Seasonal weaknesses remain visible | same eligible hours, retrospective revision',fontsize=12)
    fig.tight_layout();fig.savefig(ROOT/'reports/seasonal_diagnostics.png',dpi=170,bbox_inches='tight');plt.close(fig)


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
    lines=[]; table_open=False
    for line in brief.splitlines():
        if line.startswith('|'):
            if not table_open:lines.append('<table>');table_open=True
            if set(line.replace('|','').replace(':','').strip()) <= set('- '):continue
            cells=[html.escape(c.strip()) for c in line.strip('|').split('|')]
            lines.append('<tr>'+''.join('<td>'+c+'</td>' for c in cells)+'</tr>');continue
        if table_open:lines.append('</table>');table_open=False
        line=html.escape(line)
        if line.startswith('### '):lines.append('<h3>'+line[4:]+'</h3>')
        elif line.startswith('## '):lines.append('<h2>'+line[3:]+'</h2>')
        elif line.startswith('# '):lines.append('<h1>'+line[2:]+'</h1>')
        elif line.startswith('- '):lines.append('<p>'+line[2:]+'</p>')
        elif line:lines.append('<p>'+line.replace('**','')+'</p>')
    (dist/'brief.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>PEI Grid Forecast - decision brief</title><link rel="stylesheet" href="style.css"><main style="max-width:900px;padding-top:40px"><a href="index.html">Back to the application</a>'+''.join(lines)+'<p><a href="decision_brief.pdf">Download the one-page PDF brief</a></p></main></html>')
    for name in ['results.json','data_audit.json','backtest_predictions.csv','folds.csv','run_manifest.json','winter_revision.json','revision_predictions.csv','monthly_eligibility.csv']:shutil.copyfile(ROOT/'reports'/name,dist/name)
    shutil.copyfile(ROOT/'protocol.json',dist/'protocol.json')
    figure(predictions,results)
    for name in ['evidence.png','seasonal_diagnostics.png']:shutil.copyfile(ROOT/'reports'/name,dist/name)
    # The PDF is generated by a separate command so the project also works without PDF tools.
    pdf=ROOT/'reports/decision_brief.pdf'
    if pdf.exists():shutil.copyfile(pdf,dist/pdf.name)

if __name__=='__main__':
    p=pd.read_csv(ROOT/'reports/backtest_predictions.csv',index_col=0,parse_dates=[0]);p.index=pd.to_datetime(p.index,utc=True)
    latest=pd.read_csv(ROOT/'reports/latest_forecast.csv',index_col=0,parse_dates=[0]);latest.index=pd.to_datetime(latest.index,utc=True)
    read=lambda f:json.loads((ROOT/'reports'/f).read_text())
    publish(p,latest,read('results.json'),read('data_audit.json'),read('eligibility.json'))
