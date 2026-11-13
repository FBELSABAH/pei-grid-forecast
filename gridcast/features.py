"""Construct all inputs using an explicit forecast origin and cutoff."""
from __future__ import annotations
import numpy as np
import pandas as pd
from .data import TZ

BASE_FEATURES = ["hour", "dow", "weekend", "year_sin", "year_cos", "hour_sin", "hour_cos",
                 "year_end", "lag48", "lag168", "profile_mean", "last_load", "mean24", "min24", "max24", "mean168", "level_delta"]
WEATHER_FEATURES = ["temperature_forecast_c", "heating_degrees", "cooling_degrees", "heating_hour"]

def origin_for_day(day) -> pd.Timestamp:
    day = pd.Timestamp(day).date()
    return (pd.Timestamp(day) - pd.Timedelta(days=1) + pd.Timedelta(hours=18)).tz_localize(TZ).tz_convert("UTC")

def target_hours(day) -> pd.DatetimeIndex:
    local = pd.Timestamp(pd.Timestamp(day).date()).tz_localize(TZ)
    end = (pd.Timestamp(pd.Timestamp(day).date()) + pd.Timedelta(days=1)).tz_localize(TZ)
    return pd.date_range(local, end, freq="h", inclusive="left").tz_convert("UTC")

def day_features(load: pd.Series, weather: pd.Series, day) -> tuple[pd.DataFrame, str | None]:
    origin = origin_for_day(day)
    cutoff = origin - pd.Timedelta(hours=1)
    # A labelled interval at t ends at t+1h. Require end <= cutoff.
    history = load.loc[(load.index >= cutoff-pd.Timedelta(days=7)) & (load.index < cutoff)].dropna()
    recent = history.loc[history.index >= cutoff-pd.Timedelta(hours=24)]
    if len(recent) < 20 or len(history) < 140:
        return pd.DataFrame(), "insufficient_history"
    if history.index.max() < cutoff-pd.Timedelta(hours=3):
        return pd.DataFrame(), "stale_history"
    targets = target_hours(day)
    local = targets.tz_convert(TZ)
    a, b = targets-pd.Timedelta(hours=48), targets-pd.Timedelta(hours=168)
    # This assertion also protects future refactors from accidentally adding lag24.
    assert max(a.max(), b.max(), history.index.max()) + pd.Timedelta(hours=1) <= cutoff
    d = pd.DataFrame(index=targets)
    d["origin"] = origin
    d["cutoff"] = cutoff
    d["target_local"] = local.astype(str)
    d["day"] = str(pd.Timestamp(day).date())
    d["hour"], d["dow"] = local.hour, local.day_of_week
    d["weekend"] = (local.day_of_week >= 5).astype(int)
    d["year_sin"] = np.sin(2*np.pi*local.day_of_year/365.2425)
    d["year_cos"] = np.cos(2*np.pi*local.day_of_year/365.2425)
    d["hour_sin"] = np.sin(2*np.pi*local.hour/24)
    d["hour_cos"] = np.cos(2*np.pi*local.hour/24)
    d["year_end"] = ((local.month == 12) & (local.day >= 24) | (local.month == 1) & (local.day == 1)).astype(int)
    d["lag48"] = load.reindex(a).to_numpy()
    d["lag168"] = load.reindex(b).to_numpy()
    d["profile_mean"] = (d.lag48+d.lag168)/2
    d["last_load"] = float(history.iloc[-1])
    d["mean24"], d["min24"], d["max24"] = recent.mean(), recent.min(), recent.max()
    d["mean168"] = history.mean()
    d["level_delta"] = recent.mean()-history.mean()
    d["temperature_forecast_c"] = weather.reindex(targets).to_numpy()
    d["heating_degrees"] = np.maximum(18-d.temperature_forecast_c, 0)
    d["cooling_degrees"] = np.maximum(d.temperature_forecast_c-18, 0)
    d["heating_hour"] = d.heating_degrees*d.hour_cos
    d["max_load_source_utc"] = [max(x,y,history.index.max()) for x,y in zip(a,b)]
    d["weather_nominal_issued_utc"] = targets-pd.Timedelta(hours=48)
    d["actual"] = load.reindex(targets).to_numpy()
    d.index.name = "target_utc"
    return d, None

def build_dataset(load: pd.Series, weather: pd.Series) -> tuple[pd.DataFrame, dict]:
    last_day = load.index.max().tz_convert(TZ).date()
    days = pd.date_range("2021-01-09", last_day, freq="D")
    frames, excluded = [], []
    for day in days:
        d, reason = day_features(load, weather, day)
        if reason:
            excluded.append({"day":str(day.date()), "reason":reason})
        else:
            frames.append(d)
    if not frames:
        raise ValueError("No forecast origins pass history requirements")
    full = pd.concat(frames)
    eligible = full[BASE_FEATURES+WEATHER_FEATURES+["actual"]].notna().all(axis=1)
    dataset = full.loc[eligible].copy()
    report = {"candidate_days": len(days), "days_with_history": len(frames), "excluded_origin_days": excluded,
              "candidate_hours_after_history_gate": len(full), "eligible_hours": len(dataset),
              "hours_missing_target_or_lag_or_weather": int((~eligible).sum()),
              "evaluation_scope": "All methods scored on identical eligible hours. Missing target, lag or weather rows are omitted, never interpolated."}
    for start,end,name in [("2024-01-01","2024-07-01","validation"),("2025-01-01","2026-01-01","primary_test"),("2026-01-01",str(last_day),"extension_test")]:
        potential = pd.date_range(start,end,freq="h",tz=TZ,inclusive="left")
        n = int(((dataset.day>=start)&(dataset.day<end)).sum())
        report[name] = {"eligible_hours":n,"calendar_hours":len(potential),"coverage_pct":100*n/len(potential) if len(potential) else 0}
    return dataset, report
