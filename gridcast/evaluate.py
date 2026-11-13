"""Model choice on development data, then a locked quarterly walk-forward test."""
from __future__ import annotations
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits
from .data import ROOT, TZ, write_json
from .features import BASE_FEATURES, WEATHER_FEATURES, origin_for_day
from .metrics import metrics, conformal_radius, paired_block_bootstrap

CANDIDATES = ["ridge_weather", "boost_weather_15", "boost_weather_31", "boost_load_only"]
BASELINES = ["weekly_naive", "two_day_naive", "mean_2_and_7_day"]

def columns(name):
    return BASE_FEATURES if name=="boost_load_only" else BASE_FEATURES+WEATHER_FEATURES

def new_model(name):
    if name=="ridge_weather":
        return make_pipeline(SimpleImputer(strategy="median"),StandardScaler(),Ridge(alpha=100))
    return HistGradientBoostingRegressor(max_iter=220,learning_rate=.065,
        max_leaf_nodes=31 if name=="boost_weather_31" else 15,min_samples_leaf=40,
        l2_regularization=10,early_stopping=False,random_state=2027)

def score_frame(d,pred):
    out=d[["origin","target_local","day","actual","temperature_forecast_c"]].copy()
    out["forecast"]=pred
    out["weekly_naive"]=d.lag168
    out["two_day_naive"]=d.lag48
    out["mean_2_and_7_day"]=d.profile_mean
    return out

def choose_model(df):
    cutoff=origin_for_day("2024-01-01")-pd.Timedelta(hours=1)
    train=df[(df.index+pd.Timedelta(hours=1)<=cutoff)&(df.day<"2024-01-01")]
    val=df[(df.day>="2024-01-01")&(df.day<"2024-07-01")]
    if len(train)<8000 or len(val)<2000:
        raise ValueError("Insufficient training or validation coverage")
    rows=[]
    for name in CANDIDATES:
        model=new_model(name);cols=columns(name)
        with threadpool_limits(limits=2):
            model.fit(train[cols],train.actual)
            p=np.maximum(model.predict(val[cols]),0)
        rows.append({"model":name,**metrics(val.actual,p)})
        print(f"Development {name}: MAE {rows[-1]['mae_mw']:.3f} MW",flush=True)
    selected=min(rows,key=lambda r:r["mae_mw"])["model"]
    write_json(ROOT/"reports/model_selection.json",{"selected":selected,"train_rows":len(train),"validation_rows":len(val),
        "validation_start":"2024-01-01","validation_end_exclusive":"2024-07-01","candidates":rows,
        "rule":"Minimum validation MAE only. Test predictions do not participate in selection."})
    return selected

def fit_at(df,name,start_day):
    # All labels used in fitting/calibration must have been available at earliest issue.
    asof=origin_for_day(start_day)-pd.Timedelta(hours=1)
    calibration_start=asof-pd.Timedelta(days=180)
    train_start=calibration_start-pd.DateOffset(years=3)
    ends=df.index+pd.Timedelta(hours=1)
    train=df[(df.index>=train_start)&(ends<=calibration_start)]
    calibration=df[(df.index>=calibration_start)&(ends<=asof)]
    if len(train)<8000 or len(calibration)<1000:
        raise ValueError(f"Insufficient fold data at {start_day}")
    cols=columns(name);model=new_model(name)
    with threadpool_limits(limits=2):
        model.fit(train[cols],train.actual)
        residual=abs(model.predict(calibration[cols])-calibration.actual)
    radius=conformal_radius(residual)
    threshold=float(train.actual.quantile(.95))
    meta={"first_issue_utc":str(origin_for_day(start_day)),"label_cutoff_utc":str(asof),
          "train_first_target_utc":str(train.index.min()),"train_last_target_utc":str(train.index.max()),
          "calibration_first_target_utc":str(calibration.index.min()),"calibration_last_target_utc":str(calibration.index.max()),
          "train_n":len(train),"calibration_n":len(calibration),"interval_radius_mw":radius,"peak_threshold_mw":threshold}
    return model,radius,threshold,meta

def aggregate(frame):
    result={name:metrics(frame.actual,frame[name],frame.peak_threshold_mw,
                        frame.lower if name=="forecast" else None,frame.upper if name=="forecast" else None)
            for name in ["forecast"]+BASELINES}
    # Daily peak metrics only use days with every expected elapsed hour present.
    daily=[]
    for day,g in frame.groupby("day"):
        start=pd.Timestamp(day).tz_localize(TZ)
        end=(pd.Timestamp(day)+pd.Timedelta(days=1)).tz_localize(TZ)
        if len(g)!=int((end-start).total_seconds()/3600):continue
        yi=g.actual.idxmax();pi=g.forecast.idxmax()
        daily.append({"day":day,"peak_absolute_error_mw":abs(float(g.actual.max()-g.forecast.max())),
                      "peak_timing_absolute_error_h":abs((yi-pi).total_seconds())/3600})
    result["daily_peaks"]={"complete_days":len(daily),
        "peak_mae_mw":float(np.mean([x["peak_absolute_error_mw"] for x in daily])) if daily else None,
        "timing_mae_hours":float(np.mean([x["peak_timing_absolute_error_h"] for x in daily])) if daily else None}
    return result

