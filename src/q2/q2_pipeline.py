from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.sparse import lil_matrix
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor
import torch
from torch import nn

DT = 1 / 6


def read_csv_auto(path: str | Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "gb18030", "utf-8"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise UnicodeError(f"无法识别编码：{path}")


def to_daily_matrices(raw: pd.DataFrame, year: int = 2025):
    """把“时段结束时刻”的长表转成 日期×144。

    例如 2025-02-01 00:00 是 1 月 31 日最后一个 10 分钟时段，
    所以用 时间-10分钟 确定计划所属日期。
    """
    need = {"时间", "小区负载", "光伏发电实际功率"}
    if not need.issubset(raw.columns):
        raise ValueError(f"缺少字段：{sorted(need - set(raw.columns))}")
    x = raw[list(need)].copy()
    x["时间"] = pd.to_datetime(x["时间"])
    if x["时间"].duplicated().any():
        raise ValueError("拼接后存在重复时间戳")
    x = x.sort_values("时间")
    x["计划日"] = (x["时间"] - pd.Timedelta(minutes=10)).dt.normalize()
    x = x[x["计划日"].dt.year.eq(year)]
    counts = x.groupby("计划日").size()
    bad = counts[counts.ne(144)]
    if len(bad):
        raise ValueError(f"以下计划日不是144条：{bad.to_dict()}")
    dates = pd.DatetimeIndex(sorted(x["计划日"].unique()))
    load = np.vstack([x.loc[x["计划日"].eq(d), "小区负载"].to_numpy(float) for d in dates])
    pv = np.vstack([x.loc[x["计划日"].eq(d), "光伏发电实际功率"].to_numpy(float) for d in dates])
    return dates, load, pv


def load_project_data(train_csv, future_csv, year=2025):
    raw = pd.concat([read_csv_auto(train_csv), read_csv_auto(future_csv)], ignore_index=True)
    return to_daily_matrices(raw, year=year)


def low_load_day(date) -> bool:
    return pd.Timestamp(date).dayofweek in (4, 5)


def _date_features(date, slots=144):
    date = pd.Timestamp(date)
    t = np.arange(slots) / slots
    dow = date.dayofweek
    doy = date.dayofyear
    return [
        np.sin(2*np.pi*t), np.cos(2*np.pi*t),
        np.sin(4*np.pi*t), np.cos(4*np.pi*t),
        np.full(slots, float(low_load_day(date))),
        np.full(slots, np.sin(2*np.pi*dow/7)),
        np.full(slots, np.cos(2*np.pi*dow/7)),
        np.full(slots, np.sin(2*np.pi*doy/365)),
        np.full(slots, np.cos(2*np.pi*doy/365)),
        np.full(slots, doy/365),
    ]


def build_features_for_day(y: np.ndarray, dates, d: int) -> np.ndarray:
    """用 d 之前的数据构造 d 日的滞后、差分、滚动与 calendar 特征。"""
    if d < 7:
        raise ValueError("至少需要7天历史")
    dates = pd.DatetimeIndex(dates)
    if d >= len(dates):
        target_date = dates[-1] + pd.Timedelta(days=d-len(dates)+1)
    else:
        target_date = dates[d]
    lag1, lag2, lag7 = y[d-1], y[d-2], y[d-7]
    r3, r7 = y[d-3:d], y[d-7:d]
    features = [
        lag1, lag2, lag7,
        lag1-lag2, lag1-lag7,
        r3.mean(0), r3.std(0), r7.mean(0), r7.std(0),
        np.full(y.shape[1], lag1.mean()),
        *_date_features(target_date, y.shape[1]),
    ]
    return np.column_stack(features)


def _training_xy(y, dates, cutoff, first_target=7):
    xs, ys = [], []
    for j in range(first_target, cutoff):
        xs.append(build_features_for_day(y, dates, j))
        ys.append(y[j])
    return np.vstack(xs), np.concatenate(ys)


def make_model(name: str, random_state=42):
    if name == "XGBoost":
        return XGBRegressor(
            n_estimators=100, max_depth=5, learning_rate=0.06,
            subsample=0.85, colsample_bytree=0.85,
            objective="reg:squarederror", random_state=random_state,
            n_jobs=-1, tree_method="hist", verbosity=0)
    raise ValueError(name)


def _force_nonnegative(pred, kind, history):
    pred = np.maximum(np.asarray(pred, float), 0.0)
    if kind == "pv":
        pred[np.max(history, axis=0) <= 0] = 0.0
    return pred


def rolling_ml_forecasts(y, dates, model_name, kind, start=14, end=None, refit_every=1):
    """XGBoost扩展窗口滚动预测；岭回归转到用户原始实现。"""
    if model_name == "岭回归":
        return rolling_original_ridge_forecasts(y, dates, kind, start, end)
    end = len(y) if end is None else end
    f1 = np.full_like(y, np.nan, dtype=float)
    f2 = np.full_like(y, np.nan, dtype=float)
    model = None
    for d in range(start, end):
        if model is None or (d-start) % refit_every == 0:
            xtr, ytr = _training_xy(y, dates, d)
            model = make_model(model_name)
            model.fit(xtr, ytr)
        p1 = _force_nonnegative(model.predict(build_features_for_day(y, dates, d)), kind, y[:d])
        y_tmp = np.vstack([y[:d], p1])
        dates_tmp = pd.DatetimeIndex(list(pd.DatetimeIndex(dates)[:d]) + [pd.DatetimeIndex(dates)[d]])
        p2 = _force_nonnegative(model.predict(build_features_for_day(y_tmp, dates_tmp, d+1)), kind, y_tmp)
        f1[d], f2[d] = p1, p2
    return f1, f2


def _original_ridge_fourier(slots: int) -> np.ndarray:
    """用户原Notebook的1、2、3阶日内Fourier特征。"""
    slot = np.arange(slots)
    return np.column_stack(
        [np.sin(2*np.pi*k*slot/slots) for k in (1, 2, 3)]
        + [np.cos(2*np.pi*k*slot/slots) for k in (1, 2, 3)])


def _original_ridge_same_type_mean(y, dates, cutoff, target_date, n=4):
    """用户原Notebook的最近4个同类型日等权均值。"""
    target_type = low_load_day(target_date)
    idx = [j for j in range(cutoff-1, -1, -1)
           if low_load_day(dates[j]) == target_type][:n]
    if not idx:
        raise ValueError("没有可用于同类型日均值的历史")
    return np.mean(y[idx], axis=0)


def build_original_ridge_features(y: np.ndarray, dates, d: int, kind: str) -> np.ndarray:
    """逐项迁移用户原Notebook的岭回归特征定义。"""
    if d < 7:
        raise ValueError("至少需要7天历史")
    dates = pd.DatetimeIndex(dates)
    target_date = (dates[d] if d < len(dates)
                   else dates[-1] + pd.Timedelta(days=d-len(dates)+1))
    previous_date = dates[d-1]
    y1, y2, y7 = y[d-1], y[d-2], y[d-7]
    m3 = y[d-3:d].mean(axis=0)
    m7 = y[d-7:d].mean(axis=0)
    s7 = y[d-7:d].std(axis=0)
    same_type = (_original_ridge_same_type_mean(y, dates, d, target_date, n=4)
                 if kind == "load" else m7)
    return np.column_stack([
        y1, y7, m3, m7, y1-y2, y1-m7, s7, same_type,
        np.full(y.shape[1], float(low_load_day(target_date))),
        np.full(y.shape[1], float(low_load_day(previous_date))),
        _original_ridge_fourier(y.shape[1]),
    ])


def rolling_original_ridge_forecasts(y, dates, kind, start=14, end=None,
                                     train_window=42, alpha=1.0):
    """用户原岭回归：近42天、alpha=1、原特征；每天0:00重拟合。

    第一天预测完全复现原Notebook。为48小时CCP新增的第二天预测，
    仅将第一天预测递归作为滞后量，不使用当天或未来真值。
    """
    end = len(y) if end is None else end
    dates = pd.DatetimeIndex(dates)
    f1 = np.full_like(y, np.nan, dtype=float)
    f2 = np.full_like(y, np.nan, dtype=float)
    for d in range(start, end):
        train_days = list(range(max(8, d-train_window), d))
        xtr = np.vstack([build_original_ridge_features(y, dates, j, kind)
                         for j in train_days])
        ytr = y[train_days].ravel()
        scaler = StandardScaler().fit(xtr)
        model = Ridge(alpha=alpha).fit(scaler.transform(xtr), ytr)

        p1 = model.predict(scaler.transform(
            build_original_ridge_features(y, dates, d, kind)))
        p1 = _force_nonnegative(p1, kind, y[:d])

        y_tmp = np.vstack([y[:d], p1])
        p2 = model.predict(scaler.transform(
            build_original_ridge_features(y_tmp, dates, d+1, kind)))
        p2 = _force_nonnegative(p2, kind, y_tmp)
        f1[d], f2[d] = p1, p2
    return f1, f2


class _GRUNet(nn.Module):
    def __init__(self, slots: int, hidden_size: int = 32):
        super().__init__()
        self.gru = nn.GRU(input_size=slots, hidden_size=hidden_size, batch_first=True)
        self.head = nn.Linear(hidden_size + 5, slots)

    def forward(self, sequence, calendar):
        h, _ = self.gru(sequence)
        return self.head(torch.cat([h[:, -1], calendar], dim=1))


def _gru_calendar(date):
    date = pd.Timestamp(date)
    dow, doy = date.dayofweek, date.dayofyear
    return np.array([
        float(low_load_day(date)),
        np.sin(2*np.pi*dow/7), np.cos(2*np.pi*dow/7),
        np.sin(2*np.pi*doy/365), np.cos(2*np.pi*doy/365),
    ], dtype=np.float32)


def _gru_training_data(y_scaled, dates, cutoff, seq_len=7):
    xs, cs, ys = [], [], []
    for j in range(seq_len, cutoff):
        xs.append(y_scaled[j-seq_len:j])
        cs.append(_gru_calendar(dates[j]))
        ys.append(y_scaled[j])
    return (
        torch.tensor(np.asarray(xs), dtype=torch.float32),
        torch.tensor(np.asarray(cs), dtype=torch.float32),
        torch.tensor(np.asarray(ys), dtype=torch.float32),
    )


def rolling_gru_forecasts(y, dates, kind, start=14, end=None, seq_len=7,
                          hidden_size=32, initial_epochs=120, update_epochs=5,
                          random_state=42):
    """GRU 逐日滚动预测：每天结束后将当天真值加入训练集并更新网络。"""
    if start <= seq_len:
        raise ValueError("GRU初始训练日必须大于序列长度")
    end = len(y) if end is None else end
    dates = pd.DatetimeIndex(dates)
    f1 = np.full_like(y, np.nan, dtype=float)
    f2 = np.full_like(y, np.nan, dtype=float)

    # 归一化参数只由首次预测前的历史确定，后续不回看未来。
    mean = y[:start].mean(axis=0)
    scale = y[:start].std(axis=0)
    scale[scale < 1e-6] = 1.0
    y_scaled = (y-mean)/scale

    torch.manual_seed(random_state)
    np.random.seed(random_state)
    torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
    model = _GRUNet(y.shape[1], hidden_size)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=1e-5)
    loss_fn = nn.MSELoss()

    def train_until(cutoff, epochs, lr):
        for group in optimizer.param_groups:
            group["lr"] = lr
        xtr, ctr, ytr = _gru_training_data(y_scaled, dates, cutoff, seq_len)
        model.train()
        for _ in range(epochs):
            optimizer.zero_grad()
            loss = loss_fn(model(xtr, ctr), ytr)
            loss.backward()
            optimizer.step()

    for d in range(start, end):
        # d>start 时，d-1 日已结束并成为新的已知训练样本。
        train_until(d, initial_epochs if d == start else update_epochs,
                    0.01 if d == start else 0.003)
        model.eval()
        with torch.no_grad():
            seq1 = torch.tensor(y_scaled[d-seq_len:d][None], dtype=torch.float32)
            cal1 = torch.tensor(_gru_calendar(dates[d])[None], dtype=torch.float32)
            p1 = model(seq1, cal1).numpy()[0]*scale + mean
            p1 = _force_nonnegative(p1, kind, y[:d])

            p1_scaled = (p1-mean)/scale
            seq2_np = np.vstack([y_scaled[d-seq_len+1:d], p1_scaled])
            seq2 = torch.tensor(seq2_np[None], dtype=torch.float32)
            cal2 = torch.tensor(_gru_calendar(dates[d] + pd.Timedelta(days=1))[None], dtype=torch.float32)
            p2 = model(seq2, cal2).numpy()[0]*scale + mean
            p2 = _force_nonnegative(p2, kind, np.vstack([y[:d], p1]))
        f1[d], f2[d] = p1, p2
    return f1, f2


