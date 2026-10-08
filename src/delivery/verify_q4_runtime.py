"""独立运行并核验问题4最终EW方案，不改写原项目文件。"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd

Q4 = Path(r"C:\Users\12055\Desktop\第四问预测+优化")
BASE = Path(r"C:\Users\12055\Desktop\2026 国赛")
ANSWER = Path(r"C:\Users\12055\Desktop\答案")
sys.path.insert(0, str(Q4))
import q4_pipeline as q4
from q4_ew_compare import EWPriceEngine, ew_coupled_price_forecast, ew_history_profile


def plan_matrix(path, sheet):
    return pd.read_excel(path, sheet_name=sheet).iloc[:, 1:145].to_numpy(float)


def main():
    data = q4.load_official_data(BASE)
    selected = pd.read_csv(Q4 / "EW一月选参.csv").iloc[0]
    engine = EWPriceEngine(data, n=int(selected["历史同类型日数N"]),
                           decay=float(selected["衰减系数lambda"]))
    # 未来扰动不影响当前预测
    d = 45
    net48 = engine.point48(d, 0, False)
    a, meta = ew_coupled_price_forecast(engine.net, data.price, data.dates, d, net48, n=engine.ew_n, decay=engine.ew_decay,
                                        forecast_provider=lambda j: engine.point48(j, 0, False))
    net2 = engine.net.copy(); price2 = data.price.copy()
    net2[d:] = 999999; price2[d:] = 999999
    b, meta2 = ew_coupled_price_forecast(net2, price2, data.dates, d, net48, n=engine.ew_n, decay=engine.ew_decay,
                                         forecast_provider=lambda j: engine.point48(j, 0, False))

    rec2 = engine.simulate_q2(); rec3 = engine.simulate_q3()
    c2 = q4.cost_q2(rec2["qplan"], rec2["emergency"], data.price[q4.START:])
    c3 = q4.cost_q3(rec3["qplan"], rec3["qadj"], rec3["emergency"], data.price[q4.START:])
    x42 = plan_matrix(ANSWER / "result4-2.xlsx", "计划购电量")
    x43p = plan_matrix(ANSWER / "result4-3.xlsx", "计划购电量")
    x43a = plan_matrix(ANSWER / "result4-3.xlsx", "调整购电量")
    # 直接核验一个目标时段的EW只使用同负荷类型历史日。
    target = np.array([d * q4.T])
    prof, latest = ew_history_profile(engine.net, data.dates, target, d*q4.T,
                                      n=engine.ew_n, decay=engine.ew_decay)
    target_low = q4.low_load_day(data.dates[d]); selected_days=[]
    for j in range(d-1, -1, -1):
        if q4.low_load_day(data.dates[j]) == target_low:
            selected_days.append(j)
            if len(selected_days) == engine.ew_n: break
    weights=engine.ew_decay**np.arange(len(selected_days)); weights/=weights.sum()
    expected_profile=float(np.dot(weights, engine.net[selected_days,0]))
    checks = {
        "same_type_ew_exact": bool(np.isclose(prof[0], expected_profile)),
        "future_blind": bool(np.allclose(a, b) and meta == meta2),
        "q2_lp_all_success": bool(np.all(rec2["lp_status"] == 0)),
        "q3_lp_all_success": bool(np.all(rec3["lp_status"] == 0)),
        "q2_soc_bounds": bool(np.all((rec2["soc"] >= q4.SMIN-1e-6) & (rec2["soc"] <= q4.SMAX+1e-6))),
        "q3_soc_bounds": bool(np.all((rec3["soc"] >= q4.SMIN-1e-6) & (rec3["soc"] <= q4.SMAX+1e-6))),
        "q2_soc_continuity": bool(np.allclose(rec2["s0"][1:], rec2["soc"][:-1, -1])),
        "q3_soc_continuity": bool(np.allclose(rec3["s0"][1:], rec3["soc"][:-1, -1])),
        "q2_cost_identity": bool(np.isclose(c2["总费用_元"], c2["计划购电费_元"] + c2["紧急购电费_元"])),
        "q3_cost_identity": bool(np.isclose(c3["总费用_元"], c3["计划购电费_元"] + c3["调增费_元"] - c3["调减退费_元"] + c3["紧急购电费_元"])),
        "result42_matches_runtime": bool(np.allclose(x42, rec2["qplan"])),
        "result43_plan_matches_runtime": bool(np.allclose(x43p, rec3["qplan"])),
        "result43_adjusted_matches_runtime": bool(np.allclose(x43a, rec3["qadj"])),
    }
    result = {"checks": checks, "cost_q42": c2, "cost_q43": c3}
    if not all(checks.values()):
        raise AssertionError(result)
    (ANSWER / "问题4独立运行验证.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
