"""Evaluation and energy-conserving scenarios; no utility savings claims."""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

def metrics(actual, pred, threshold=None, lower=None, upper=None) -> dict:
    y, p = np.asarray(actual,float), np.asarray(pred,float)
    if len(y)==0 or len(y)!=len(p) or not (np.isfinite(y).all() and np.isfinite(p).all()):
        raise ValueError("Metrics require paired finite arrays")
    error = p-y
    result = {"n":len(y),"mae_mw":float(np.mean(abs(error))),"rmse_mw":float(np.sqrt(np.mean(error**2))),
              "wape_pct":float(100*np.sum(abs(error))/np.sum(abs(y))),"bias_mw":float(np.mean(error))}
    if threshold is not None:
        positive, alert = y>=np.asarray(threshold), p>=np.asarray(threshold)
        tp, fp, fn = int(np.sum(positive&alert)),int(np.sum(~positive&alert)),int(np.sum(positive&~alert))
        result.update(tp=tp,fp=fp,fn=fn,tn=int(np.sum(~positive&~alert)),
                      peak_precision=tp/(tp+fp) if tp+fp else 0.0,peak_recall=tp/(tp+fn) if tp+fn else 0.0)
    if lower is not None:
        lo,hi = np.asarray(lower),np.asarray(upper)
        result.update(interval_coverage_pct=float(100*np.mean((y>=lo)&(y<=hi))),interval_mean_width_mw=float(np.mean(hi-lo)))
    return result

def conformal_radius(residuals, coverage=.9) -> float:
    values = np.sort(np.asarray(residuals,float))
    if len(values)<30 or not np.isfinite(values).all():
        raise ValueError("At least 30 finite calibration residuals required")
    rank = min(len(values), math.ceil((len(values)+1)*coverage))
    return float(values[rank-1])

def shift_load(values, energy_mwh: float, max_shift_mw: float, source_hours=None, dest_hours=None) -> dict:
    """Move flexible energy from highest to lowest permitted hours, within caps.

    One row is one elapsed hour, hence MW * 1h = MWh. Energy is a scenario
    assumption, not measured flexible capacity. Bound eligible source/dest sets.
    """
    base = np.asarray(values,float)
    if len(base)<2 or not np.isfinite(base).all() or np.any(base<0):
        raise ValueError("Require at least two finite nonnegative hourly loads")
    if not np.isfinite([energy_mwh,max_shift_mw]).all() or energy_mwh<0 or max_shift_mw<0:
        raise ValueError("Scenario inputs must be finite and nonnegative")
    src = list(range(len(base))) if source_hours is None else list(source_hours)
    dst = list(range(len(base))) if dest_hours is None else list(dest_hours)
    if any(i<0 or i>=len(base) for i in src+dst):
        raise ValueError("Invalid scenario hour")
    # Choose disjoint top/bottom thirds if no eligibility was supplied.
    if source_hours is None and dest_hours is None:
        order = np.argsort(base,kind="stable")
        n = max(1,len(base)//3);src=list(order[-n:]);dst=list(order[:n])
    if set(src)&set(dst):
        raise ValueError("Source and destination hours must be disjoint")
    result = base.copy();removed=np.zeros(len(base));added=np.zeros(len(base))
    # Allocate in small bounded steps to flatten, rather than move a peak wholesale.
    remaining=energy_mwh
    while remaining>1e-9 and src and dst:
        sources=[i for i in src if removed[i]<min(max_shift_mw,base[i])-1e-9]
        dests=[i for i in dst if added[i]<max_shift_mw-1e-9]
        if not sources or not dests:break
        i=max(sources,key=lambda i:result[i]);j=min(dests,key=lambda j:result[j])
        if result[i]<=result[j]+1e-9:break
        move=min(remaining,.1,max_shift_mw-removed[i],base[i]-removed[i],max_shift_mw-added[j],(result[i]-result[j])/2)
        if move<=1e-9:break
        result[i]-=move;result[j]+=move;removed[i]+=move;added[j]+=move;remaining-=move
    return {"original":base.tolist(),"shifted":result.tolist(),"requested_mwh":energy_mwh,
            "moved_mwh":float(removed.sum()),"peak_before_mw":float(base.max()),"peak_after_mw":float(result.max()),
            "energy_difference_mwh":float(result.sum()-base.sum()),"per_hour_cap_mw":max_shift_mw}

def paired_block_bootstrap(frame: pd.DataFrame, baseline: str, repetitions=1000) -> dict:
    day=frame.groupby("day").apply(lambda g: float(np.mean(abs(g[baseline]-g.actual))-np.mean(abs(g.forecast-g.actual))),include_groups=False)
    calendar=day.reindex(pd.date_range(day.index.min(),day.index.max()).strftime("%Y-%m-%d")).to_numpy()
    rng=np.random.default_rng(2027);estimates=[]
    for _ in range(repetitions):
        starts=rng.integers(0,max(1,len(calendar)-6),size=math.ceil(len(calendar)/7))
        sample=np.concatenate([calendar[i:i+7] for i in starts])[:len(calendar)]
        estimates.append(float(np.nanmean(sample)))
    return {"baseline":baseline,"daily_mean_mae_gain_mw":float(np.nanmean(calendar)),
            "ci95_mw":[float(x) for x in np.quantile(estimates,[.025,.975])],
            "method":"1000 seeded moving-block bootstrap replicates, 7 calendar-day blocks; positive gain favours model; approximate time-series interval"}
