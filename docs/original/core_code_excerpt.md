# 四问预测与优化核心代码汇总

本文档从四个支撑材料文件夹中抽取最核心、最能复现建模主线的代码。筛选原则如下：

- 保留数据进入模型后的关键处理、预测模型、优化模型、滚动/分阶段求解、结算与校验逻辑。
- 排除测试代码、缓存、纯绘图脚本、Notebook 构建脚本、历史备份和结果数据文件。
- 代码保持原样，仅按原文件的完整逻辑区段截取；来源和截取范围均在各节注明。
- 第三问以 Notebook 为唯一主实现，因此按代码单元抽取。

> 注意：本文档用于集中阅读核心算法。部分片段仍依赖原文件夹内的数据文件、第三方库或同目录模块；如需直接运行，请回到对应原项目环境。


## 第一问：储能调度预测与优化

来源：`第一问预测+优化/solve_q1.py（第 1–416 行）`

包含数据结构、时段处理、附件读取、储能调度线性规划、可行性校验与结果摘要。绘图、Excel 导出和命令行包装未纳入。

```python
"""2026 年国赛 C 题问题 1：微网计划购电优化。"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path
from typing import Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from scipy.optimize import linprog
from scipy.sparse import lil_matrix


DELTA_T_HOURS = 1.0 / 6.0


@dataclass
class DispatchData:
    """问题 1 的逐时段输入数据。"""

    end_times: list[str]
    price: np.ndarray
    load_power: np.ndarray
    pv_power: np.ndarray
    load_energy: np.ndarray
    pv_energy: np.ndarray


@dataclass
class DispatchSolution:
    """线性规划返回的逐时段决策结果。"""

    success: bool
    status: int
    message: str
    total_cost: float
    pv_to_load: np.ndarray
    pv_to_storage: np.ndarray
    grid_to_load: np.ndarray
    grid_to_storage: np.ndarray
    discharge: np.ndarray
    soc: np.ndarray


def _normalise_end_time(value: object) -> str:
    if isinstance(value, datetime):
        value = value.time()
    if isinstance(value, time):
        return value.strftime("%H:%M")
    text = str(value).strip()
    if text in {"0:00+1", "00:00+1"}:
        return "0:00+1"
    if ":" in text:
        parts = text.split(":")
        try:
            return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
        except (ValueError, IndexError):
            pass
    return text


def interval_labels_from_end_times(end_times: Sequence[str]) -> list[str]:
    """把表中“区间结束时刻”转换为十分钟区间标签。"""

    labels: list[str] = []
    for raw in end_times:
        text = _normalise_end_time(raw)
        if text == "0:00+1":
            end_minutes = 24 * 60
        else:
            try:
                hour_text, minute_text = text.split(":")[:2]
                end_minutes = int(hour_text) * 60 + int(minute_text)
            except (ValueError, IndexError) as exc:
                raise ValueError(f"无法识别时间：{raw}") from exc
        start_minutes = end_minutes - 10
        if start_minutes < 0:
            raise ValueError(f"结束时刻早于第一个十分钟区间：{raw}")

        def format_minutes(value: int) -> str:
            if value == 24 * 60:
                return "24:00"
            return f"{value // 60:02d}:{value % 60:02d}"

        labels.append(f"{format_minutes(start_minutes)}-{format_minutes(end_minutes)}")
    return labels


def interval_plot_coordinates(periods: int) -> tuple[np.ndarray, np.ndarray]:
    """返回十分钟区间的边界和中心坐标（小时）。"""

    if periods <= 0:
        raise ValueError("绘图区间数必须为正整数")
    edges = np.arange(periods + 1, dtype=float) * DELTA_T_HOURS
    centres = edges[:-1] + DELTA_T_HOURS / 2.0
    return edges, centres


def load_attachment1(path: str | Path) -> DispatchData:
    """读取附件 1，并把 kW 按 10 分钟换算为 kWh。"""

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"找不到附件 1：{path}")

    workbook = load_workbook(path, read_only=True, data_only=True)
    sheet = workbook.active
    rows = list(sheet.iter_rows(min_row=2, values_only=True))
    if not rows:
        raise ValueError("附件 1 没有数据行")
    if any(len(row) < 4 or any(value is None for value in row[:4]) for row in rows):
        raise ValueError("附件 1 的时间、电价、负载或光伏列存在空值")

    end_times = [_normalise_end_time(row[0]) for row in rows]
    price = np.asarray([float(row[1]) for row in rows], dtype=float)
    load_power = np.asarray([float(row[2]) for row in rows], dtype=float)
    pv_power = np.asarray([float(row[3]) for row in rows], dtype=float)

    if np.any(price < 0) or np.any(load_power < 0) or np.any(pv_power < 0):
        raise ValueError("附件 1 出现负电价、负负载或负光伏功率")

    return DispatchData(
        end_times=end_times,
        price=price,
        load_power=load_power,
        pv_power=pv_power,
        load_energy=load_power * DELTA_T_HOURS,
        pv_energy=pv_power * DELTA_T_HOURS,
    )


def solve_dispatch(
    data: DispatchData,
    *,
    eta: float = 0.9,
    rate_limit: float = 5000.0 * DELTA_T_HOURS,
    soc_min: float = 1200.0,
    soc_max: float = 10800.0,
    soc_initial: float = 6000.0,
    soc_terminal: float = 6000.0,
) -> DispatchSolution:
    """按题设线性规划求解问题 1。

    所有流量变量均为每个时段累计电量（kWh）。充电量与放电量
    之和不超过单时段吞吐上限，允许十分钟内分时切换工作模式。
    """

    n = len(data.price)
    arrays = (
        data.load_power,
        data.pv_power,
        data.load_energy,
        data.pv_energy,
    )
    if n == 0 or any(len(values) != n for values in arrays):
        raise ValueError("输入数组长度不一致或为空")
    if not 0.0 < eta <= 1.0:
        raise ValueError("eta 必须位于 (0, 1] 内")
    if rate_limit <= 0.0 or soc_min > soc_max:
        raise ValueError("充放电上限或储能容量边界无效")
    if not soc_min <= soc_initial <= soc_max:
        raise ValueError("初始储电量不在容量范围内")
    if not soc_min <= soc_terminal <= soc_max:
        raise ValueError("终止储电量不在容量范围内")

    # 变量分块：e^u, e^s, g^u, g^s, d, S。
    def variable(block: int, period: int) -> int:
        return block * n + period

    objective = np.zeros(6 * n, dtype=float)
    objective[2 * n : 3 * n] = data.price
    objective[3 * n : 4 * n] = data.price

    # 不等式统一写成 A_ub @ x <= b_ub。
    # 1) e^u + g^u + d >= l；2) e^u + e^s <= G；
    # 3) e^s + g^s + d <= R_max（区间内分时充放电）。
    a_ub = lil_matrix((3 * n, 6 * n), dtype=float)
    b_ub = np.zeros(3 * n, dtype=float)
    for t in range(n):
        a_ub[t, variable(0, t)] = -1.0
        a_ub[t, variable(2, t)] = -1.0
        a_ub[t, variable(4, t)] = -1.0
        b_ub[t] = -data.load_energy[t]

        a_ub[n + t, variable(0, t)] = 1.0
        a_ub[n + t, variable(1, t)] = 1.0
        b_ub[n + t] = data.pv_energy[t]

        a_ub[2 * n + t, variable(1, t)] = 1.0
        a_ub[2 * n + t, variable(3, t)] = 1.0
        a_ub[2 * n + t, variable(4, t)] = 1.0
        b_ub[2 * n + t] = rate_limit

    # n 条状态转移方程，加 1 条终止储电量方程。
    a_eq = lil_matrix((n + 1, 6 * n), dtype=float)
    b_eq = np.zeros(n + 1, dtype=float)
    for t in range(n):
        a_eq[t, variable(5, t)] = 1.0
        if t == 0:
            b_eq[t] = soc_initial
        else:
            a_eq[t, variable(5, t - 1)] = -1.0
        a_eq[t, variable(1, t)] = -eta
        a_eq[t, variable(3, t)] = -eta
        a_eq[t, variable(4, t)] = 1.0 / eta

    a_eq[n, variable(5, n - 1)] = 1.0
    b_eq[n] = soc_terminal

    bounds = [(0.0, None)] * (5 * n) + [(soc_min, soc_max)] * n
    result = linprog(
        objective,
        A_ub=a_ub.tocsr(),
        b_ub=b_ub,
        A_eq=a_eq.tocsr(),
        b_eq=b_eq,
        bounds=bounds,
        method="highs",
    )
    if not result.success:
        empty = np.full(n, np.nan)
        return DispatchSolution(
            success=False,
            status=int(result.status),
            message=str(result.message),
            total_cost=float("nan"),
            pv_to_load=empty.copy(),
            pv_to_storage=empty.copy(),
            grid_to_load=empty.copy(),
            grid_to_storage=empty.copy(),
            discharge=empty.copy(),
            soc=empty.copy(),
        )

    x = np.asarray(result.x, dtype=float)
    return DispatchSolution(
        success=True,
        status=int(result.status),
        message=str(result.message),
        total_cost=float(result.fun),
        pv_to_load=x[0:n].copy(),
        pv_to_storage=x[n : 2 * n].copy(),
        grid_to_load=x[2 * n : 3 * n].copy(),
        grid_to_storage=x[3 * n : 4 * n].copy(),
        discharge=x[4 * n : 5 * n].copy(),
        soc=x[5 * n : 6 * n].copy(),
    )


def validate_solution(
    data: DispatchData,
    solution: DispatchSolution,
    *,
    eta: float = 0.9,
    rate_limit: float = 5000.0 * DELTA_T_HOURS,
    soc_min: float = 1200.0,
    soc_max: float = 10800.0,
    soc_initial: float = 6000.0,
    soc_terminal: float = 6000.0,
    tolerance: float = 1e-6,
) -> dict[str, float]:
    """独立重算所有核心约束；发现违反时立即报错。"""

    if not solution.success:
        raise ValueError(f"求解器未返回可行最优解：{solution.message}")

    flows = (
        solution.pv_to_load,
        solution.pv_to_storage,
        solution.grid_to_load,
        solution.grid_to_storage,
        solution.discharge,
    )
    n = len(data.price)
    if any(len(values) != n for values in (*flows, solution.soc)):
        raise ValueError("解向量长度与输入时段数不一致")
    if not np.isfinite(solution.total_cost) or any(
        not np.all(np.isfinite(values)) for values in (*flows, solution.soc)
    ):
        raise ValueError("目标值和全部解向量必须为有限数")
    if min(float(np.min(values)) for values in flows) < -tolerance:
        raise ValueError("解中出现负的电量决策")

    charge = solution.pv_to_storage + solution.grid_to_storage
    throughput = charge + solution.discharge
    if float(np.max(throughput - rate_limit)) > tolerance:
        raise ValueError("充放电总量超过单时段上限")

    pv_used = solution.pv_to_load + solution.pv_to_storage
    if float(np.max(pv_used - data.pv_energy)) > tolerance:
        raise ValueError("使用的光伏电量超过可用光伏电量")

    supply = solution.pv_to_load + solution.grid_to_load + solution.discharge
    shortage = data.load_energy - supply
    if float(np.max(shortage)) > tolerance:
        raise ValueError("微网供电量低于小区负载")

    if float(np.min(solution.soc)) < soc_min - tolerance:
        raise ValueError("储电量低于下限")
    if float(np.max(solution.soc)) > soc_max + tolerance:
        raise ValueError("储电量高于上限")

    previous_soc = np.r_[soc_initial, solution.soc[:-1]]
    expected_soc = previous_soc + eta * charge - solution.discharge / eta
    state_residual = solution.soc - expected_soc
    if float(np.max(np.abs(state_residual))) > tolerance:
        raise ValueError("储能状态转移方程不成立")
    if abs(float(solution.soc[-1]) - soc_terminal) > tolerance:
        raise ValueError("终止储电量不符合要求")

    recalculated_cost = float(
        np.dot(data.price, solution.grid_to_load + solution.grid_to_storage)
    )
    if abs(recalculated_cost - solution.total_cost) > max(tolerance, tolerance * abs(recalculated_cost)):
        raise ValueError("目标函数值与逐时段费用不一致")

    return {
        "max_shortage_kwh": max(0.0, float(np.max(shortage))),
        "max_supply_surplus_kwh": max(0.0, float(np.max(-shortage))),
        "max_pv_excess_kwh": max(0.0, float(np.max(pv_used - data.pv_energy))),
        "max_throughput_excess_kwh": max(0.0, float(np.max(throughput - rate_limit))),
        "max_state_residual_kwh": float(np.max(np.abs(state_residual))),
        "terminal_soc_residual_kwh": abs(float(solution.soc[-1]) - soc_terminal),
    }


def build_summary(
    data: DispatchData,
    solution: DispatchSolution,
    validation: dict[str, float],
    *,
    soc_initial: float = 6000.0,
) -> dict[str, object]:
    """汇总论文中最常用的购电、储能与校验指标。"""

    labels = interval_labels_from_end_times(data.end_times)
    grid = solution.grid_to_load + solution.grid_to_storage
    charge = solution.pv_to_storage + solution.grid_to_storage
    pv_used = solution.pv_to_load + solution.pv_to_storage
    curtailed = np.maximum(data.pv_energy - pv_used, 0.0)
    interval_cost = data.price * grid
    baseline_grid = np.maximum(data.load_energy - data.pv_energy, 0.0)
    baseline_cost = float(np.dot(data.price, baseline_grid))
    savings = baseline_cost - solution.total_cost
    savings_rate = savings / baseline_cost if baseline_cost > 0 else 0.0

    specified_labels = [
        "10:00-10:10",
        "12:00-12:10",
        "14:00-14:10",
        "16:00-16:10",
        "18:00-18:10",
        "20:00-20:10",
    ]
    label_to_index = {label: index for index, label in enumerate(labels)}
    specified_intervals = []
    for label in specified_labels:
        index = label_to_index[label]
        specified_intervals.append(
            {
                "时间段": label,
                "购电量_kWh": float(grid[index]),
                "时段购电费_元": float(interval_cost[index]),
            }
        )

    four_hour_summary = []
    periods_per_group = 4 * 6
    for group in range(6):
        start = group * periods_per_group
        end = (group + 1) * periods_per_group
        four_hour_summary.append(
            {
                "时间段": f"{group * 4:02d}:00-{(group + 1) * 4:02d}:00",
                "充电量_kWh": float(np.sum(charge[start:end])),
                "放电量_kWh": float(np.sum(solution.discharge[start:end])),
            }
        )

    return {
        "solver_status": "Optimal" if solution.success else "Failed",
        "solver_message": solution.message,
        "periods": len(data.price),
        "total_cost_yuan": float(solution.total_cost),
        "total_grid_purchase_kwh": float(np.sum(grid)),
        "grid_to_load_kwh": float(np.sum(solution.grid_to_load)),
        "grid_to_storage_kwh": float(np.sum(solution.grid_to_storage)),
        "total_load_kwh": float(np.sum(data.load_energy)),
        "total_pv_available_kwh": float(np.sum(data.pv_energy)),
        "total_pv_used_kwh": float(np.sum(pv_used)),
        "pv_curtailed_kwh": float(np.sum(curtailed)),
        "total_charge_kwh": float(np.sum(charge)),
        "total_discharge_kwh": float(np.sum(solution.discharge)),
        "soc_initial_kwh": float(soc_initial),
        "soc_terminal_kwh": float(solution.soc[-1]),
        "soc_min_observed_kwh": float(np.min(solution.soc)),
        "soc_max_observed_kwh": float(np.max(solution.soc)),
        "no_storage_baseline_cost_yuan": baseline_cost,
        "cost_saving_vs_no_storage_yuan": float(savings),
        "cost_saving_rate": float(savings_rate),
        "intervals_with_both_charge_and_discharge": int(
            np.sum((charge > 1e-7) & (solution.discharge > 1e-7))
        ),
        "specified_intervals": specified_intervals,
        "four_hour_summary": four_hour_summary,
        "validation": validation,
    }
```


