import numpy as np
import pandas as pd
from gridcast.features import day_features,target_hours,origin_for_day,BASE_FEATURES,WEATHER_FEATURES

def inputs():
    t=pd.date_range("2025-01-01",periods=24*30,freq="h",tz="UTC")
    return pd.Series(100+np.sin(np.arange(len(t))/10),index=t),pd.Series(3.,index=t)

def test_dst_target_days():
    assert len(target_hours("2025-03-09"))==23
    assert len(target_hours("2025-11-02"))==25
    assert len(target_hours("2025-02-01"))==24

def test_future_load_mutation_cannot_change_features():
    load,w=inputs();day="2025-01-20";origin=origin_for_day(day)
    first,reason=day_features(load,w,day);assert reason is None
    load.loc[load.index>=origin-pd.Timedelta(hours=1)]=9999
    second,_=day_features(load,w,day)
    pd.testing.assert_frame_equal(first[BASE_FEATURES+WEATHER_FEATURES],second[BASE_FEATURES+WEATHER_FEATURES])
    assert (first.max_load_source_utc+pd.Timedelta(hours=1)<=first.cutoff).all()
    assert (first.weather_nominal_issued_utc<first.origin).all()

def test_missing_history_blocks_forecast():
    load,w=inputs();load.loc["2025-01-18":"2025-01-20"]=np.nan
    d,reason=day_features(load,w,"2025-01-20")
    assert d.empty and reason=="insufficient_history"
