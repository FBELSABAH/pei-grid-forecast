"""One declared post-audit experiment; chronological reconstruction, not new holdout evidence."""
from __future__ import annotations
import math
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from .data import ROOT, write_json
from .features import origin_for_day
from .evaluate import new_model, columns
from .metrics import metrics


def signed_bounds(errors, coverage=.9):
    """Conservative equal-tail order statistics of earlier out-of-sample y - prediction."""
    x=np.sort(np.asarray(errors,float)); n=len(x)
    if n<500 or not np.isfinite(x).all():
        raise ValueError("At least 500 finite earlier out-of-sample errors required")
    tail=(1-coverage)/2
    lo=max(0,math.floor((n+1)*tail)-1)
    hi=min(n-1,math.ceil((n+1)*(1-tail))-1)
    return float(x[lo]),float(x[hi])


def historical_errors_before(history, asof):
    if not history:return pd.DataFrame()
    previous=pd.concat(history)
    return previous[(previous.index>=asof-pd.Timedelta(days=365)) &
                    (previous.index+pd.Timedelta(hours=1)<=asof)]


def run_revision(df, name, original):
    history=[]; scored=[]; folds=[]
    last=original.day.max()
    for start in pd.date_range("2023-01-01",last,freq="MS"):
        end=start+pd.DateOffset(months=1)
        asof=origin_for_day(start)-pd.Timedelta(hours=1)
        train=df[(df.index>=asof-pd.DateOffset(years=3)) &
                 (df.index+pd.Timedelta(hours=1)<=asof)]
        test=df[(df.day>=str(start.date())) & (df.day<str(end.date())) & (df.day<=last)]
        if len(train)<8000 or test.empty:raise ValueError(f"Insufficient monthly data: {start}")
        model=new_model(name)
        with threadpool_limits(limits=2):
            model.fit(train[columns(name)],train.actual)
            pred=np.maximum(model.predict(test[columns(name)]),0)
        out=test[['day','origin','actual']].copy()
        out['forecast']=pred;out['error']=out.actual-pred
        # Capture only earlier predictions and their already-available labels.
        cal=historical_errors_before(history,asof)
        if start.year>=2025:
            lo,hi=signed_bounds(cal.error)
            out['lower']=np.maximum(0,pred+lo);out['upper']=np.maximum(0,pred+hi)
            # Preserve the published quarterly threshold for directly comparable alert metrics.
            out['peak_threshold_mw']=original.peak_threshold_mw.reindex(out.index)
            if out.peak_threshold_mw.isna().any():raise ValueError('Comparison hours differ')
            scored.append(out)
            folds.append({'month':str(start.date())[:7],'first_issue_utc':str(origin_for_day(start)),
                'label_cutoff_utc':str(asof),'train_n':len(train),
                'train_first_target_utc':str(train.index.min()),'train_last_target_utc':str(train.index.max()),
                'calibration_n':len(cal),'calibration_first_target_utc':str(cal.index.min()),
                'calibration_last_target_utc':str(cal.index.max()),
                'residual_lower_mw':lo,'residual_upper_mw':hi,
                'metrics':metrics(out.actual,out.forecast,out.peak_threshold_mw,out.lower,out.upper)})
        history.append(out[['day','actual','forecast','error']])
    revised=pd.concat(scored)
    if not revised.index.equals(original.index):raise ValueError('Revised comparison must score exactly original target rows in order')
    summary={'status':'Single post-audit retrospective experiment; 2025/26 results already inspected before this design. No new untouched test or operational guarantee.',
        'method':'Monthly recent-label refits of fixed original boosting; trailing 365-day signed prequential errors for equal-tail 90% intervals. No bias correction, new feature or hyperparameter search.',
        'caution':'Earlier-model out-of-sample errors may not match a new refit under drift. Empirical intervals have no time-series coverage guarantee.',
        'primary_2025':metrics(*(revised[revised.day<'2026-01-01'][c] for c in ['actual','forecast','peak_threshold_mw','lower','upper'])),
        'extension_2026':metrics(*(revised[revised.day>='2026-01-01'][c] for c in ['actual','forecast','peak_threshold_mw','lower','upper'])),
        'folds':folds,'comparisons':[]}
    for label,mask in [('2025 January-March', original.day.between('2025-01-01','2025-03-31')),
                       ('2025 December-January-February', (original.day<'2026-01-01') & original.day.str[5:7].isin(['12','01','02'])),
                       ('2026 January-March', original.day.between('2026-01-01','2026-03-31'))]:
        a=original.loc[mask];b=revised.loc[mask]
        summary['comparisons'].append({'period':label,'original':metrics(a.actual,a.forecast,a.peak_threshold_mw,a.lower,a.upper),
            'monthly_revision':metrics(b.actual,b.forecast,b.peak_threshold_mw,b.lower,b.upper),
            'ridge_linear':metrics(a.actual,a.ridge_linear)})
    summary['monthly']=[{'month':m,**metrics(g.actual,g.forecast,g.peak_threshold_mw,g.lower,g.upper)} for m,g in revised.groupby(revised.day.str[:7])]
    revised.to_csv(ROOT/'reports/revision_predictions.csv',float_format='%.8f')
    pd.DataFrame([{k:v for k,v in f.items() if k!='metrics'} for f in folds]).to_csv(ROOT/'reports/revision_folds.csv',index=False)
    write_json(ROOT/'reports/winter_revision.json',summary)
    return summary