def run_backtest(df,name,last_complete_day):
    frames=[];folds=[]
    ends=pd.Timestamp(last_complete_day)+pd.Timedelta(days=1)
    for start in pd.date_range("2025-01-01",ends,freq="QS"):
        end=min(start+pd.DateOffset(months=3),ends)
        test=df[(df.day>=str(start.date()))&(df.day<str(end.date()))]
        if len(test)==0:continue
        model,radius,threshold,meta=fit_at(df,name,start.date())
        with threadpool_limits(limits=2):p=np.maximum(model.predict(test[columns(name)]),0)
        scored=score_frame(test,p)
        scored["lower"],scored["upper"]=np.maximum(p-radius,0),p+radius
        scored["peak_threshold_mw"]=threshold
        scored["fold"]=str(start.date())
        frames.append(scored)
        meta.update(test_first_day=str(start.date()),test_end_exclusive=str(end.date()),test_n=len(scored),metrics=aggregate(scored))
        folds.append(meta)
        print(f"Fold {start.date()}: {len(scored)} held-out hours, MAE {meta['metrics']['forecast']['mae_mw']:.3f} MW",flush=True)
    scored=pd.concat(frames)
    primary=scored[scored.day<"2026-01-01"]
    extension=scored[scored.day>="2026-01-01"]
    report={"selected_model":name,"primary_2025":aggregate(primary),"extension_2026":aggregate(extension),"folds":folds,
            "primary_best_baseline":min(BASELINES,key=lambda n:metrics(primary.actual,primary[n])["mae_mw"])}
    best=report["primary_best_baseline"]
    report["primary_paired_bootstrap"]=paired_block_bootstrap(primary,best)
    report["primary_mae_improvement_pct"]=100*(1-report["primary_2025"]["forecast"]["mae_mw"]/report["primary_2025"][best]["mae_mw"])
    breakdown=[]
    for month,g in scored.groupby(scored.day.str[:7]):
        breakdown.append({"month":month,**aggregate(g)})
    report["monthly"]=breakdown
    peak=scored[scored.actual>=scored.peak_threshold_mw]
    report["high_load_hours"]=metrics(peak.actual,peak.forecast)
    report["worst_days"]=scored.groupby("day").apply(lambda g:float(np.mean(abs(g.forecast-g.actual))),include_groups=False).nlargest(10).to_dict()
    write_json(ROOT/"reports/results.json",report)
    scored.to_csv(ROOT/"reports/backtest_predictions.csv",float_format="%.8f")
    pd.DataFrame([{**{k:v for k,v in r.items() if k not in ['metrics']},"mae_mw":r['metrics']['forecast']['mae_mw']} for r in folds]).to_csv(ROOT/"reports/folds.csv",index=False)
    return scored,report

def make_latest(df,load,weather,name):
    from .features import day_features
    latest=load.dropna().index.max().tz_convert(TZ)
    # Most recent daily issue whose one-hour publication buffer is supported by source.
    possible=latest.floor("D")+pd.Timedelta(hours=18)
    if possible>latest:possible-=pd.Timedelta(days=1)
    target=(possible+pd.Timedelta(days=1)).date()
    d,reason=day_features(load,weather,target)
    if reason:raise ValueError(f"Latest forecast blocked: {reason}")
    if d[BASE_FEATURES+WEATHER_FEATURES].isna().any().any():
        raise ValueError("Latest forecast blocked by missing lag/weather input; refresh sources")
    quarter=pd.Timestamp(target).to_period("Q").start_time.date()
    model,radius,threshold,meta=fit_at(df,name,quarter)
    with threadpool_limits(limits=2):pred=np.maximum(model.predict(d[columns(name)]),0)
    out=score_frame(d,pred);out["lower"]=np.maximum(pred-radius,0);out["upper"]=pred+radius
    out["peak_threshold_mw"]=threshold
    out.to_csv(ROOT/"reports/latest_forecast.csv",float_format="%.8f")
    (ROOT/"models").mkdir(exist_ok=True)
    joblib.dump({"model":model,"features":columns(name),"metadata":meta,"model_name":name},ROOT/"models/model.joblib")
    write_json(ROOT/"reports/latest_metadata.json",{"origin_utc":str(origin_for_day(target)),"target_day":str(target),
        "status":"Snapshot reconstruction from public archive; not independently logged at historical issue time",
        "last_source_local":str(latest),"model":meta})
    return out
