import numpy as np
import pandas as pd
import pytest
from gridcast.data import clean_load, ROOT
from gridcast.features import day_features, BASE_FEATURES, WEATHER_FEATURES
from gridcast.revision import signed_bounds, historical_errors_before
from gridcast.metrics import metrics
import json


def test_raw_future_mutation_preserves_inputs_and_completed_prefix():
    times=pd.date_range('2025-01-10','2025-01-22',freq='15min')
    x=150+20*np.sin(np.arange(len(times))/20)
    flat=(times>=pd.Timestamp('2025-01-19 15:00'))&(times<=pd.Timestamp('2025-01-19 20:00'))
    raw=pd.DataFrame({'updatetime':times.astype(str),'on-island-load':np.where(flat,100,x)})
    other=raw.copy();future=times>=pd.Timestamp('2025-01-19 18:00')
    other.loc[future,'on-island-load']=x[future]
    a,_,_=clean_load(raw);b,_,_=clean_load(other)
    cutoff=pd.Timestamp('2025-01-19 17:00',tz='America/Halifax').tz_convert('UTC')
    pd.testing.assert_series_equal(a.loc[a.index+pd.Timedelta(hours=1)<=cutoff].load_mw,b.loc[b.index+pd.Timedelta(hours=1)<=cutoff].load_mw)
    w=pd.Series(0.,index=a.index)
    fa,reason=day_features(a.load_mw,w,'2025-01-20');fb,reason_b=day_features(b.load_mw,w,'2025-01-20')
    assert reason is None and reason_b is None
    pd.testing.assert_frame_equal(fa[BASE_FEATURES+WEATHER_FEATURES],fb[BASE_FEATURES+WEATHER_FEATURES])


def test_gap_resets_flatline_evidence():
    times=pd.DatetimeIndex(['2025-01-01 00:00','2025-01-01 08:00','2025-01-01 08:15','2025-01-01 08:30','2025-01-01 08:45','2025-01-01 09:00'])
    _,audit,_=clean_load(pd.DataFrame({'updatetime':times.astype(str),'on-island-load':100}))
    assert audit['rejected_rows']==0


def test_signed_bounds_require_enough_errors_and_are_asymmetric():
    with pytest.raises(ValueError):signed_bounds([1,2])
    low,high=signed_bounds(np.arange(1000)-100)
    assert low<0<high and high>abs(low)


def test_calibration_cannot_see_future_labels():
    t=pd.date_range('2024-01-01',periods=9000,freq='h',tz='UTC')
    h=pd.DataFrame({'error':np.arange(len(t))},index=t)
    cutoff=t[8500]
    eligible=historical_errors_before([h],cutoff)
    assert (eligible.index+pd.Timedelta(hours=1)<=cutoff).all()
    changed=h.copy();changed.loc[changed.index>=cutoff,'error']=1e9
    pd.testing.assert_frame_equal(eligible,historical_errors_before([changed],cutoff))


def test_interval_score_penalizes_misses_and_unnecessary_width():
    assert metrics([10],[10],lower=[9],upper=[11])['interval_score_90_mw']==2
    assert metrics([12],[10],lower=[9],upper=[11])['interval_score_90_mw']==22


@pytest.mark.skipif(not (ROOT/'reports/revision_predictions.csv').exists(),reason='Revision not built')
def test_revision_artifacts_and_timing():
    a=pd.read_csv(ROOT/'reports/backtest_predictions.csv');b=pd.read_csv(ROOT/'reports/revision_predictions.csv')
    assert a.target_utc.equals(b.target_utc)
    assert np.allclose(a.actual,b.actual)
    report=json.loads((ROOT/'reports/winter_revision.json').read_text())
    mask=b.day<'2026-01-01'
    assert metrics(b.loc[mask,'actual'],b.loc[mask,'forecast'])['mae_mw']==pytest.approx(report['primary_2025']['mae_mw'],abs=1e-7)
    for f in report['folds']:
        cutoff=pd.Timestamp(f['label_cutoff_utc'])
        assert pd.Timestamp(f['train_last_target_utc'])+pd.Timedelta(hours=1)<=cutoff
        assert pd.Timestamp(f['calibration_last_target_utc'])+pd.Timedelta(hours=1)<=cutoff
        assert cutoff<pd.Timestamp(f['first_issue_utc'])


@pytest.mark.skipif(not (ROOT/'reports/eligibility.json').exists(),reason='Full dataset not built')
def test_monthly_coverage_reconciles_with_annual_denominator():
    report=json.loads((ROOT/'reports/eligibility.json').read_text())
    months=[m for m in report['monthly'] if m['month'].startswith('2025')]
    assert sum(m['calendar_hours'] for m in months)==8760
    assert sum(m['eligible_hours'] for m in months)==report['primary_test']['eligible_hours']
    assert all(m['eligible_hours']<=m['calendar_hours'] for m in months)
