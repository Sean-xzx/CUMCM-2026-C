from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from q4_pipeline import (
    DT,
    T,
    coupled_price_forecast,
    select_price_gamma,
    partial_price_netload_dependence,
    solve_stage48,
    solve_q2_plan48,
    settle_day,
    cost_q2,
    cost_q3,
    ablation_table,
    validate_excel,
)


def synthetic_history(days=70, slots=8):
    rng = np.random.default_rng(7)
    net = 80 + np.arange(days)[:, None] * 0.2 + rng.normal(0, 2, (days, slots))
    price = 0.5 + 0.003 * net + rng.normal(0, 0.01, (days, slots))
    dates = pd.date_range("2025-01-01", periods=days)
    return dates, net, price


def test_price_forecast_is_strictly_history_only():
    dates, net, price = synthetic_history()
    d = 45
    net_hat = np.r_[net[d], net[d] + 1]
    a, meta = coupled_price_forecast(net, price, dates, d, net_hat, max_history_days=42)
    price[d:] = 999999.0
    net[d:] = -999999.0
    b, meta2 = coupled_price_forecast(net, price, dates, d, net_hat, max_history_days=42)
    np.testing.assert_allclose(a, b)
    assert a.shape == (2 * net.shape[1],)
    assert pd.Timestamp(meta["history_end"]) < dates[d]
    assert meta["ridge_alpha"] == 1.0
    assert meta["gamma"] == 1.0
    assert meta == meta2


def test_january_selection_only_compares_declared_shrinkage_grid():
    dates, net, price = synthetic_history(days=31, slots=8)
    table, gamma = select_price_gamma(net, price, dates, lambda d: np.r_[net[d], net[d]])
    assert table["gamma"].tolist() == [0.0, 0.25, 0.5, 0.75, 1.0]
    assert gamma in table["gamma"].tolist()
    assert set(table.columns) == {"gamma", "一月14—31日MAE"}


def test_future_netload_update_changes_price_forecast_not_history_fit():
    dates, net, price = synthetic_history()
    d = 45
    base = np.r_[net[d], net[d]]
    changed = base.copy(); changed[3] += 20
    p0, m0 = coupled_price_forecast(net, price, dates, d, base)
    p1, m1 = coupled_price_forecast(net, price, dates, d, changed)
    assert p1[3] != pytest.approx(p0[3])
    assert m0["coef_scaled"] == pytest.approx(m1["coef_scaled"])
    assert m0["intercept"] == pytest.approx(m1["intercept"])


def test_partial_dependence_returns_computed_ci_and_large_residual_relation():
    dates, net, price = synthetic_history(days=90, slots=12)
    out = partial_price_netload_dependence(net, price, dates, bootstrap=80, seed=1)
    required = {"raw_pearson", "raw_spearman", "partial_pearson", "partial_spearman", "ci_low", "ci_high"}
    assert required <= set(out)
    assert out["ci_low"] <= out["partial_pearson"] <= out["ci_high"]
    assert out["partial_pearson"] > 0.2


def test_stage_optimizer_requires_exact_48_hours_and_respects_soc():
    slots = 4
    target = np.full(2 * slots, 100.0)
    price_hat = np.linspace(0.4, 1.0, 2 * slots)
    sol = solve_stage48(target, price_hat, 6000.0, periods_per_day=slots,
                        rmax=100.0, smin=1200.0, smax=10800.0)
    assert sol["success"]
    assert len(sol["q_exec"]) == slots
    assert np.all((sol["soc48"] >= 1200 - 1e-7) & (sol["soc48"] <= 10800 + 1e-7))
    with pytest.raises(ValueError, match="48小时"):
        solve_stage48(target[:-1], price_hat, 6000.0, periods_per_day=slots)


def test_q2_solver_preserves_load_pv_split_and_48h_contract():
    slots=4
    load=np.full(2*slots,100.0); pv=np.array([20.,20.,0.,0.]*2); price=np.ones(2*slots)
    sol=solve_q2_plan48(load,pv,price,6000.0,periods_per_day=slots,rmax=100.0)
    assert sol["success"] and len(sol["q_exec"])==slots
    with pytest.raises(ValueError,match="48小时"):
        solve_q2_plan48(load[:-1],pv,price,6000.0,periods_per_day=slots)


def test_settlement_soc_continuity_and_cost_identities():
    q = np.full((2, 4), 100.0)
    net = np.array([[90., 110., 100., 95.], [105., 80., 120., 100.]])
    rec = settle_day(q[0], net[0], 6000.0, rmax=100.0)
    rec2 = settle_day(q[1], net[1], rec["soc"][-1], rmax=100.0)
    assert rec2["s0"] == pytest.approx(rec["soc"][-1])
    true_price = np.full_like(q, 0.8)
    e = np.vstack([rec["emergency"], rec2["emergency"]])
    c2 = cost_q2(q, e, true_price)
    assert c2["总费用_元"] == pytest.approx(c2["计划购电费_元"] + c2["紧急购电费_元"])
    qa = q + np.array([[0., 1., -1., 0.], [2., -2., 0., 0.]])
    c3 = cost_q3(q, qa, e, true_price)
    assert c3["总费用_元"] == pytest.approx(
        c3["计划购电费_元"] + c3["调增费_元"] - c3["调减退费_元"] + c3["紧急购电费_元"]
    )


def test_ablation_table_reports_parallel_lag7_and_coupled_savings():
    rows = {("问题4-2", 0.0): 120.0, ("问题4-2", 1.0): 110.0,
            ("问题4-3", 0.0): 100.0, ("问题4-3", 1.0): 97.0}
    tab = ablation_table(rows, selected_gamma=1.0)
    assert len(tab) == 4
    assert set(tab["价格方案"]) == {"lag7基线", "净负荷耦合"}
    assert tab.query("方案 == '问题4-2' and 价格方案 == '净负荷耦合'")["相对lag7节省_元"].iat[0] == pytest.approx(10.0)


def test_filled_workbooks_match_templates_and_have_no_blanks():
    template_dir = Path(r"C:\Users\12055\Desktop\2026 国赛\附件5")
    for stem in ("result4-2", "result4-3"):
        filled = ROOT / f"{stem}_filled.xlsx"
        if not filled.exists():
            pytest.skip("完整流水线尚未运行")
        report = validate_excel(template_dir / f"{stem}.xlsx", filled, stem)
        assert report["sheet_names_match"]
        assert report["dates_ok"]
        assert report["required_nonempty"]