def _weights(n=8, decay=0.6):
    w = decay ** np.arange(n)
    return w / w.sum()


def ew_point(y, dates, cutoff, target_date, kind, n=8, decay=0.6):
    if kind == "load":
        same = low_load_day(target_date)
        idx = [j for j in range(cutoff-1, -1, -1) if low_load_day(dates[j]) == same][:n]
    else:
        idx = list(range(cutoff-1, max(-1, cutoff-n-1), -1))
    w = _weights(len(idx), decay)
    pred = (w[:, None] * y[idx]).sum(0)
    return _force_nonnegative(pred, kind, y[:cutoff])


def rolling_ew_forecasts(y, dates, kind, start=14, end=None, n=8, decay=0.6):
    end = len(y) if end is None else end
    f1 = np.full_like(y, np.nan, dtype=float)
    f2 = np.full_like(y, np.nan, dtype=float)
    dates = pd.DatetimeIndex(dates)
    for d in range(start, end):
        f1[d] = ew_point(y, dates, d, dates[d], kind, n, decay)
        f2[d] = ew_point(y, dates, d, dates[d] + pd.Timedelta(days=1), kind, n, decay)
    return f1, f2


def make_all_forecasts(load, pv, dates, start=14, end=None, ml_refit_every=1,
                       gru_initial_epochs=120, gru_update_epochs=5):
    out = {}
    out["EW/EWMA"] = {
        "load": rolling_ew_forecasts(load, dates, "load", start, end),
        "pv": rolling_ew_forecasts(pv, dates, "pv", start, end)}
    out["岭回归"] = {
        "load": rolling_original_ridge_forecasts(load, dates, "load", start, end),
        "pv": rolling_original_ridge_forecasts(pv, dates, "pv", start, end)}
    out["XGBoost"] = {
        "load": rolling_ml_forecasts(load, dates, "XGBoost", "load", start, end, ml_refit_every),
        "pv": rolling_ml_forecasts(pv, dates, "XGBoost", "pv", start, end, ml_refit_every)}
    out["GRU"] = {
        "load": rolling_gru_forecasts(load, dates, "load", start, end,
                                      initial_epochs=gru_initial_epochs, update_epochs=gru_update_epochs),
        "pv": rolling_gru_forecasts(pv, dates, "pv", start, end,
                                    initial_epochs=gru_initial_epochs, update_epochs=gru_update_epochs)}
    return out