## 第二问：逐日滚动预测与 CCP 优化

来源：`第二问预测&优化/q2_pipeline.py（完整文件）`

该文件本身就是紧凑的核心计算模块，包含特征工程、多模型滚动预测、EW 融合、评价指标、日前计划 LP、日内结算及 CCP 全流程。

```python
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
```


## 第三问：多阶段预测更新与优化

来源：`第三问预测+优化/问题三_预测与优化.ipynb（代码单元 2、7、9）`

包含数据装载、EW 基准预测、24 点到 48 点下采样、卡尔曼式预测修正、残差场景、多阶段优化、滚动仿真、费用计算、参数选择，以及主仿真调用。纯展示、绘图和 Excel 回填单元未纳入。

```python
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.sparse import csr_matrix, lil_matrix

# ---------- constants ----------
T, DT = 144, 1 / 6
START = 31
SELECT_DAYS = range(10, START)
ISSUE = [0, 6, 12, 18]
STAGE_SLOT = [0, 36, 72, 108]
ETA, R_MAX, SMIN, SMAX = 0.9, 5000 / 6, 1200.0, 10800.0
PEN, UP, DN = 5.0, 1.5, 0.5
EW_N, EW_DECAY, RESID_LOOK, FUSER_LOOK = 8, 0.6, 14, 14
DAY0 = pd.Timestamp("2025-01-01")


def resolve_file(name: str, candidates: list[str]) -> Path:
    for raw in candidates:
        p = Path(raw)
        if p.exists():
            return p
    raise FileNotFoundError(f"找不到 {name}；已检查：{candidates}")


DATA1 = resolve_file("附件1.xlsx", [
    "附件1.xlsx", r"C:\Users\12055\Desktop\2026 国赛\附件1.xlsx",
    r"C:\Users\12055\Desktop\Hermes\2026国赛C题\official\extracted\C题\附件\附件1.xlsx",
])
DATA2 = resolve_file("附件2.xlsx", [
    "附件2.xlsx", r"C:\Users\12055\Desktop\2026 国赛\附件2.xlsx",
    r"C:\Users\12055\Desktop\Hermes\2026国赛C题\official\extracted\C题\附件\附件2.xlsx",
])
DATA3 = resolve_file("附件3.xlsx", [
    "附件3.xlsx", r"C:\Users\12055\Desktop\2026 国赛\附件3.xlsx",
    r"C:\Users\12055\Desktop\Hermes\2026国赛C题\official\extracted\C题\附件\附件3.xlsx",
])
RESULT3_TEMPLATE = resolve_file("result3.xlsx", [
    "result3.xlsx", r"C:\Users\12055\Desktop\2026 国赛\附件5\result3.xlsx",
    r"C:\Users\12055\Desktop\Hermes\2026国赛C题\official\extracted\C题\附件\附件5\result3.xlsx",
])

price = pd.read_excel(DATA1)["电价"].to_numpy(float)
Ld = pd.read_excel(DATA2, sheet_name="小区负载")
L = Ld.iloc[:, 1:].to_numpy(float)
Gv = pd.read_excel(DATA2, sheet_name="光伏发电实际功率").iloc[:, 1:].to_numpy(float)
dates = pd.DatetimeIndex(pd.to_datetime(Ld.iloc[:, 0]))
ND = len(dates)
assert L.shape == Gv.shape == (365, T)
assert len(price) == T

F = pd.read_excel(DATA3)
F["日期"] = pd.to_datetime(F["日期"].ffill())
F["h0"] = F["预报时刻"].astype(str).str.split(":").str[0].astype(int)
FC = np.full((ND, 4, 25), np.nan)
for _, row in F.iterrows():
    d = (row["日期"] - DAY0).days
    if 0 <= d < ND:
        k = ISSUE.index(int(row["h0"]))
        for h in range(1, 25):
            FC[d, k, h] = float(row[f"预报{h}小时"])

Lflat, Gflat = L.ravel(), Gv.ravel()


def low_type(target_day: int) -> bool:
    return (DAY0 + pd.Timedelta(days=int(target_day))).dayofweek in (4, 5)


@lru_cache(None)
def ew_load_day(cutoff: int, target_day: int) -> np.ndarray:
    idx = [j for j in range(cutoff - 1, -1, -1) if low_type(j) == low_type(target_day)][:EW_N]
    w = EW_DECAY ** np.arange(len(idx)); w /= w.sum()
    return np.sum(w[:, None] * L[idx], axis=0)


@lru_cache(None)
def ew_pv_day(cutoff: int, target_day: int) -> np.ndarray:
    idx = list(range(cutoff - 1, max(-1, cutoff - EW_N - 1), -1))
    w = EW_DECAY ** np.arange(len(idx)); w /= w.sum()
    pred = np.sum(w[:, None] * Gv[idx], axis=0)
    pred[Gv[:cutoff].max(axis=0) <= 0] = 0
    return np.maximum(pred, 0)


def ew_abs(kind: str, cutoff: int, abs_slots: np.ndarray) -> np.ndarray:
    out = np.empty(len(abs_slots), float)
    for td in np.unique(abs_slots // T):
        m = abs_slots // T == td
        day_pred = ew_load_day(cutoff, int(td)) if kind == "load" else ew_pv_day(cutoff, int(td))
        out[m] = day_pred[abs_slots[m] % T]
    return out


def downscale_24h(d: int, k: int, method: str = "linear") -> tuple[np.ndarray, np.ndarray]:
    """保留发布后完整24小时；返回绝对目标时段及10分钟预报。"""
    release = d * T + STAGE_SLOT[k]
    x = np.arange(release, release + T)  # release + T 明确跨日保留
    anchors = release + 6 * np.arange(1, 25) - 1
    vals = FC[d, k, 1:25].astype(float)
    prev = Gflat[release - 1] if release > 0 else 0.0
    if method == "linear":
        out = np.interp(x, np.r_[release - 1, anchors], np.r_[prev, vals])
    elif method == "hold":
        out = np.repeat(vals, 6)
    elif method == "shape":
        base = ew_abs("pv", d, x)
        out = np.interp(x, np.r_[release - 1, anchors], np.r_[prev, vals])
        for pos, value in zip(anchors, vals):
            m = (x >= pos - 5) & (x <= pos)
            seg = base[m]
            if len(seg) and seg[-1] > 1e-6:
                out[m] = value * seg / seg[-1]
    else:
        raise ValueError(method)
    return x, np.maximum(out, 0)


def january_alignment_table() -> pd.DataFrame:
    rows = []
    hourly = Gv.reshape(ND, 24, 6).mean(2).ravel()
    for mode in ("小时均值", "小时末瞬时", "小时初瞬时"):
        for off in (0, -1):
            err = []
            for d in SELECT_DAYS:
                for k, h0 in enumerate(ISSUE):
                    for h in range(1, 25):
                        hour_abs = d * 24 + h0 + h + off
                        if mode == "小时均值":
                            if 0 <= hour_abs < START * 24:
                                err.append(FC[d, k, h] - hourly[hour_abs])
                        else:
                            slot_abs = hour_abs * 6 - (1 if mode == "小时末瞬时" else 0)
                            if 0 <= slot_abs < START * T:
                                err.append(FC[d, k, h] - Gflat[slot_abs])
            rows.append({"对齐方式": mode, "偏移": off, "一月MAE/kW": np.mean(np.abs(err))})
    return pd.DataFrame(rows).sort_values("一月MAE/kW").reset_index(drop=True)


def january_downscale_table() -> pd.DataFrame:
    rows = []
    for method in ("hold", "linear", "shape"):
        err = []
        for d in SELECT_DAYS:
            for k in range(4):
                pos, pred = downscale_24h(d, k, method)
                m = pos < START * T
                act = Gflat[pos[m]]; p = pred[m]
                daylight = (act > 50) | (p > 50)
                if daylight.any(): err.extend(p[daylight] - act[daylight])
        e = np.asarray(err)
        rows.append({"方法": method, "一月MAE/kW": np.abs(e).mean(), "一月RMSE/kW": np.sqrt(np.mean(e**2))})
    return pd.DataFrame(rows).sort_values("一月MAE/kW").reset_index(drop=True)


# 方法只由一月选择；在后续期冻结。
ALIGNMENT_TABLE = january_alignment_table()
DOWNSCALE_TABLE = january_downscale_table()
SELECTED_DOWNSCALE = str(DOWNSCALE_TABLE.iloc[0]["方法"])
FC10 = np.full((ND, 4, T), np.nan)
for d in range(ND):
    for k in range(4):
        FC10[d, k] = downscale_24h(d, k, SELECTED_DOWNSCALE)[1]


@lru_cache(None)
def point_forecast48(d: int, k: int, use_attachment: bool = True) -> np.ndarray:
    """决策时刻起严格48小时净负荷点预测，只用d日前真值与当时已发布预报。"""
    release = d * T + STAGE_SLOT[k]
    abs_slots = np.arange(release, release + 2 * T)
    load_hat = ew_abs("load", d, abs_slots)
    pv_ew = ew_abs("pv", d, abs_slots)
    pv_hat = pv_ew.copy()
    if use_attachment:
        for r in range(T):
            target = release + r
            if target >= len(Gflat) + T:
                continue
            efc, eew = [], []
            for j in range(d - 1, max(7, d - FUSER_LOOK - 3), -1):
                hist_target = j * T + STAGE_SLOT[k] + r
                if hist_target >= release or hist_target >= len(Gflat):
                    continue
                f = FC10[j, k, r]
                if not np.isfinite(f):
                    continue
                actual = Gflat[hist_target]
                ew0 = ew_abs("pv", j, np.array([hist_target]))[0]
                if actual > 50 or f > 50:
                    efc.append(f - actual); eew.append(ew0 - actual)
                if len(efc) >= FUSER_LOOK:
                    break
            fcur = FC10[d, k, r]
            if len(efc) < 5:
                pv_hat[r] = 0.5 * fcur + 0.5 * pv_ew[r]
            else:
                efc = np.asarray(efc); eew = np.asarray(eew)
                bias = efc.mean(); vfc = max(efc.var(), 1.0); vew = max(eew.var(), 1.0)
                fcur -= bias
                pv_hat[r] = ((1 / vfc) * fcur + (1 / vew) * pv_ew[r]) / ((1 / vfc) + (1 / vew))
    return (load_hat - np.maximum(pv_hat, 0)) * DT


@lru_cache(None)
def residual_samples48(d: int, k: int, look: int = RESID_LOOK) -> np.ndarray:
    """每个相对时段取最近look个、在当前发布时刻前已揭晓的残差。"""
    release = d * T + STAGE_SLOT[k]
    samples = np.full((look, 2 * T), np.nan)
    for r in range(2 * T):
        vals = []
        for j in range(d - 1, 7, -1):
            target = j * T + STAGE_SLOT[k] + r
            if target >= release or target >= len(Gflat):
                continue
            vals.append((Lflat[target] - Gflat[target]) * DT - point_forecast48(j, k)[r])
            if len(vals) == look:
                break
        if vals:
            samples[:len(vals), r] = vals
    return samples


def rho48(d: int, k: int, alpha: float, look: int = RESID_LOOK) -> np.ndarray:
    """严格48小时全窗的经验分位数余量；今天、明天及跨日部分均不遗漏。"""
    s = residual_samples48(d, k, look)
    out = np.nanquantile(s, alpha, axis=0)
    return np.nan_to_num(out, nan=0.0)


def solve_stage48(d: int, k: int, target48: np.ndarray, S0: float,
                  qplan: np.ndarray | None = None) -> np.ndarray:
    """每个阶段严格优化未来48小时，只执行到当日24:00。"""
    H = 2 * T
    target48 = np.asarray(target48, float)
    if target48.shape != (H,):
        raise ValueError("target48必须恰为288个10分钟时段")
    t0 = STAGE_SLOT[k]; n_exec = T - t0
    abs_slots = d * T + t0 + np.arange(H)
    ph = price[abs_slots % T]
    nv = 4 * H + (n_exec if qplan is not None else 0)
    iq, ic, iu, iS = (np.arange(H) + j * H for j in range(4))
    cobj = np.zeros(nv)
    if qplan is None:
        cobj[iq] = ph
    else:
        cobj[iq[n_exec:]] = ph[n_exec:]
        iy = 4 * H + np.arange(n_exec); cobj[iy] = 1.0
    lb = np.zeros(nv); ub = np.full(nv, np.inf)
    lb[iS] = SMIN; ub[iS] = SMAX
    if qplan is not None:
        lb[iy] = -np.inf
    rows, cols, vals, rhs = [], [], [], []; rr = 0; tt = np.arange(H)
    rows += [rr + tt, rr + tt, rr + tt]; cols += [iq, iu, ic]
    vals += [-np.ones(H), -np.ones(H), np.ones(H)]; rhs.append(-target48); rr += H
    rows += [rr + tt, rr + tt]; cols += [ic, iu]
    vals += [np.ones(H), np.ones(H)]; rhs.append(np.full(H, R_MAX)); rr += H
    if qplan is not None:
        pd0 = price[t0:]
        for coef in (DN, UP):
            r0 = rr + np.arange(n_exec)
            rows += [r0, r0]; cols += [iq[:n_exec], iy]
            vals += [coef * pd0, -np.ones(n_exec)]
            rhs.append(coef * pd0 * qplan[t0:]); rr += n_exec
    A_ub = csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(rr, nv))
    er = [tt, tt[1:], tt, tt]; ec = [iS, iS[:-1], ic, iu]
    ev = [np.ones(H), -np.ones(H - 1), -ETA * np.ones(H), np.ones(H) / ETA]
    A_eq = csr_matrix((np.concatenate(ev), (np.concatenate(er), np.concatenate(ec))), shape=(H, nv))
    b_eq = np.zeros(H); b_eq[0] = S0
    res = linprog(cobj, A_ub=A_ub, b_ub=np.concatenate(rhs), A_eq=A_eq, b_eq=b_eq,
                  bounds=np.c_[lb, ub], method="highs")
    if not res.success:
        raise RuntimeError(f"{dates[min(d, ND-1)].date()} 阶段{k} LP失败：{res.message}")
    return res.x[iq[:n_exec]]


def settle(q: np.ndarray, net_act: np.ndarray, S0: float):
    n = len(q); c = np.zeros(n); u = np.zeros(n); e = np.zeros(n); w = np.zeros(n); S = np.zeros(n); s = float(S0)
    for t in range(n):
        gap = net_act[t] - q[t]
        if gap > 0:
            u[t] = min(gap, R_MAX, (s - SMIN) * ETA); e[t] = gap - u[t]; s -= u[t] / ETA
        else:
            c[t] = min(-gap, R_MAX, (SMAX - s) / ETA); w[t] = -gap - c[t]; s += ETA * c[t]
        S[t] = s
    return c, u, e, w, S


def state_at(q: np.ndarray, net_act: np.ndarray, S0: float, t0: int) -> float:
    if t0 == 0:
        return S0
    return float(settle(q[:t0], net_act[:t0], S0)[4][-1])


def simulate(stages=(1, 2, 3), A0=0.7, ALO=0.7, AHI=0.9,
             S_init=6000.0, days=None, use_attachment=True):
    days = list(range(START, ND) if days is None else days)
    if not days or days != list(range(days[0], days[-1] + 1)):
        raise ValueError("days必须为非空连续日期范围")
    rec = {k: [] for k in ["qplan", "qadj", "c", "u", "e", "w", "S", "S0"]}
    s = float(S_init)
    for d in days:
        q = np.zeros(T)
        pred0 = point_forecast48(d, 0, use_attachment)
        target0 = pred0 + rho48(d, 0, A0)
        q[:] = solve_stage48(d, 0, target0, s)
        qplan = q.copy(); plan_target_day = target0[:T].copy()
        for k in stages:
            t0 = STAGE_SLOT[k]; n_exec = T - t0
            pred = point_forecast48(d, k, use_attachment)
            lo = pred + rho48(d, k, ALO)
            hi = pred + rho48(d, k, AHI)
            # 固定比较0:00原始方案所依据的净负荷供电目标；全部在带内则不调整。
            base = plan_target_day[t0:]
            inside_band = (base >= lo[:n_exec]) & (base <= hi[:n_exec])
            if np.all(inside_band):
                continue
            target48 = pred + rho48(d, k, A0)  # 明天及整个48小时同样带安全余量
            target48[:n_exec] = np.clip(base, lo[:n_exec], hi[:n_exec])
            s_now = state_at(q, (L[d] - Gv[d]) * DT, s, t0)
            q[t0:] = solve_stage48(d, k, target48, s_now, qplan)
        c, u, e, w, S = settle(q, (L[d] - Gv[d]) * DT, s)
        for key, value in zip(["qplan", "qadj", "c", "u", "e", "w", "S"], [qplan, q, c, u, e, w, S]):
            rec[key].append(value)
        rec["S0"].append(s); s = float(S[-1])
    return {k: np.asarray(v) for k, v in rec.items()}


def cost(rec: dict[str, np.ndarray]) -> dict[str, float]:
    P = price[None, :]; qp, qa, e = rec["qplan"], rec["qadj"], rec["e"]
    plan = np.sum(qp * P); up = np.sum(UP * P * np.maximum(qa - qp, 0))
    dn = np.sum(DN * P * np.maximum(qp - qa, 0)); emg = np.sum(PEN * P * e)
    return {"计划购电费/万元": plan / 1e4, "调增费/万元": up / 1e4,
            "调减退费/万元": -dn / 1e4, "紧急购电费/万元": emg / 1e4,
            "总费用/万元": (plan + up - dn + emg) / 1e4,
            "紧急购电量/万kWh": e.sum() / 1e4,
            "发生紧急购电天数": int(np.sum(e.sum(axis=1) > 1e-6))}


def select_parameters_january(a0_values=(0.6, 0.7, 0.8, 0.9),
                              bands=((0.5, 0.99), (0.6, 0.95), (0.7, 0.9), (0.75, 0.85))):
    rows = []
    for a0 in a0_values:
        for lo, hi in bands:
            rec = simulate(A0=a0, ALO=lo, AHI=hi, days=SELECT_DAYS)
            rows.append({"A0": a0, "ALO": lo, "AHI": hi, **cost(rec)})
    table = pd.DataFrame(rows).sort_values(["总费用/万元", "A0", "ALO"]).reset_index(drop=True)
    best = table.iloc[0]
    return table, {"A0": float(best.A0), "ALO": float(best.ALO), "AHI": float(best.AHI)}


# ---------- Q2 exact baseline: copied specification from final Q2 ----------
def solve_plan_lp(load_energy, pv_energy, price48, s0):
    h = 2 * T; nv = 6 * h
    eu, es, qu, qs, v, soc = [np.arange(h) + k * h for k in range(6)]
    cobj = np.zeros(nv); cobj[qu] = price48; cobj[qs] = price48
    bounds = [(0, None)] * (5 * h) + [(SMIN, SMAX)] * h
    aub = lil_matrix((2 * h, nv)); bub = np.r_[pv_energy, np.full(h, R_MAX)]
    for t in range(h):
        aub[t, eu[t]] = 1; aub[t, es[t]] = 1
        aub[h + t, es[t]] = 1; aub[h + t, qs[t]] = 1; aub[h + t, v[t]] = 1
    aeq = lil_matrix((2 * h, nv)); beq = np.r_[load_energy, s0, np.zeros(h - 1)]
    for t in range(h):
        aeq[t, eu[t]] = 1; aeq[t, qu[t]] = 1; aeq[t, v[t]] = 1
        r = h + t; aeq[r, soc[t]] = 1; aeq[r, es[t]] = -ETA; aeq[r, qs[t]] = -ETA; aeq[r, v[t]] = 1 / ETA
        if t > 0: aeq[r, soc[t - 1]] = -1
    res = linprog(cobj, A_ub=aub.tocsr(), b_ub=bub, A_eq=aeq.tocsr(), b_eq=beq,
                  bounds=bounds, method="highs")
    if not res.success: raise RuntimeError(res.message)
    return res.x[qu][:T] + res.x[qs][:T]


def simulate_q2_baseline(alpha=0.8, look=14, S_init=6000.0):
    hist = []
    for d in range(10, START):
        pred = (ew_load_day(d, d) - ew_pv_day(d, d)) * DT
        hist.append((L[d] - Gv[d]) * DT - pred)
    qrows, erows, s = [], [], float(S_init)
    price48 = np.r_[price, price]
    for d in range(START, ND):
        rho = np.quantile(np.asarray(hist[-look:]), alpha, axis=0)
        l48 = np.r_[ew_load_day(d, d), ew_load_day(d, d + 1)] * DT + np.r_[rho, rho]
        p48 = np.r_[ew_pv_day(d, d), ew_pv_day(d, d + 1)] * DT
        q = solve_plan_lp(l48, p48, price48, s)
        _, _, e, _, S = settle(q, (L[d] - Gv[d]) * DT, s); s = float(S[-1])
        pred = (ew_load_day(d, d) - ew_pv_day(d, d)) * DT
        hist.append((L[d] - Gv[d]) * DT - pred); hist = hist[-60:]
        qrows.append(q); erows.append(e)
    rec = {"qplan": np.asarray(qrows), "qadj": np.asarray(qrows), "e": np.asarray(erows)}
    return rec, cost(rec)

# ===== 参数选择（原 Notebook 单元 7）=====

selection_table, PARAMS = select_parameters_january()
selection_evidence = selection_table.assign(
    **{"不调整带": selection_table.apply(lambda r: f"[{r.ALO:.2f},{r.AHI:.2f}]", axis=1),
       "调整净费用/万元": selection_table["调增费/万元"] + selection_table["调减退费/万元"]}
)[["A0", "不调整带", "计划购电费/万元", "调整净费用/万元", "紧急购电费/万元", "总费用/万元"]]
print("一月联合选择证据（按总费用排序，前5项）：")
display(selection_evidence.head(5).style.format({
    "A0":"{:.1f}", "计划购电费/万元":"{:.3f}", "调整净费用/万元":"{:.3f}",
    "紧急购电费/万元":"{:.3f}", "总费用/万元":"{:.3f}"}))
print("冻结参数：", PARAMS)
print(f"第一、二名费用差：{selection_table.iloc[1]['总费用/万元']-selection_table.iloc[0]['总费用/万元']:.3f} 万元")
assert set(SELECT_DAYS) == set(range(10, START))
assert selection_table.shape[0] == 16

# ===== 主仿真与费用汇总（原 Notebook 单元 9）=====

import time
run_start = time.time()
Q2_REC, Q2_COST = simulate_q2_baseline()
Q3_NO = simulate(stages=(), **PARAMS)
FIN = simulate(stages=(1, 2, 3), **PARAMS)
Q3_NO_COST, Q3_COST = cost(Q3_NO), cost(FIN)
summary = pd.DataFrame([Q2_COST, Q3_NO_COST, Q3_COST],
                       index=["问题2最终方案（同口径重算）", "问题3仅0:00计划", "问题3四阶段方案"])
display(summary)
q2 = Q2_COST["总费用/万元"]; q3 = Q3_COST["总费用/万元"]; no = Q3_NO_COST["总费用/万元"]
print(f"问题3相对问题2：节省 {q2-q3:.4f} 万元，下降 {(q2-q3)/q2:.3%}")
print(f"三次日内调整相对仅0:00计划：节省 {no-q3:.4f} 万元，下降 {(no-q3)/no:.3%}")
print(f"运行用时：{time.time()-run_start:.1f}秒")
```


