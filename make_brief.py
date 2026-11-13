"""Create a one-page review brief from measured results, without hand-edited numbers."""
import json
import shutil
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,KeepTogether
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parent
def main():
    r=json.loads((ROOT/'reports/results.json').read_text());a=json.loads((ROOT/'reports/data_audit.json').read_text());e=json.loads((ROOT/'reports/eligibility.json').read_text())
    p=r['primary_2025'];m=p['forecast'];b=p[r['primary_best_baseline']];ext=r['extension_2026']['forecast']
    ink=colors.HexColor('#193e3a');teal=colors.HexColor('#087f75')
    title=ParagraphStyle('title',fontName='Helvetica-Bold',fontSize=25,leading=28,textColor=ink,spaceAfter=7)
    sub=ParagraphStyle('sub',fontName='Helvetica',fontSize=8.5,leading=12,textColor=colors.HexColor('#586a66'),spaceAfter=17)
    heading=ParagraphStyle('heading',fontName='Helvetica-Bold',fontSize=11,leading=14,textColor=teal,spaceBefore=13,spaceAfter=6)
    body=ParagraphStyle('body',fontName='Helvetica',fontSize=9.2,leading=13,textColor=ink,spaceAfter=7)
    small=ParagraphStyle('small',parent=body,fontSize=7.6,leading=10)
    out=ROOT/'reports/decision_brief.pdf'
    doc=SimpleDocTemplate(str(out),pagesize=(612,792),leftMargin=43,rightMargin=43,topMargin=36,bottomMargin=36,title='PEI Grid Forecast - Decision Brief',author='Faris Elsabah')
    story=[Paragraph('PEI Grid Forecast',title),Paragraph('DECISION BRIEF  /  Faris Elsabah  /  Independent educational research<br/>Source snapshot: '+a['last_source_wall_time']+' Atlantic wall time',sub)]
    def section(h,t,style=body):story.extend([Paragraph(h,heading),Paragraph(t,style)])
    section('The decision','Proceed to a small, prospectively logged forecasting pilot after practitioner review. This retrospective study supports further testing; it does not establish operational readiness or cost savings.')
    cells=[['2025 MODEL ERROR','ERROR REDUCTION','TEST COVERAGE'],[f"{m['mae_mw']:.2f} MW",f"{r['primary_mae_improvement_pct']:.1f}%",f"{e['primary_test']['coverage_pct']:.1f}%"],['Hourly mean absolute error','Against strongest simple baseline',f"{m['n']:,} identical scored hours"]]
    table=Table(cells,colWidths=[175,175,176]);table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#edf2e9')),('TEXTCOLOR',(0,0),(-1,-1),ink),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,0),8),('FONTNAME',(0,1),(-1,1),'Helvetica-Bold'),('FONTSIZE',(0,1),(-1,1),21),('FONTSIZE',(0,2),(-1,2),7.5),('LEFTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]));story.extend([Spacer(1,8),table])
    section('What was built','A daily 18:00 Atlantic forecast of the following local day\'s hourly mean sampled PEI load. A Python pipeline audits the electricity archive, joins older GFS temperature forecasts, builds explicitly timed features, refits quarterly, and exports an interactive forecast and energy-conserving scenario tool.')
    section('Evidence, including the weaknesses',f"Locked 2025 test: MAE <b>{m['mae_mw']:.2f} MW</b> versus <b>{b['mae_mw']:.2f} MW</b> for the two-/seven-day mean baseline; weekly naive {p['weekly_naive']['mae_mw']:.2f} MW. RMSE {m['rmse_mw']:.2f} MW; weighted absolute percentage error {m['wape_pct']:.2f}%. Bias {m['bias_mw']:.2f} MW: the model underpredicts on average.<br/><br/>Nominal 90% intervals achieved <b>{m['interval_coverage_pct']:.1f}% coverage</b>. Statistical high-load precision {m['peak_precision']*100:.1f}%, recall {m['peak_recall']*100:.1f}%. Separate 2026 extension: {ext['n']:,} hours and {ext['mae_mw']:.2f} MW MAE. Thresholds are training percentiles, not grid limits.")
    section('Validation and next action','Four candidates selected using January-June 2024 only. Separate calibration windows precede each test quarter; all methods share the same eligible hours. Review underprediction, missed high-load hours and interval undercoverage. Log new forecasts before outcomes arrive and ask a utility practitioner to check the target and assumed publication delay.')
    section('Limits on interpretation',f"{a['source_rows']:,} archived readings; {a['rejected_rows']:,} quarantined. No target interpolation. Historical timezone and one-hour load-publication latency are assumptions; exact release vintages are unavailable. Weather is a fixed-48h archive proxy at Charlottetown, not the exact latest issue run. Scenario flexibility is assumed. No measured savings, adoption, grid control or utility endorsement.",small)
    section('Sources and audit trail','Electricity: energy.reinvented.net (Peter Rukavina / Reinvented; provincial indicators). Definitions: princeedwardisland.ca/en/feature/renewable-energy-indicators. Weather: open-meteo.com/en/docs/previous-runs-api (CC BY 4.0; API terms separate). Exact metrics, predictions, exclusions and hashes accompany the project in reports/ and protocol.json.',small)
    doc.build(story)
    pages=len(PdfReader(out).pages)
    if pages!=1:raise RuntimeError(f'Brief must fit one page; got {pages}')
    if (ROOT/'dist').exists():shutil.copyfile(out,ROOT/'dist'/out.name)
    print(f'Created and checked {out.name}: {pages} page')

if __name__=='__main__':main()
