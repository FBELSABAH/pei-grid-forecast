import json
import subprocess
import shutil
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from gridcast.metrics import shift_load,metrics
from gridcast.data import ROOT

def test_javascript_scenario_matches_python():
    if not shutil.which('node'):pytest.skip('Node not installed')
    cases=[]
    for n in [23,24,25]:
        for energy in [0,20,100]:
            a=(150+50*np.sin(np.arange(n)/3)).tolist();cases.append({'values':a,'energy':energy,'cap':5})
    script="const {shiftLoad}=require('./web/app.js'); const fs=require('fs'); const a=JSON.parse(fs.readFileSync(0,'utf8'));process.stdout.write(JSON.stringify(a.map(x=>shiftLoad(x.values,x.energy,x.cap))));"
    js=json.loads(subprocess.check_output(['node','-e',script],input=json.dumps(cases).encode(),cwd=ROOT))
    for c,r in zip(cases,js):
        py=shift_load(c['values'],c['energy'],c['cap'])
        np.testing.assert_allclose(py['shifted'],r['shifted'],atol=1e-8)
        assert abs(py['moved_mwh']-r['moved'])<1e-8

@pytest.mark.skipif(not (ROOT/'reports/results.json').exists(),reason='Full backtest artifacts not built')
def test_artifact_metrics_and_fold_boundaries():
    r=json.loads((ROOT/'reports/results.json').read_text())
    p=pd.read_csv(ROOT/'reports/backtest_predictions.csv')
    primary=p[p.day<'2026-01-01'];got=metrics(primary.actual,primary.forecast)
    assert got['mae_mw']==pytest.approx(r['primary_2025']['forecast']['mae_mw'],abs=1e-7)
    assert metrics(primary.actual,primary.ridge_linear)['mae_mw']==pytest.approx(r['primary_2025']['ridge_linear']['mae_mw'],abs=1e-7)
    assert not p.target_utc.duplicated().any()
    assert (p.lower<=p.forecast).all() and (p.forecast<=p.upper).all()
    for f in r['folds']:
        assert pd.Timestamp(f['train_last_target_utc'])+pd.Timedelta(hours=1)<=pd.Timestamp(f['calibration_first_target_utc'])
        assert pd.Timestamp(f['calibration_last_target_utc'])+pd.Timedelta(hours=1)<=pd.Timestamp(f['label_cutoff_utc'])
        assert pd.Timestamp(f['label_cutoff_utc'])<pd.Timestamp(f['first_issue_utc'])

@pytest.mark.skipif(not (ROOT/'data/processed/features.csv').exists(),reason='Full dataset not built')
def test_all_feature_lineage_is_before_issue():
    d=pd.read_csv(ROOT/'data/processed/features.csv')
    origin=pd.to_datetime(d.origin,utc=True);cutoff=pd.to_datetime(d.cutoff,utc=True)
    assert (pd.to_datetime(d.max_load_source_utc,utc=True)+pd.Timedelta(hours=1)<=cutoff).all()
    assert (pd.to_datetime(d.weather_nominal_issued_utc,utc=True)<origin).all()
