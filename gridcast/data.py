"""Fetch, fingerprint, audit and aggregate public source observations."""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
TZ = "America/Halifax"
LOAD_URL = "https://energy.reinvented.net/archive/index.php"
CURRENT_URL = "https://energy.reinvented.net/pei-energy/govpeca/get-govpeca-json.php"
WEATHER_URL = "https://previous-runs-api.open-meteo.com/v1/forecast"

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False, default=str) + "\n")

def fetch(refresh: bool = False) -> dict:
    raw = ROOT / "data/raw"
    raw.mkdir(parents=True, exist_ok=True)
    manifest_path = raw / "manifest.json"
    old = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    session = requests.Session()
    session.headers["User-Agent"] = "PEI-Grid-Forecast/1.0 (educational research; cached downloads)"
    manifest = dict(old)
    for name, url, params in [
        ("electricity.csv", LOAD_URL, None),
        ("electricity_current.json", CURRENT_URL, None),
        ("weather.json", WEATHER_URL, {
            "latitude": 46.2382, "longitude": -63.1311,
            "hourly": "temperature_2m_previous_day2", "models": "gfs_seamless",
            "start_date": "2021-01-01",
            "end_date": (datetime.now(timezone.utc).date() + timedelta(days=2)).isoformat(),
            "timezone": "GMT",
        }),
    ]:
        dest = raw / name
        if refresh or not dest.exists():
            response = session.get(url, params=params, timeout=(15, 150))
            response.raise_for_status()
            if name.endswith(".json"):
                obj = response.json()
                if obj.get("error"):
                    raise ValueError(f"Source error for {name}: {obj.get('reason')}")
            temporary = dest.with_suffix(dest.suffix + ".tmp")
            temporary.write_bytes(response.content)
            temporary.replace(dest)
            manifest[name] = {"url": response.url, "retrieved_at_utc": datetime.now(timezone.utc).isoformat()}
        if name not in manifest:
            manifest[name] = {"url": url, "retrieved_at_utc": None,
                              "note": "Initial audited download; exact retrieval timestamp not retained. File mtime is not source publication time."}
        manifest[name].update(sha256=sha256(dest), bytes=dest.stat().st_size)
    write_json(manifest_path, manifest)
    return manifest

def clean_load(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    """Keep DST uncertainty explicit; never interpolate the forecast target."""
    required = {"updatetime", "on-island-load"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Missing source columns: {required - set(frame.columns)}")
    source = frame.copy()
    naive = pd.to_datetime(source.updatetime, errors="coerce")
    localized = naive.dt.tz_localize(TZ, ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC")
    value = pd.to_numeric(source["on-island-load"], errors="coerce")
    reasons = pd.Series("", index=source.index, dtype="str")
    reasons.loc[localized.isna()] = "invalid_or_ambiguous_local_timestamp"
    reasons.loc[~np.isfinite(value) | (value <= 0)] = "invalid_or_nonpositive_load"
    reasons.loc[localized.duplicated(keep="first") & localized.notna()] = "duplicate_timestamp"
    usable = pd.DataFrame({"timestamp": localized, "load_mw": value})[reasons.eq("")]
    usable = usable.sort_values("timestamp")
    # Causal quality rule: at each observation, use only the elapsed prefix.
    # A gap breaks evidence of continuous repetition. Never backdate a stale flag.
    reset = usable.load_mw.ne(usable.load_mw.shift()) | usable.timestamp.diff().gt(pd.Timedelta(minutes=30))
    runs = reset.cumsum()
    duration = usable.timestamp - usable.groupby(runs).timestamp.transform("min")
    stale = duration >= pd.Timedelta(hours=4)
    reasons.loc[usable.index[stale]] = "flat_source_elapsed_at_least_4h"
    usable = usable.loc[~stale].set_index("timestamp")
    usable["sample_timestamp"] = usable.index
    hourly = usable.resample("h").agg(load_mw=("load_mw", "mean"), samples=("load_mw", "count"),
                                    first_sample=("sample_timestamp", "min"), last_sample=("sample_timestamp", "max"))
    hourly["span_minutes"] = (hourly.last_sample - hourly.first_sample).dt.total_seconds() / 60
    # A partial trailing hour must not be presented as a completed observation.
    last_source = localized.dropna().max()
    completed = hourly.index + pd.Timedelta(hours=1) <= last_source
    hourly["accepted"] = (hourly.samples >= 3) & (hourly.span_minutes >= 30) & completed
    hourly.loc[~hourly.accepted, "load_mw"] = np.nan
    rejected = source.loc[reasons.ne("")].copy()
    rejected["reason"] = reasons[reasons.ne("")]
    by_year = hourly.assign(year=hourly.index.tz_convert(TZ).year).groupby("year").agg(
        hours=("accepted", "size"), accepted_hours=("accepted", "sum"))
    report = {"source_rows": len(frame), "rejected_rows": len(rejected),
              "reasons": {k: int(v) for k,v in reasons[reasons.ne("")].value_counts().items()},
              "first_source_wall_time": str(naive.min()), "last_source_wall_time": str(naive.max()),
              "hourly_bins": len(hourly), "accepted_hours": int(hourly.accepted.sum()),
              "missing_or_rejected_hours": int((~hourly.accepted).sum()),
              "by_year": {str(k): {a:int(b) for a,b in v.items()} for k,v in by_year.to_dict("index").items()}}
    return hourly, report, rejected

def load_weather(path: Path) -> pd.Series:
    obj = json.loads(path.read_text())
    if obj.get("utc_offset_seconds") != 0:
        raise ValueError("Weather timestamps must be requested in UTC")
    hourly = obj["hourly"]
    t = pd.to_datetime(hourly["time"], utc=True)
    weather = pd.Series(hourly["temperature_2m_previous_day2"], index=t, dtype=float, name="temperature_forecast_c")
    if weather.index.duplicated().any():
        raise ValueError("Duplicate weather validity timestamps")
    return weather

def prepare() -> tuple[pd.DataFrame, pd.Series, dict]:
    raw, out = ROOT / "data/raw", ROOT / "reports"
    hourly, report, rejected = clean_load(pd.read_csv(raw / "electricity.csv"))
    weather = load_weather(raw / "weather.json")
    current = json.loads((raw / "electricity_current.json").read_text())
    epoch_local = pd.Timestamp(current["updatetime"], unit="s", tz="UTC").tz_convert(TZ).tz_localize(None)
    report["timezone_check"] = {"unix_timestamp_as_halifax": str(epoch_local),
                                "feed_wall_time": current["updatetime_human"],
                                "matches": str(epoch_local) == current["updatetime_human"],
                                "historical_timezone_confirmed": False}
    if not report["timezone_check"]["matches"]:
        raise ValueError("Current timestamp does not support America/Halifax assumption")
    report["weather"] = {"hours": len(weather), "missing": int(weather.isna().sum()),
                         "first_nonmissing_utc": str(weather.first_valid_index()),
                         "last_nonmissing_utc": str(weather.last_valid_index()),
                         "point": "46.2382 N, 63.1311 W (Charlottetown), representative proxy, not island average",
                         "nominal_lead_hours": 48}
    out.mkdir(exist_ok=True)
    rejected.to_csv(out / "rejected_readings.csv", index=False)
    hourly.to_csv(ROOT / "data/processed/hourly_load.csv")
    write_json(out / "data_audit.json", report)
    return hourly, weather, report
