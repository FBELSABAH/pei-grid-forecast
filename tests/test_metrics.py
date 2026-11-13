import numpy as np
import pytest
from gridcast.metrics import metrics,conformal_radius,shift_load

def test_metrics_known_values():
    r=metrics([100,200],[110,180],[150,150],[90,170],[115,210])
    assert r["mae_mw"]==15 and r["bias_mw"]==-5
    assert r["peak_precision"]==1 and r["peak_recall"]==1 and r["interval_coverage_pct"]==100

def test_bad_metric_input():
    with pytest.raises(ValueError):metrics([],[])
    with pytest.raises(ValueError):metrics([1],[float("nan")])

def test_conformal_quantile():
    assert conformal_radius(np.arange(100))==90
    with pytest.raises(ValueError):conformal_radius([1])

@pytest.mark.parametrize("n",[23,24,25])
def test_shift_conserves_energy_and_caps(n):
    a=np.linspace(100,250,n);r=shift_load(a,50,7)
    shifted=np.array(r["shifted"])
    assert abs(shifted.sum()-a.sum())<1e-8
    assert np.max(abs(shifted-a))<=7+1e-8
    assert shifted.min()>=0 and shifted.max()<=a.max()
    assert r["moved_mwh"]<=50+1e-8

def test_no_flexibility_no_change():
    r=shift_load([100,200],100,0);assert r["shifted"]==[100,200]

def test_invalid_simulation_rejected():
    with pytest.raises(ValueError):shift_load([100,200],-1,5)
    with pytest.raises(ValueError):shift_load([100,200],3,5,[0],[0])
