"""Run with cached data by default; --refresh is the only network update path."""
import argparse
import json
import time
from datetime import datetime, timezone
import pandas as pd
from gridcast.data import ROOT, TZ, fetch, prepare, sha256, write_json
from gridcast.features import build_dataset
from gridcast.evaluate import choose_model,run_backtest,make_latest

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--refresh",action="store_true",help="Download new source snapshots before rebuilding")
    parser.add_argument("--audit-only",action="store_true")
    args=parser.parse_args();began=time.perf_counter()
    manifest=fetch(args.refresh)
    hourly,weather,audit=prepare()
    dataset,coverage=build_dataset(hourly.load_mw,weather)
    dataset.to_csv(ROOT/"data/processed/features.csv",float_format="%.8f")
    write_json(ROOT/"reports/eligibility.json",coverage)
    if args.audit_only:
        print(json.dumps({"audit":audit,"coverage":{k:v for k,v in coverage.items() if k!="excluded_origin_days"}},indent=2));return
    selected=choose_model(dataset)
    # Exclude current local day even if a downloaded partial hour is present.
    last_complete=hourly.index.max().tz_convert(TZ).date()-pd.Timedelta(days=1)
    predictions,results=run_backtest(dataset,selected,last_complete)
    latest=make_latest(dataset,hourly.load_mw,weather,selected)
    write_json(ROOT/"reports/run_manifest.json",{"completed_at_utc":datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds":round(time.perf_counter()-began,3),"protocol_sha256":sha256(ROOT/"protocol.json"),
        "source_manifest":manifest,"feature_sha256":sha256(ROOT/"data/processed/features.csv"),
        "prediction_sha256":sha256(ROOT/"reports/backtest_predictions.csv"),
        "primary_test":"2025 calendar year","extension_through":str(last_complete)})
    from gridcast.publish import publish
    publish(predictions,latest,results,audit,coverage)
    print(f"Complete in {time.perf_counter()-began:.1f}s. Open dist/index.html or serve dist/.",flush=True)

if __name__=="__main__":main()