def forecast_metrics(eps: np.ndarray) -> Dict[str, float]:
    eps = np.asarray(eps, float)
    e_day = eps.sum(axis=1)
    pin = np.where(e_day >= 0, 0.8*e_day, 0.2*np.abs(e_day))
    max_gap = np.maximum(0, np.cumsum(eps, axis=1).max(axis=1))
    return {
        "逐时段RMSE": float(np.sqrt(np.mean(eps**2))),
        "平均日电量绝对误差": float(np.mean(np.abs(e_day))),
        "平均日Pinball损失": float(np.mean(pin)),
        "平均最大累计缺口": float(np.mean(max_gap)),
        "最大累计缺口P95": float(np.quantile(max_gap, 0.95)),
    }


def model_metrics_table(forecasts, load, pv, start, end):
    """按指定日期切片计算模型指标；只使用各模型的一步预测。"""
    net = (load-pv)*DT
    rows = {}
    for name, item in forecasts.items():
        fl, fg = item["load"][0], item["pv"][0]
        eps = net[start:end] - (fl[start:end]-fg[start:end])*DT
        rows[name] = forecast_metrics(eps)
    result = pd.DataFrame(rows).T.sort_values("平均日Pinball损失")
    result.index.name = "模型"
    return result


def january_model_table(forecasts, load, pv, start=14, end=31):
    return model_metrics_table(forecasts, load, pv, start, end)


