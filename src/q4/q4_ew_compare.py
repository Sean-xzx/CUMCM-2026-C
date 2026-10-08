from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

import q4_pipeline as q4


def ew_history_profile(arr: np.ndarray, dates, targets: np.ndarray, release: int,
                       n: int = 8, decay: float = .8) -> tuple[np.ndarray,np.ndarray]:
    """取发布前最近n个“同负荷日型、同日内时段”历史值做有限窗EW。"""
    arr=np.asarray(arr,float); dates=pd.DatetimeIndex(dates)
    if len(dates)>1 and not np.all(np.diff(dates.values)==np.timedelta64(1,'D')):
        raise ValueError("同类型EW要求日期索引按自然日连续")
    first_dow=int(dates[0].dayofweek)
    is_low=lambda day: (first_dow+int(day))%7 in (4,5)
    targets=np.asarray(targets,int); slots=arr.shape[1]; flat=arr.ravel()
    out=np.empty(len(targets)); latest=np.empty(len(targets),dtype=int)
    for r,target in enumerate(targets):
        target_day=int(target//slots); slot=int(target%slots)
        target_type=is_low(target_day)
        idx=[]
        for hist_day in range(target_day-1,-1,-1):
            z=hist_day*slots+slot
            if z>=release or z>=len(flat):
                continue
            if is_low(hist_day)==target_type:
                idx.append(z)
                if len(idx)==n: break
        if not idx: raise ValueError("EW基线没有合法历史")
        w=decay**np.arange(len(idx)); w=w/w.sum()
        out[r]=np.dot(w,flat[idx]); latest[r]=max(idx)
    return out,latest


def ew_coupled_price_forecast(net: np.ndarray, price: np.ndarray, dates,
                              cutoff_day: int, net_hat48: np.ndarray,
                              start_slot: int = 0, n: int = 8, decay: float = .8,
                              lookback: int = 42, forecast_provider=None) -> tuple[np.ndarray,dict]:
    """严格历史EW价格基线，加滚动Ridge净负荷变化修正。"""
    net=np.asarray(net,float); price=np.asarray(price,float); slots=net.shape[1]
    release=cutoff_day*slots+start_slot; targets=release+np.arange(2*slots)
    nh=np.asarray(net_hat48,float)
    if nh.shape!=(2*slots,): raise ValueError("电价预测必须为严格48小时")
    provider=forecast_provider or (lambda j:np.r_[net[j-1],net[j-1]])
    xs=[]; ys=[]; max_used=-1
    for j in range(max(8,cutoff_day-lookback),cutoff_day):
        rel=j*slots+start_slot; tj=rel+np.arange(2*slots)
        pred=np.asarray(provider(j),float)
        if pred.shape!=(2*slots,): raise ValueError("历史预测版本必须为严格48小时")
        valid=(tj<release)&(tj<len(net.ravel()))
        if not np.any(valid): continue
        nb,ni=ew_history_profile(net,dates,tj[valid],rel,n,decay)
        pb,pi=ew_history_profile(price,dates,tj[valid],rel,n,decay)
        xs.extend((pred[valid]-nb).tolist()); ys.extend((price.ravel()[tj[valid]]-pb).tolist())
        max_used=max(max_used,int(tj[valid].max()),int(ni.max()),int(pi.max()))
    x=np.asarray(xs)[:,None]; y=np.asarray(ys)
    sc=StandardScaler().fit(x); model=Ridge(alpha=1.0).fit(sc.transform(x),y)
    nb,ni=ew_history_profile(net,dates,targets,release,n,decay)
    pb,pi=ew_history_profile(price,dates,targets,release,n,decay)
    max_used=max(max_used,int(ni.max()),int(pi.max()))
    pred=np.maximum(pb+model.predict(sc.transform((nh-nb)[:,None])),1e-6)
    meta={"n":int(n),"decay":float(decay),"ridge_alpha":1.0,"n_train":int(len(y)),
          "history_max_abs":int(max_used),"history_end":str(pd.Timestamp(dates[cutoff_day]).date())}
    return pred,meta


class EWPriceEngine(q4.Q4Engine):
    def __init__(self,data,n=8,decay=.8):
        super().__init__(data,price_gamma=1.0); self.ew_n=int(n); self.ew_decay=float(decay)
    def price48(self,d,k,net_hat,use_attachment=True):
        provider=lambda j:self.point48(j,k,use_attachment)
        return ew_coupled_price_forecast(self.net,self.data.price,self.data.dates,d,net_hat,
                 start_slot=q4.STAGE_SLOT[k],n=self.ew_n,decay=self.ew_decay,
                 forecast_provider=provider)[0]


def price_metrics(data,engine):
    rows=[]
    for label,days in (("一月14—31日",range(13,31)),("2—12月",range(31,365))):
        err=[]
        for d in days:
            pred=engine.price48(d,0,engine.point48(d,0,False),False)[:q4.T]
            err.extend(pred-data.price[d])
        e=np.asarray(err)
        rows.append({"评价期":label,"同类型EW_Ridge_MAE":float(np.mean(np.abs(e))),
                     "同类型EW_Ridge_RMSE":float(np.sqrt(np.mean(e**2)))})
    return pd.DataFrame(rows)


def select_ew_parameters(data, n_values=(2,4,8), decay_values=(.4,.6,.8)):
    """只用1月14—31日滚动回测选择同类型EW的N与衰减系数。"""
    rows=[]
    for n in n_values:
        for decay in decay_values:
            engine=EWPriceEngine(data,n,decay); err=[]
            for d in range(13,31):
                pred=engine.price48(d,0,engine.point48(d,0,False),False)[:q4.T]
                err.extend(pred-data.price[d])
            e=np.asarray(err,float)
            rows.append({"历史同类型日数N":int(n),"衰减系数lambda":float(decay),
                         "一月14—31日MAE":float(np.mean(np.abs(e))),
                         "一月14—31日RMSE":float(np.sqrt(np.mean(e**2)))})
    table=pd.DataFrame(rows).sort_values(["一月14—31日MAE","一月14—31日RMSE"]).reset_index(drop=True)
    return table,int(table.loc[0,"历史同类型日数N"]),float(table.loc[0,"衰减系数lambda"])


def run_compare(base=r"C:\Users\12055\Desktop\2026 国赛",out_dir=None):
    out=Path(out_dir or Path.cwd()); data=q4.load_official_data(base)
    selection,n,decay=select_ew_parameters(data)
    engine=EWPriceEngine(data,n,decay)
    pm=price_metrics(data,engine)
    rec2=engine.simulate_q2(); rec3=engine.simulate_q3()
    c2=q4.cost_q2(rec2['qplan'],rec2['emergency'],data.price[q4.START:])
    c3=q4.cost_q3(rec3['qplan'],rec3['qadj'],rec3['emergency'],data.price[q4.START:])
    old=pd.read_csv(out/'问题四_费用与求解指标.csv')
    rows=[]
    for scheme,cost in [('问题4-2',c2),('问题4-3',c3)]:
        oldrow=old.loc[old['方案']==scheme].iloc[0]
        oldtotal=float(oldrow['总费用_元']); newtotal=float(cost['总费用_元'])
        rows.append({'方案':scheme,'价格模型':'7日基线+Ridge','总费用_元':oldtotal,'相对旧模型节省_元':0.0})
        rows.append({'方案':scheme,'价格模型':f'同类型{n}日EW(λ={decay:g})+Ridge','总费用_元':newtotal,
                     '相对旧模型节省_元':oldtotal-newtotal})
    cmp=pd.DataFrame(rows)
    selection.to_csv(out/'EW一月选参.csv',index=False,encoding='utf-8-sig')
    pm.to_csv(out/'EW价格预测指标.csv',index=False,encoding='utf-8-sig')
    cmp.to_csv(out/'EW与7日基线_优化费用对比.csv',index=False,encoding='utf-8-sig')
    ewout=out/'EW方案结果'; ewout.mkdir(exist_ok=True)
    q4.export_results(rec2,rec3,data,Path(base)/'附件5',ewout)
    checks={'same_type_price_ew':True,'selection_uses_january_only':True,
            'q2_lp_all_success':bool(np.all(rec2['lp_status']==0)),'q3_lp_all_success':bool(np.all(rec3['lp_status']==0)),
            'q2_soc_bounds':bool(np.all((rec2['soc']>=q4.SMIN-1e-6)&(rec2['soc']<=q4.SMAX+1e-6))),
            'q3_soc_bounds':bool(np.all((rec3['soc']>=q4.SMIN-1e-6)&(rec3['soc']<=q4.SMAX+1e-6))),
            'q2_soc_continuity':bool(np.allclose(rec2['s0'][1:],rec2['soc'][:-1,-1])),
            'q3_soc_continuity':bool(np.allclose(rec3['s0'][1:],rec3['soc'][:-1,-1])),
            'q2_cost_identity':bool(np.isclose(c2['总费用_元'],c2['计划购电费_元']+c2['紧急购电费_元'])),
            'q3_cost_identity':bool(np.isclose(c3['总费用_元'],c3['计划购电费_元']+c3['调增费_元']-c3['调减退费_元']+c3['紧急购电费_元']))}
    (out/'EW方案运行验证.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
    print(pm.to_string(index=False)); print(cmp.to_string(index=False)); print(json.dumps(checks,ensure_ascii=False,indent=2))
    return pm,cmp,checks

if __name__=='__main__': run_compare(out_dir=Path(__file__).resolve().parent)
