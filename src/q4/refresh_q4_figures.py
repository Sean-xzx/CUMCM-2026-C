"""用同类型EW方案的结果刷新问题四图表与费用明细，不重跑LP。

输入：EW方案结果/result4-2_filled.xlsx、result4-3_filled.xlsx、EW一月选参.csv
输出：图表/问题四_典型日电价预测.png|svg、图表/问题四_费用构成.png|svg、
      问题四_同类型EW费用明细.csv
"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd
import openpyxl

import q4_pipeline as q4
from q4_ew_compare import EWPriceEngine

Q4 = Path(r"C:\Users\12055\Desktop\第四问预测+优化")
BASE = Path(r"C:\Users\12055\Desktop\2026 国赛")
EWDIR = Q4 / "EW方案结果"


def plan_matrix(path, sheet):
    return pd.read_excel(path, sheet_name=sheet).iloc[:, 1:145].to_numpy(float)


def emergency_matrix(path, dates):
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb["紧急购电量"]
    out = np.zeros((len(dates), q4.T))
    days = {pd.Timestamp(d).normalize(): i for i, d in enumerate(dates)}
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[0] or not row[1] or row[2] is None:
            continue
        d = pd.Timestamp(row[0]).normalize()
        if d not in days:
            continue
        start = str(row[1]).split("-")[0]
        h, m = (int(x) for x in start.split(":"))
        out[days[d], (h * 60 + m) // 10] += float(row[2])
    return out


def main():
    data = q4.load_official_data(BASE)
    sel = pd.read_csv(Q4 / "EW一月选参.csv").iloc[0]
    engine = EWPriceEngine(data, n=int(sel["历史同类型日数N"]), decay=float(sel["衰减系数lambda"]))

    dates = data.dates[q4.START:]
    p42 = EWDIR / "result4-2_filled.xlsx"
    p43 = EWDIR / "result4-3_filled.xlsx"
    rec2 = {"qplan": plan_matrix(p42, "计划购电量"), "emergency": emergency_matrix(p42, dates)}
    rec3 = {"qplan": plan_matrix(p43, "计划购电量"), "qadj": plan_matrix(p43, "调整购电量"),
            "emergency": emergency_matrix(p43, dates)}

    c2 = q4.cost_q2(rec2["qplan"], rec2["emergency"], data.price[q4.START:])
    c3 = q4.cost_q3(rec3["qplan"], rec3["qadj"], rec3["emergency"], data.price[q4.START:])

    q4.generate_figures(data, engine, rec2, rec3, None, Q4)

    rows = []
    for scheme, c in (("问题4-2", c2), ("问题4-3", c3)):
        for k, v in c.items():
            rows.append({"方案": scheme, "费用项": k, "金额_元": float(v),
                         "金额_万元": float(v) / 1e4})
    detail = pd.DataFrame(rows)
    detail.to_csv(Q4 / "问题四_同类型EW费用明细.csv", index=False, encoding="utf-8-sig")

    summary = {"cost_q42": c2, "cost_q43": c3,
               "emergency_kwh_q42": float(rec2["emergency"].sum()),
               "emergency_kwh_q43": float(rec3["emergency"].sum())}
    (Q4 / "EW费用核验.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(detail.to_string(index=False))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
