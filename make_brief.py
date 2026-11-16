"""One-page professor review brief, populated exclusively from computed artifacts."""
import json
import shutil
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parent

def main():
    read=lambda n:json.loads((ROOT/'reports'/n).read_text())
    r=read('results.json');a=read('data_audit.json');e=read('eligibility.json')
    p=r['primary_2025'];m=p['forecast'];v=r['revision']['primary_2025'];w=r['revision']['comparisons'][0]
    feb=next(x for x in e['monthly'] if x['month']=='2025-02')
    ink=colors.HexColor('#193e3a');teal=colors.HexColor('#087f75')
    title=ParagraphStyle('title',fontName='Helvetica-Bold',fontSize=24,leading=27,textColor=ink,spaceAfter=5)
    sub=ParagraphStyle('sub',fontName='Helvetica',fontSize=8.2,leading=11,textColor=colors.HexColor('#586a66'),spaceAfter=9)
    heading=ParagraphStyle('heading',fontName='Helvetica-Bold',fontSize=10.5,leading=13,textColor=teal,spaceBefore=9,spaceAfter=4)
    body=ParagraphStyle('body',fontName='Helvetica',fontSize=9,leading=12,textColor=ink,spaceAfter=5)
    small=ParagraphStyle('small',parent=body,fontSize=7.6,leading=10)
    out=ROOT/'reports/decision_brief.pdf'
    doc=SimpleDocTemplate(str(out),pagesize=(612,792),leftMargin=40,rightMargin=40,topMargin=29,bottomMargin=29,title='PEI Grid Forecast - Professor Review Brief',author='Faris Elsabah')
    story=[Paragraph('PEI Grid Forecast',title),Paragraph('PROFESSOR REVIEW BRIEF  /  Faris Elsabah  /  Revised 16 November 2026<br/>Independent educational research. Frozen source: '+a['last_source_wall_time']+' Atlantic wall time.',sub)]
    def section(h,t,style=body):story.extend([Paragraph(h,heading),Paragraph(t,style)])
    section('Question and evaluation','At 18:00 Atlantic, forecast the following local day\'s hourly mean sampled PEI load using historical load, calendar features and archived fixed-48h GFS temperature forecasts. Compare forecasting error, not causal effects. Candidate selection used January-June 2024; all methods below share <b>'+f"{m['n']:,} eligible 2025 hours ({e['primary_test']['coverage_pct']:.2f}% of the year)</b>.")
    cells=[['METHOD','MAE (MW)','RMSE (MW)'],['Original quarterly gradient boosting',f"{m['mae_mw']:.2f}",f"{m['rmse_mw']:.2f}"],['Ridge linear regression (alpha = 100)',f"{p['ridge_linear']['mae_mw']:.2f}",f"{p['ridge_linear']['rmse_mw']:.2f}"],['Mean of two- / seven-day profiles',f"{p['mean_2_and_7_day']['mae_mw']:.2f}",f"{p['mean_2_and_7_day']['rmse_mw']:.2f}"],['Two-day naive',f"{p['two_day_naive']['mae_mw']:.2f}",f"{p['two_day_naive']['rmse_mw']:.2f}"],['Weekly naive',f"{p['weekly_naive']['mae_mw']:.2f}",f"{p['weekly_naive']['rmse_mw']:.2f}"],['Monthly boosting revision (exploratory)',f"{v['mae_mw']:.2f}",f"{v['rmse_mw']:.2f}"]]
    table=Table(cells,colWidths=[342,95,95]);table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),ink),('TEXTCOLOR',(0,0),(-1,0),colors.white),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#edf2e9'),colors.white]),('TEXTCOLOR',(0,1),(-1,-1),ink),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTNAME',(0,1),(-1,-1),'Helvetica'),('FONTSIZE',(0,0),(-1,-1),8.5),('ALIGN',(1,0),(-1,-1),'RIGHT'),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]));story.extend([Spacer(1,5),table,Spacer(1,6)])
    story.append(Paragraph('Ridge uses training-only scaling and the same features/training windows as original boosting. It is regularized linear prediction, not ordinary least squares or coefficient inference. Original boosting reduces MAE by '+f"{100*(1-m['mae_mw']/p['ridge_linear']['mae_mw']):.1f}% versus ridge; {r['primary_mae_improvement_pct']:.1f}% versus the strongest simple baseline.",body))
    section('Winter: improved, still below the interval target',f"The original point model excludes its latest 180 days for separate calibration. The revision refits monthly with recent available labels; intervals use signed errors from earlier monthly forecasts over the prior 365 days. January-March 2025 MAE: <b>{w['original']['mae_mw']:.2f} to {w['monthly_revision']['mae_mw']:.2f} MW</b>. Nominal-90% coverage: <b>{w['original']['interval_coverage_pct']:.1f}% to {w['monthly_revision']['interval_coverage_pct']:.1f}%</b>; mean width {w['original']['interval_mean_width_mw']:.2f} to {w['monthly_revision']['interval_mean_width_mw']:.2f} MW. Interval score improves {w['original']['interval_score_90_mw']:.2f} to {w['monthly_revision']['interval_score_90_mw']:.2f} (lower is better). Annual coverage improves to {v['interval_coverage_pct']:.1f}% with narrower mean width ({v['interval_mean_width_mw']:.2f} vs {m['interval_mean_width_mw']:.2f} MW). Winter is <b>not solved</b>.")
    story.append(Paragraph('<b>Interpretation:</b> this is one post-audit retrospective revision after inspecting 2025/26 results, not a new untouched test. Several design elements change together. In January-March 2026, revised MAE improves slightly but RMSE and high-load recall worsen. All results are retained; prospective validation is still required.',body))
    section('Audit correction and statistical limits',f"Fixed a flatline filter that used a future run end to reject earlier readings. It now flags only after four observed hours, resets across gaps, and never backdates rejection. A raw-future-mutation regression test passes; original scored predictions in this snapshot are unchanged. The first four hours of a freeze remain undetectable. February 2025 coverage is only <b>{feb['coverage_pct']:.1f}%</b>; no target imputation. Errors are serially dependent (lag-1 correlation {r['residual_diagnostics']['lag_correlation']['1']:.3f}); 7/14/28-day block sensitivity is reported for daily MAE gains. No independent-hour inference or naive coefficient p-values.")
    section('What I would like reviewed','The linear benchmark specification, temporal validation, and treatment of seasonal uncertainty and missingness. Source publication vintages are unavailable; one-hour latency and historical timezone are assumptions. Charlottetown weather is a single-point proxy. No measured savings, deployment or utility endorsement is claimed.',body)
    section('Sources and reproducibility','Electricity: energy.reinvented.net (Peter Rukavina / Reinvented; provincial indicators). Weather: open-meteo.com/en/docs/previous-runs-api (CC BY 4.0; API terms separate). Protocol v2, archived v1, predictions, monthly exclusions and fold cutoffs:<br/><link href="https://github.com/FBELSABAH/pei-grid-forecast" color="#087f75">github.com/FBELSABAH/pei-grid-forecast</link>',small)
    doc.build(story)
    pages=len(PdfReader(out).pages)
    if pages!=1:raise RuntimeError(f'Brief must fit one page; got {pages}')
    if (ROOT/'dist').exists():shutil.copyfile(out,ROOT/'dist'/out.name)
    print(f'Created and checked {out.name}: {pages} page')
if __name__=='__main__':main()
