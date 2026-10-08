from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from q4_ew_compare import ew_history_profile, ew_coupled_price_forecast


def synthetic(days=70,slots=8):
    rng=np.random.default_rng(42)
    net=80+rng.normal(0,2,(days,slots))
    price=.5+.004*net+rng.normal(0,.01,(days,slots))
    dates=pd.date_range('2025-01-01',periods=days)
    return dates,net,price


def test_ew_profile_uses_only_values_before_release_for_full_48h():
    dates,net,_=synthetic()
    slots=net.shape[1]; d=30; release=d*slots+3
    targets=release+np.arange(2*slots)
    base,latest=ew_history_profile(net,dates,targets,release,n=8,decay=.8)
    assert base.shape==(2*slots,)
    assert np.all(latest<release)
    changed=net.copy(); changed.ravel()[release:]=999999
    base2,latest2=ew_history_profile(changed,dates,targets,release,n=8,decay=.8)
    np.testing.assert_allclose(base,base2)
    np.testing.assert_array_equal(latest,latest2)


def test_ew_profile_uses_same_load_type_days():
    dates,net,_=synthetic(); slots=net.shape[1]; d=30; release=d*slots
    targets=np.array([release])
    base,latest=ew_history_profile(net,dates,targets,release,n=8,decay=.8)
    target_low=pd.Timestamp(dates[d]).dayofweek in (4,5)
    selected=[]
    for j in range(d-1,-1,-1):
        if (pd.Timestamp(dates[j]).dayofweek in (4,5))==target_low:
            selected.append(j*slots)
            if len(selected)==8: break
    w=.8**np.arange(len(selected)); w=w/w.sum()
    assert base[0]==pytest.approx(np.dot(w,net.ravel()[selected]))
    assert latest[0]==max(selected)


def test_ew_coupled_price_forecast_is_future_blind():
    dates,net,price=synthetic(); slots=net.shape[1]; d=45; start=3
    provider=lambda j: np.r_[net[j-1],net[j-1]]
    nh=provider(d)
    a,meta=ew_coupled_price_forecast(net,price,dates,d,nh,start_slot=start,
                                     n=8,decay=.8,forecast_provider=provider)
    net2=net.copy(); price2=price.copy()
    net2.ravel()[d*slots+start:]=888888
    price2.ravel()[d*slots+start:]=999999
    provider2=lambda j: np.r_[net2[j-1],net2[j-1]]
    b,meta2=ew_coupled_price_forecast(net2,price2,dates,d,nh,start_slot=start,
                                      n=8,decay=.8,forecast_provider=provider2)
    np.testing.assert_allclose(a,b)
    assert a.shape==(2*slots,)
    assert meta['history_max_abs']<d*slots+start
    assert meta['n']==8 and meta['decay']==.8
    assert meta==meta2