## 第四问：波动电价耦合预测与多阶段优化

来源：`第四问预测+优化/q4_pipeline.py（第 1–440 行）`

包含官方数据读取、净负荷预测、电价耦合修正与参数选择、偏相关分析、日前/阶段优化、结算、费用口径、完整多阶段引擎与消融计算。导出和绘图包装未纳入。

```python
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import json
import shutil
import time

import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.sparse import csr_matrix, lil_matrix
from scipy.stats import pearsonr, spearmanr
from sklearn.linear_model import Ridge
from openpyxl import load_workbook

T = 144
DT = 1 / 6
START = 31
SELECT_DAYS = range(13, 31)  # 1月14—31日
ISSUE = (0, 6, 12, 18)
STAGE_SLOT = (0, 36, 72, 108)
ETA, R_MAX, SMIN, SMAX = 0.9, 5000 / 6, 1200.0, 10800.0
PEN, UP, DN = 5.0, 1.5, 0.5
EW_N, EW_DECAY, RESID_LOOK, FUSER_LOOK = 8, 0.6, 14, 14
DAY0 = pd.Timestamp("2025-01-01")
PRICE_GAMMAS = (0.0, 0.25, 0.5, 0.75, 1.0)


@dataclass
class DataBundle:
    dates: pd.DatetimeIndex
    load: np.ndarray
    pv: np.ndarray
    price: np.ndarray
    forecast_hourly: np.ndarray


def load_official_data(base: str | Path) -> DataBundle:
    base = Path(base)
    ld = pd.read_excel(base / "附件2.xlsx", sheet_name="小区负载")
    dates = pd.DatetimeIndex(pd.to_datetime(ld.iloc[:, 0]))
    load = ld.iloc[:, 1:].to_numpy(float)
    pv = pd.read_excel(base / "附件2.xlsx", sheet_name="光伏发电实际功率").iloc[:, 1:].to_numpy(float)
    price = pd.read_excel(base / "附件4.xlsx").iloc[:, 1:].to_numpy(float)
    f = pd.read_excel(base / "附件3.xlsx")
    f["日期"] = pd.to_datetime(f["日期"].ffill())
    f["h0"] = f["预报时刻"].astype(str).str.split(":").str[0].astype(int)
    fc = np.full((len(dates), 4, 25), np.nan)
    for _, row in f.iterrows():
        d = int((row["日期"] - DAY0).days)
        if 0 <= d < len(dates):
            k = ISSUE.index(int(row["h0"]))
            for h in range(1, 25):
                fc[d, k, h] = float(row[f"预报{h}小时"])
    if load.shape != (365, T) or pv.shape != load.shape or price.shape != load.shape:
        raise ValueError(f"官方附件维度异常：L={load.shape}, G={pv.shape}, C={price.shape}")
    if not np.isfinite(load).all() or not np.isfinite(pv).all() or not np.isfinite(price).all():
        raise ValueError("附件2或附件4存在非数值/缺失值")
    return DataBundle(dates, load, pv, price, fc)


def low_load_day(date) -> bool:
    return pd.Timestamp(date).dayofweek in (4, 5)


def _weights(n: int, decay: float = EW_DECAY) -> np.ndarray:
    w = decay ** np.arange(n)
    return w / w.sum()


def ew_day(y: np.ndarray, dates, cutoff: int, target_day: int, kind: str) -> np.ndarray:
    dates = pd.DatetimeIndex(dates)
    target_date = dates[target_day] if target_day < len(dates) else dates[-1] + pd.Timedelta(days=target_day-len(dates)+1)
    if kind == "load":
        typ = low_load_day(target_date)
        idx = [j for j in range(cutoff-1, -1, -1) if low_load_day(dates[j]) == typ][:EW_N]
    elif kind == "pv":
        idx = list(range(cutoff-1, max(-1, cutoff-EW_N-1), -1))
    else:
        raise ValueError(kind)
    pred = np.sum(_weights(len(idx))[:, None] * y[idx], axis=0)
    pred = np.maximum(pred, 0.0)
    if kind == "pv":
        pred[np.max(y[:cutoff], axis=0) <= 0] = 0.0
    return pred


def ew_net48(data: DataBundle, d: int) -> np.ndarray:
    n1 = (ew_day(data.load, data.dates, d, d, "load") - ew_day(data.pv, data.dates, d, d, "pv")) * DT
    n2 = (ew_day(data.load, data.dates, d, d+1, "load") - ew_day(data.pv, data.dates, d, d+1, "pv")) * DT
    return np.r_[n1, n2]


def _default_historical_net_hat(net: np.ndarray, day: int) -> np.ndarray:
    """仅供通用接口/测试使用；正式流水线传入Q2/Q3预测器。"""
    return np.r_[net[day-1], net[day-1]]


def _fit_price_correction(net, price, cutoff_day, start_slot, forecast_provider,
                          max_history_days=42):
    """用同类历史预测误差拟合 StandardScaler + Ridge(alpha=1)。"""
    slots=net.shape[1]; cutoff_abs=cutoff_day*slots+start_slot
    nf,pf=net.ravel(),price.ravel(); xs=[]; ys=[]
    for j in range(max(7,cutoff_day-max_history_days),cutoff_day):
        pred_j=np.asarray(forecast_provider(j),float)
        if pred_j.shape!=(2*slots,): raise ValueError("历史净负荷预测必须为严格48小时")
        target=j*slots+start_slot+np.arange(2*slots)
        valid=(target<cutoff_abs)&(target<len(nf)); lag=target[valid]-7*slots
        xs.append(pred_j[valid]-nf[lag]); ys.append(pf[target[valid]]-pf[lag])
    x=np.concatenate(xs)[:,None]; y=np.concatenate(ys)
    mean=x.mean(axis=0); scale=x.std(axis=0); scale[scale<1e-12]=1.0
    model=Ridge(alpha=1.0).fit((x-mean)/scale,y)
    return model,mean,scale,len(y)


def coupled_price_forecast(net: np.ndarray, price: np.ndarray, dates,
                           cutoff_day: int, net_hat48: np.ndarray,
                           gamma: float = 1.0, max_history_days: int = 42,
                           start_slot: int = 0, forecast_provider=None) -> tuple[np.ndarray, dict]:
    """单向耦合：7日前价格基线 + gamma×Ridge(预测净负荷变化)。"""
    net=np.asarray(net,float); price=np.asarray(price,float); slots=net.shape[1]
    net_hat48=np.asarray(net_hat48,float)
    if net_hat48.shape!=(2*slots,): raise ValueError("价格预测必须接收严格48小时净负荷")
    provider=forecast_provider or (lambda j:_default_historical_net_hat(net,j))
    model,mean,scale,n_train=_fit_price_correction(net,price,cutoff_day,start_slot,provider,max_history_days)
    target=cutoff_day*slots+start_slot+np.arange(2*slots); lag=target-7*slots
    if lag.min()<0 or lag.max()>=cutoff_day*slots: raise ValueError("7日基线超出决策时刻前的合法历史")
    xcur=(net_hat48-net.ravel()[lag])[:,None]
    pred=np.maximum(price.ravel()[lag]+float(gamma)*model.predict((xcur-mean)/scale),1e-6)
    dates=pd.DatetimeIndex(dates)
    meta={"gamma":float(gamma),"ridge_alpha":1.0,"n_train":int(n_train),
          "coef_scaled":float(model.coef_[0]),"intercept":float(model.intercept_),
          "history_start":str(dates[max(7,cutoff_day-max_history_days)].date()),
          "history_end":str(dates[cutoff_day-1].date())}
    return pred,meta


def select_price_gamma(net: np.ndarray, price: np.ndarray, dates, forecast_provider,
                       candidates=PRICE_GAMMAS) -> tuple[pd.DataFrame,float]:
    rows=[]
    for gamma in candidates:
        err=[]
        for d in SELECT_DAYS:
            pred,_=coupled_price_forecast(net,price,dates,d,forecast_provider(d),gamma=gamma,
                                          forecast_provider=forecast_provider)
            err.extend(pred[:net.shape[1]]-price[d])
        rows.append({"gamma":float(gamma),"一月14—31日MAE":float(np.mean(np.abs(err)))})
    table=pd.DataFrame(rows)
    best=float(table.loc[table["一月14—31日MAE"].idxmin(),"gamma"])
    return table,best


def price_metrics(data: DataBundle, gamma: float) -> pd.DataFrame:
    net=(data.load-data.pv)*DT; provider=lambda d:ew_net48(data,d); rows=[]
    for label,days in (("一月14—31日",range(13,31)),("2—12月",range(31,365))):
        lag,cp=[],[]
        for d in days:
            pred,_=coupled_price_forecast(net,data.price,data.dates,d,provider(d),gamma=gamma,
                                          forecast_provider=provider)
            lag.extend(data.price[d-7]-data.price[d]); cp.extend(pred[:T]-data.price[d])
        lag,cp=np.asarray(lag),np.asarray(cp)
        rows.append({"评价期":label,"lag7_MAE":np.abs(lag).mean(),"耦合预测_MAE":np.abs(cp).mean(),
                     "耦合预测_RMSE":np.sqrt(np.mean(cp**2))})
    return pd.DataFrame(rows)


def _controls(dates, slots: int) -> np.ndarray:
    dates = pd.DatetimeIndex(dates)
    n = len(dates)
    slot = np.tile(np.arange(slots), n)
    slot_dm = np.eye(slots, dtype=float)[slot][:, 1:]
    dow = np.repeat(dates.dayofweek.to_numpy(), slots)
    dow_dm = np.eye(7, dtype=float)[dow][:, 1:]
    doy = np.repeat(dates.dayofyear.to_numpy(), slots)
    trend = np.repeat(np.arange(n, dtype=float), slots) / max(n-1, 1)
    return np.column_stack([np.ones(n*slots), slot_dm, dow_dm,
                            np.sin(2*np.pi*doy/365), np.cos(2*np.pi*doy/365), trend])


def _residualize(y: np.ndarray, x: np.ndarray) -> np.ndarray:
    coef, *_ = np.linalg.lstsq(x, y.ravel(), rcond=None)
    return (y.ravel() - x @ coef).reshape(y.shape)


def partial_price_netload_dependence(net: np.ndarray, price: np.ndarray, dates,
                                     bootstrap: int = 400, seed: int = 42) -> dict:
    net, price = np.asarray(net, float), np.asarray(price, float)
    x = _controls(dates, net.shape[1])
    rn, rp = _residualize(net, x), _residualize(price, x)
    raw_p = pearsonr(net.ravel(), price.ravel()).statistic
    raw_s = spearmanr(net.ravel(), price.ravel()).statistic
    pp = pearsonr(rn.ravel(), rp.ravel()).statistic
    ps = spearmanr(rn.ravel(), rp.ravel()).statistic
    rng = np.random.default_rng(seed)
    vals = np.empty(bootstrap)
    for b in range(bootstrap):
        idx = rng.integers(0, len(net), len(net))
        vals[b] = pearsonr(rn[idx].ravel(), rp[idx].ravel()).statistic
    lo, hi = np.quantile(vals, [0.025, 0.975])
    return {"raw_pearson": float(raw_p), "raw_spearman": float(raw_s),
            "partial_pearson": float(pp), "partial_spearman": float(ps),
            "ci_low": float(lo), "ci_high": float(hi), "bootstrap_days": int(bootstrap)}


def solve_q2_plan48(load_energy, pv_energy, price_hat48, s0,
                    periods_per_day=T, eta=ETA, rmax=R_MAX, smin=SMIN, smax=SMAX):
    """问题二原LP口径：显式区分小区负荷与光伏，只替换为预测电价。"""
    load_energy=np.asarray(load_energy,float); pv_energy=np.asarray(pv_energy,float); price_hat48=np.asarray(price_hat48,float)
    h=2*periods_per_day
    if load_energy.shape!=(h,) or pv_energy.shape!=(h,) or price_hat48.shape!=(h,):
        raise ValueError("问题4-2输入必须恰为48小时")
    nv=6*h; eu,es,qu,qs,v,soc=[np.arange(h)+k*h for k in range(6)]
    c=np.zeros(nv); c[qu]=price_hat48; c[qs]=price_hat48
    bounds=[(0,None)]*(5*h)+[(smin,smax)]*h
    aub=lil_matrix((2*h,nv)); bub=np.r_[pv_energy,np.full(h,rmax)]
    for t in range(h):
        aub[t,eu[t]]=1; aub[t,es[t]]=1
        aub[h+t,es[t]]=1; aub[h+t,qs[t]]=1; aub[h+t,v[t]]=1
    aeq=lil_matrix((2*h,nv)); beq=np.r_[load_energy,s0,np.zeros(h-1)]
    for t in range(h):
        aeq[t,eu[t]]=1; aeq[t,qu[t]]=1; aeq[t,v[t]]=1
        r=h+t; aeq[r,soc[t]]=1; aeq[r,es[t]]=-eta; aeq[r,qs[t]]=-eta; aeq[r,v[t]]=1/eta
        if t>0: aeq[r,soc[t-1]]=-1
    res=linprog(c,A_ub=aub.tocsr(),b_ub=bub,A_eq=aeq.tocsr(),b_eq=beq,bounds=bounds,method="highs")
    if not res.success:
        return {"success":False,"status":int(res.status),"message":res.message,
                "q_exec":np.full(periods_per_day,np.nan),"soc48":np.full(h,np.nan)}
    return {"success":True,"status":int(res.status),"message":res.message,
            "q_exec":res.x[qu][:periods_per_day]+res.x[qs][:periods_per_day],
            "soc48":res.x[soc],"objective_predicted":float(res.fun)}


def solve_stage48(target48: np.ndarray, price_hat48: np.ndarray, s0: float,
                  periods_per_day: int = T, eta: float = ETA, rmax: float = R_MAX,
                  smin: float = SMIN, smax: float = SMAX,
                  qplan: np.ndarray | None = None, exec_slots: int | None = None) -> dict:
    """预测电价目标下的严格48小时LP；返回当前可执行部分。"""
    target48 = np.asarray(target48, float); price_hat48 = np.asarray(price_hat48, float)
    h = 2 * periods_per_day
    if target48.shape != (h,) or price_hat48.shape != (h,):
        raise ValueError("优化输入必须恰为48小时且目标与预测电价等长")
    n_exec = periods_per_day if exec_slots is None else int(exec_slots)
    nv = 4*h + (n_exec if qplan is not None else 0)
    iq, ic, iu, iS = (np.arange(h)+j*h for j in range(4))
    c = np.zeros(nv)
    if qplan is None:
        c[iq] = price_hat48
    else:
        qplan = np.asarray(qplan, float)
        if qplan.shape != (n_exec,):
            raise ValueError("qplan长度必须等于可执行时段数")
        c[iq[n_exec:]] = price_hat48[n_exec:]
        iy = 4*h + np.arange(n_exec); c[iy] = 1.0
    lb = np.zeros(nv); ub = np.full(nv, np.inf)
    lb[iS] = smin; ub[iS] = smax
    if qplan is not None: lb[iy] = -np.inf
    rows=[]; cols=[]; vals=[]; rhs=[]; rr=0; tt=np.arange(h)
    rows += [rr+tt, rr+tt, rr+tt]; cols += [iq, iu, ic]
    vals += [-np.ones(h), -np.ones(h), np.ones(h)]; rhs.append(-target48); rr += h
    rows += [rr+tt, rr+tt]; cols += [ic, iu]
    vals += [np.ones(h), np.ones(h)]; rhs.append(np.full(h, rmax)); rr += h
    if qplan is not None:
        p0 = price_hat48[:n_exec]
        for coef in (DN, UP):
            r0 = rr + np.arange(n_exec)
            rows += [r0, r0]; cols += [iq[:n_exec], iy]
            vals += [coef*p0, -np.ones(n_exec)]
            rhs.append(coef*p0*qplan); rr += n_exec
    aub = csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(rr,nv))
    er=[tt,tt[1:],tt,tt]; ec=[iS,iS[:-1],ic,iu]
    ev=[np.ones(h),-np.ones(h-1),-eta*np.ones(h),np.ones(h)/eta]
    aeq=csr_matrix((np.concatenate(ev),(np.concatenate(er),np.concatenate(ec))),shape=(h,nv))
    beq=np.zeros(h); beq[0]=s0
    res=linprog(c,A_ub=aub,b_ub=np.concatenate(rhs),A_eq=aeq,b_eq=beq,bounds=np.c_[lb,ub],method="highs")
    if not res.success:
        return {"success":False,"status":int(res.status),"message":res.message,
                "q_exec":np.full(n_exec,np.nan),"soc48":np.full(h,np.nan)}
    return {"success":True,"status":int(res.status),"message":res.message,
            "q_exec":res.x[iq[:n_exec]],"soc48":res.x[iS],"objective_predicted":float(res.fun)}


def settle_day(q: np.ndarray, net_actual: np.ndarray, s0: float,
               eta: float = ETA, rmax: float = R_MAX,
               smin: float = SMIN, smax: float = SMAX) -> dict:
    q=np.asarray(q,float); net=np.asarray(net_actual,float); n=len(q)
    charge=np.zeros(n); discharge=np.zeros(n); emergency=np.zeros(n); curtail=np.zeros(n); soc=np.zeros(n)
    s=float(s0)
    for t in range(n):
        gap=net[t]-q[t]
        if gap>0:
            discharge[t]=min(gap,rmax,(s-smin)*eta); emergency[t]=gap-discharge[t]; s-=discharge[t]/eta
        else:
            charge[t]=min(-gap,rmax,(smax-s)/eta); curtail[t]=-gap-charge[t]; s+=eta*charge[t]
        soc[t]=s
    return {"s0":float(s0),"charge":charge,"discharge":discharge,"emergency":emergency,"curtail":curtail,"soc":soc}


def state_at(q, net, s0, t0):
    return float(s0) if t0 == 0 else float(settle_day(q[:t0], net[:t0], s0)["soc"][-1])


def cost_q2(q, emergency, true_price) -> dict:
    plan=float(np.sum(np.asarray(q)*true_price)); emg=float(np.sum(PEN*np.asarray(emergency)*true_price))
    return {"计划购电费_元":plan,"紧急购电费_元":emg,"总费用_元":plan+emg}


def cost_q3(qplan, qadj, emergency, true_price) -> dict:
    qp,qa,e,p=map(np.asarray,(qplan,qadj,emergency,true_price))
    plan=float(np.sum(qp*p)); up=float(np.sum(UP*p*np.maximum(qa-qp,0)))
    dn=float(np.sum(DN*p*np.maximum(qp-qa,0))); emg=float(np.sum(PEN*p*e))
    return {"计划购电费_元":plan,"调增费_元":up,"调减退费_元":dn,
            "紧急购电费_元":emg,"总费用_元":plan+up-dn+emg}


class Q4Engine:
    """忠实承接问题二 EW/EWMA 与问题三卡尔曼四阶段口径，仅替换价格层。"""
    def __init__(self, data: DataBundle, price_gamma: float):
        self.data=data; self.gamma=float(price_gamma); self.net=(data.load-data.pv)*DT
        self.lflat=data.load.ravel(); self.gflat=data.pv.ravel(); self.nflat=self.net.ravel()
        self.fc10=np.full((len(data.dates),4,T),np.nan)
        for d in range(len(data.dates)):
            for k in range(4): self.fc10[d,k]=self.downscale(d,k)

    @lru_cache(None)
    def ew_load(self, cutoff, target): return ew_day(self.data.load,self.data.dates,cutoff,target,"load")
    @lru_cache(None)
    def ew_pv(self, cutoff, target): return ew_day(self.data.pv,self.data.dates,cutoff,target,"pv")

    def ew_abs(self, kind, cutoff, abs_slots):
        out=np.empty(len(abs_slots)); arr=self.data.load if kind=="load" else self.data.pv
        for td in np.unique(abs_slots//T):
            m=abs_slots//T==td; out[m]=ew_day(arr,self.data.dates,cutoff,int(td),kind)[abs_slots[m]%T]
        return out

    def downscale(self,d,k):
        release=d*T+STAGE_SLOT[k]; x=np.arange(release,release+T)
        anchors=release+6*np.arange(1,25)-1; vals=self.data.forecast_hourly[d,k,1:25]
        prev=self.gflat[release-1] if release>0 else 0.0
        return np.maximum(np.interp(x,np.r_[release-1,anchors],np.r_[prev,vals]),0)

    @lru_cache(None)
    def point48(self,d,k,use_attachment=True):
        release=d*T+STAGE_SLOT[k]; abs_slots=np.arange(release,release+2*T)
        lh=self.ew_abs("load",d,abs_slots); gew=self.ew_abs("pv",d,abs_slots); gh=gew.copy()
        if use_attachment:
            for r in range(T):
                efc=[]; eew=[]
                for j in range(d-1,max(7,d-FUSER_LOOK-3),-1):
                    ht=j*T+STAGE_SLOT[k]+r
                    if ht>=release or ht>=len(self.gflat): continue
                    f=self.fc10[j,k,r]; actual=self.gflat[ht]; ew0=self.ew_abs("pv",j,np.array([ht]))[0]
                    if actual>50 or f>50: efc.append(f-actual); eew.append(ew0-actual)
                    if len(efc)>=FUSER_LOOK: break
                fcur=self.fc10[d,k,r]
                if len(efc)<5: gh[r]=.5*fcur+.5*gew[r]
                else:
                    efc=np.asarray(efc); eew=np.asarray(eew); bias=efc.mean()
                    vfc=max(efc.var(),1.0); vew=max(eew.var(),1.0)
                    gh[r]=((fcur-bias)/vfc+gew[r]/vew)/(1/vfc+1/vew)
        return (lh-np.maximum(gh,0))*DT

    @lru_cache(None)
    def residual_samples48(self,d,k,look=RESID_LOOK):
        release=d*T+STAGE_SLOT[k]; samples=np.full((look,2*T),np.nan)
        for r in range(2*T):
            vals=[]
            for j in range(d-1,7,-1):
                target=j*T+STAGE_SLOT[k]+r
                if target>=release or target>=len(self.nflat): continue
                vals.append(self.nflat[target]-self.point48(j,k)[r])
                if len(vals)==look: break
            if vals: samples[:len(vals),r]=vals
        return samples

    def rho48(self,d,k,alpha):
        return np.nan_to_num(np.nanquantile(self.residual_samples48(d,k),alpha,axis=0),nan=0.0)

    def price48(self,d,k,net_hat,use_attachment=True):
        provider=lambda j:self.point48(j,k,use_attachment)
        return coupled_price_forecast(self.net,self.data.price,self.data.dates,d,net_hat,
                                      gamma=self.gamma,start_slot=STAGE_SLOT[k],
                                      forecast_provider=provider)[0]

    def simulate_q2(self, days=None, alpha=.8, s_init=6000.0):
        days=list(range(START,len(self.data.dates)) if days is None else days)
        hist=[]
        for d in range(10,days[0]): hist.append(self.net[d]-self.point48(d,0,False)[:T])
        rec={k:[] for k in ("qplan","qadj","charge","discharge","emergency","curtail","soc","s0","terminal_soc48")}; s=float(s_init); statuses=[]
        for d in days:
            load48=np.r_[self.ew_load(d,d),self.ew_load(d,d+1)]*DT
            pv48=np.r_[self.ew_pv(d,d),self.ew_pv(d,d+1)]*DT
            pred=load48-pv48
            rho=np.quantile(np.asarray(hist[-RESID_LOOK:]),alpha,axis=0)
            ph=self.price48(d,0,pred,False)
            sol=solve_q2_plan48(load48+np.r_[rho,rho],pv48,ph,s)
            if not sol["success"]: raise RuntimeError(f"Q4-2 {self.data.dates[d].date()} LP失败：{sol['message']}")
            q=sol["q_exec"]; st=settle_day(q,self.net[d],s)
            for key,val in (("qplan",q),("qadj",q),("charge",st["charge"]),("discharge",st["discharge"]),
                            ("emergency",st["emergency"]),("curtail",st["curtail"]),("soc",st["soc"])): rec[key].append(val)
            rec["s0"].append(s); rec["terminal_soc48"].append(float(sol["soc48"][-1])); s=float(st["soc"][-1]); statuses.append(sol["status"])
            hist.append(self.net[d]-pred[:T]); hist=hist[-60:]
        out={k:np.asarray(v) for k,v in rec.items()}; out["lp_status"]=np.asarray(statuses); out["days"]=np.asarray(days)
        return out

    def simulate_q3(self, days=None, a0=.6, alo=.7, ahi=.9, s_init=6000.0):
        days=list(range(START,len(self.data.dates)) if days is None else days)
        rec={k:[] for k in ("qplan","qadj","charge","discharge","emergency","curtail","soc","s0","terminal_soc48")}; statuses=[]; s=float(s_init)
        for d in days:
            pred0=self.point48(d,0); target0=pred0+self.rho48(d,0,a0); ph0=self.price48(d,0,pred0)
            sol=solve_stage48(target0,ph0,s)
            if not sol["success"]: raise RuntimeError(f"Q4-3 {self.data.dates[d].date()} 0:00 LP失败")
            q=sol["q_exec"]; qplan=q.copy(); base=target0[:T].copy(); terminal0=float(sol["soc48"][-1]); statuses.append(sol["status"])
            for k in (1,2,3):
                t0=STAGE_SLOT[k]; n=T-t0; pred=self.point48(d,k); lo=pred+self.rho48(d,k,alo); hi=pred+self.rho48(d,k,ahi)
                if np.all((base[t0:]>=lo[:n])&(base[t0:]<=hi[:n])): continue
                target=pred+self.rho48(d,k,a0); target[:n]=np.clip(base[t0:],lo[:n],hi[:n])
                ph=self.price48(d,k,pred); sn=state_at(q,self.net[d],s,t0)
                sol=solve_stage48(target,ph,sn,qplan=qplan[t0:],exec_slots=n)
                if not sol["success"]: raise RuntimeError(f"Q4-3 {self.data.dates[d].date()} {ISSUE[k]}:00 LP失败")
                q[t0:]=sol["q_exec"]; statuses.append(sol["status"])
            st=settle_day(q,self.net[d],s)
            for key,val in (("qplan",qplan),("qadj",q),("charge",st["charge"]),("discharge",st["discharge"]),
                            ("emergency",st["emergency"]),("curtail",st["curtail"]),("soc",st["soc"])): rec[key].append(val)
            rec["s0"].append(s); rec["terminal_soc48"].append(terminal0); s=float(st["soc"][-1])
        out={k:np.asarray(v) for k,v in rec.items()}; out["lp_status"]=np.asarray(statuses); out["days"]=np.asarray(days)
        return out


def ablation_table(total_costs: dict, selected_gamma: float) -> pd.DataFrame:
    """把同口径 gamma=0 与一月冻结 gamma 的平行结果整理为可审计表。"""
    rows=[]
    for scheme in ("问题4-2","问题4-3"):
        base=float(total_costs[(scheme,0.0)])
        for gamma,label in ((0.0,"lag7基线"),(float(selected_gamma),"净负荷耦合")):
            total=float(total_costs[(scheme,gamma)])
            rows.append({"方案":scheme,"gamma":gamma,"价格方案":label,"总费用_元":total,
                         "相对lag7节省_元":base-total})
    return pd.DataFrame(rows)
```


## 第四问补充：EW 电价方案对比

来源：`第四问预测+优化/q4_ew_compare.py（完整文件）`

包含 EW 历史价格曲线、净负荷耦合电价预测、EW 参数选择及与 7 日基线方案的费用对比，是第四问核心方案比较逻辑。

```python
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
```
