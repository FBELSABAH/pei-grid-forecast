import numpy as np
import pandas as pd
import pytest
from gridcast.data import clean_load,load_weather

def source(start="2025-01-01",periods=8):
    return pd.DataFrame({"updatetime":pd.date_range(start,periods=periods,freq="15min").astype(str),"on-island-load":100+np.arange(periods,dtype=float)})

def test_hourly_mean_and_no_target_fill():
    h,_,_=clean_load(source());assert h.iloc[0].load_mw==101.5
    sparse=source().drop([1,2]);h,_,_=clean_load(sparse)
    assert np.isnan(h.iloc[0].load_mw)

def test_nonpositive_duplicate_and_malformed():
    s=source();s.loc[0,"on-island-load"]=-1;s.loc[1,"updatetime"]="bad"
    s=pd.concat([s,s.iloc[[2]]],ignore_index=True)
    _,r,rejected=clean_load(s)
    assert r["rejected_rows"]==3
    assert set(rejected.reason)=={"invalid_or_nonpositive_load","invalid_or_ambiguous_local_timestamp","duplicate_timestamp"}

def test_flatline_quarantine():
    s=source(periods=21);s["on-island-load"]=100
    h,r,_=clean_load(s);assert r["rejected_rows"]==21;assert h.load_mw.empty

def test_dst_ambiguous_removed():
    s=source("2025-11-02 00:00",16);_,r,rejected=clean_load(s)
    assert r["reasons"]["invalid_or_ambiguous_local_timestamp"]==4

def test_schema_failure():
    with pytest.raises(ValueError):clean_load(pd.DataFrame({"x":[1]}))

def test_partial_trailing_hour_is_not_final_observation():
    h,_,_=clean_load(source())
    assert pd.notna(h.iloc[0].load_mw)
    assert pd.isna(h.iloc[-1].load_mw)