def solve_plan_lp(load_energy, pv_energy, price, s0, periods_per_day=144,
                  eta=.9, rmax=5000/6, smin=1200., smax=10800.):
    """求解今天+明天，返回仅今天的计划购电量。"""
    load_energy = np.asarray(load_energy, float)
    pv_energy = np.asarray(pv_energy, float)
    price = np.asarray(price, float)
    h = 2*periods_per_day
    if not (len(load_energy) == len(pv_energy) == len(price) == h):
        raise ValueError("48小时输入长度不一致")
    nv = 6*h
    eu, es, qu, qs, v, soc = [np.arange(h)+k*h for k in range(6)]
    c = np.zeros(nv); c[qu] = price; c[qs] = price
    bounds = [(0, None)]*(5*h) + [(smin, smax)]*h
    aub = lil_matrix((2*h, nv)); bub = np.r_[pv_energy, np.full(h, rmax)]
    for t in range(h):
        aub[t, eu[t]] = 1; aub[t, es[t]] = 1
        aub[h+t, es[t]] = 1; aub[h+t, qs[t]] = 1; aub[h+t, v[t]] = 1
    aeq = lil_matrix((2*h, nv)); beq = np.r_[load_energy, s0, np.zeros(h-1)]
    for t in range(h):
        aeq[t, eu[t]] = 1; aeq[t, qu[t]] = 1; aeq[t, v[t]] = 1
        r = h+t
        aeq[r, soc[t]] = 1; aeq[r, es[t]] = -eta; aeq[r, qs[t]] = -eta; aeq[r, v[t]] = 1/eta
        if t > 0: aeq[r, soc[t-1]] = -1
    res = linprog(c, A_ub=aub.tocsr(), b_ub=bub, A_eq=aeq.tocsr(), b_eq=beq,
                  bounds=bounds, method="highs")
    status = {"success": bool(res.success), "status": int(res.status), "message": res.message}
    if not res.success:
        return np.full(periods_per_day, np.nan), status
    return res.x[qu][:periods_per_day] + res.x[qs][:periods_per_day], status


