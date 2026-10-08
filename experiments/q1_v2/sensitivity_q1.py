"""问题1 敏感性分析：初始储电量、充放电效率及效率口径。

决策变量记号与论文一致：e^u, e^s（光伏直供/充电），q^u, q^s（购电直供/充电），d（放电），S（储电量）。
"""
import json
from pathlib import Path

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix

from solve_q1 import load_attachment1


def solve_general(data, eta_c=0.9, eta_d=0.9, rate=5000 / 6, smin=1200.0, smax=10800.0,
                  s0=6000.0, s_end=None):
    """与 solve_q1.solve_dispatch 相同的线性规划，但充、放电效率可分别设置。
    s_end=None 表示 S_144 = S_0；s0=None 表示 S_0 作为决策变量（仍要求首尾相等）。"""
    n = len(data.price)
    free_s0 = s0 is None
    nv = 6 * n + (1 if free_s0 else 0)          # e^u e^s q^u q^s d S (+S_0)
    v = lambda b, t: b * n + t
    c = np.zeros(nv)
    c[2 * n:4 * n] = np.r_[data.price, data.price]

    A = lil_matrix((3 * n, nv)); b = np.zeros(3 * n)
    for t in range(n):
        A[t, v(0, t)] = A[t, v(2, t)] = A[t, v(4, t)] = -1; b[t] = -data.load_energy[t]
        A[n + t, v(0, t)] = A[n + t, v(1, t)] = 1; b[n + t] = data.pv_energy[t]
        A[2 * n + t, v(1, t)] = A[2 * n + t, v(3, t)] = A[2 * n + t, v(4, t)] = 1; b[2 * n + t] = rate

    E = lil_matrix((n + 1, nv)); f = np.zeros(n + 1)
    for t in range(n):
        E[t, v(5, t)] = 1
        if t == 0:
            if free_s0:
                E[t, 6 * n] = -1
            else:
                f[t] = s0
        else:
            E[t, v(5, t - 1)] = -1
        E[t, v(1, t)] = E[t, v(3, t)] = -eta_c
        E[t, v(4, t)] = 1 / eta_d
    E[n, v(5, n - 1)] = 1
    if free_s0:
        E[n, 6 * n] = -1
    else:
        f[n] = s0 if s_end is None else s_end

    bounds = [(0, None)] * (5 * n) + [(smin, smax)] * n + ([(smin, smax)] if free_s0 else [])
    r = linprog(c, A_ub=A.tocsr(), b_ub=b, A_eq=E.tocsr(), b_eq=f, bounds=bounds, method="highs")
    assert r.success, r.message
    x = r.x
    q = x[2 * n:3 * n] + x[3 * n:4 * n]
    return {"cost": float(r.fun), "q_total": float(q.sum()),
            "s0": float(x[6 * n]) if free_s0 else float(s0)}


if __name__ == "__main__":
    data = load_attachment1(Path(__file__).with_name("附件1.xlsx"))
    base = solve_general(data)
    print("基准（应为 35126.9486）:", round(base["cost"], 4))

    out = {"baseline": base}
    out["S0"] = [solve_general(data, s0=s) for s in (1200, 3000, 6000, 9000, 10800)]
    out["S0_free"] = solve_general(data, s0=None)
    out["eta_symmetric"] = [dict(eta=e, **solve_general(data, eta_c=e, eta_d=e))
                            for e in (0.85, 0.90, 0.95, 1.00)]
    rt = 0.9 ** 0.5
    out["eta_definition"] = [
        dict(name="充放各 90%（往返 81%，基准）", **solve_general(data, 0.9, 0.9)),
        dict(name="仅充电损耗 90%", **solve_general(data, 0.9, 1.0)),
        dict(name="往返 90%（充放各 √0.9）", **solve_general(data, rt, rt)),
    ]
    Path("问题1_敏感性分析.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(json.dumps(out, ensure_ascii=False, indent=2))