def settle_day(q, true_net_energy, s0, eta=.9, rmax=5000/6, smin=1200., smax=10800.):
    q = np.asarray(q, float); net = np.asarray(true_net_energy, float)
    n = len(q)
    charge = np.zeros(n); discharge = np.zeros(n); emergency = np.zeros(n); curtail = np.zeros(n); soc = np.zeros(n)
    s = float(s0)
    for t in range(n):
        surplus = q[t]-net[t]
        if surplus > 0:
            charge[t] = min(surplus, rmax, (smax-s)/eta)
            curtail[t] = surplus-charge[t]
        elif surplus < 0:
            discharge[t] = min(-surplus, rmax, eta*(s-smin))
            emergency[t] = -surplus-discharge[t]
        s += eta*charge[t]-discharge[t]/eta
        soc[t] = s
    return {"charge": charge, "discharge": discharge, "emergency": emergency,
            "curtail": curtail, "soc": soc}


def run_ccp(name, item, load, pv, price_day, start=31, alpha=.8, lookback=14,
            eta=.9, rmax=5000/6, smin=1200., smax=10800., s_init=6000.):
    net = (load-pv)*DT
    fl1, fl2 = item["load"]; fg1, fg2 = item["pv"]
    pred_net = (fl1-fg1)*DT
    residual = net-pred_net
    s = s_init
    plan_cost = emergency_cost = emergency_increment = 0.0
    emergency_kwh = 0.0; emergency_days = 0; failed = 0
    daily = []
    price48 = np.r_[price_day, price_day]
    for d in range(start, len(load)):
        rho = np.quantile(residual[d-lookback:d], alpha, axis=0)
        req = np.r_[fl1[d]*DT+rho, fl2[d]*DT+rho]
        pve = np.r_[fg1[d], fg2[d]]*DT
        q, status = solve_plan_lp(req, pve, price48, s, 144, eta, rmax, smin, smax)
        if not status["success"]:
            failed += 1
            raise RuntimeError(f"{name} {d}日 LP失败：{status['message']}")
        settled = settle_day(q, net[d], s, eta, rmax, smin, smax)
        s = settled["soc"][-1]
        emg = settled["emergency"]
        pc = float(np.dot(price_day, q)); ec = float(np.dot(5*price_day, emg)); ei = float(np.dot(4*price_day, emg))
        plan_cost += pc; emergency_cost += ec; emergency_increment += ei
        emergency_kwh += emg.sum(); emergency_days += int(emg.sum() > 1e-6)
        daily.append({"日序号": d,
                      "计划购电费": pc, "紧急购电费": ec, "紧急购电量": emg.sum(), "日末SOC": s})
    return {
        "模型": name,
        "计划购电费_万元": plan_cost/1e4,
        "紧急购电费_万元": emergency_cost/1e4,
        "其中惩罚增量_万元": emergency_increment/1e4,
        "总费用_万元": (plan_cost+emergency_cost)/1e4,
        "紧急购电量_kWh": emergency_kwh,
        "惩罚天数": emergency_days,
        "优化失败天数": failed,
        "日明细": pd.DataFrame(daily),
    }
