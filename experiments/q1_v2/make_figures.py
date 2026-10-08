"""问题1 论文插图：基于建模手的 solve_q1.py 求解结果重新绘制。"""
import glob
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from matplotlib.ticker import MultipleLocator, FuncFormatter
import numpy as np

from solve_q1 import load_attachment1, solve_dispatch

# ---------------- 字体与全局样式 ----------------
HERE = Path(__file__).resolve().parent
# 额外字体（若存在）：Linux 下的 Times 替代字体与思源宋体 SC；Windows 自带 Times New Roman 与宋体
for p in glob.glob(str(HERE / "fonts" / "*.otf")) + glob.glob(
        "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyretermes-*.otf"):
    fm.fontManager.addfont(p)
_available = {f.name for f in fm.fontManager.ttflist}
_latin = next((f for f in ["Times New Roman", "TeX Gyre Termes"] if f in _available), "DejaVu Serif")
_cjk = next((f for f in ["Noto Serif CJK SC", "SimSun", "Songti SC", "STSong"] if f in _available), "SimHei")

plt.rcParams.update({
    "font.family": ["TeX Gyre Termes", "Times New Roman", "Noto Serif CJK SC", "SimSun"],  # Windows 下自动回退到 Times New Roman + 宋体
    "mathtext.fontset": "stix",
    "font.size": 9,
    "axes.labelsize": 9,
    "axes.titlesize": 9,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "legend.fontsize": 8,
    "axes.unicode_minus": False,
    "axes.linewidth": 0.7,
    "xtick.major.width": 0.7,
    "ytick.major.width": 0.7,
    "xtick.minor.width": 0.5,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.major.size": 3,
    "ytick.major.size": 3,
    "xtick.minor.size": 1.6,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "legend.frameon": False,
    "savefig.dpi": 600,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.03,
})

# 全文统一配色
C = {
    "load": "#222222",
    "pv": "#E3A21A",       # 光伏
    "pv_lt": "#F3D48A",
    "q": "#3B6FA0",     # 外网购电 q
    "q_lt": "#A9C3DD",
    "dis": "#2E9C83",      # 储能放电
    "price": "#7B4F9E",
    "soc": "#1F4E79",
    "base": "#9A9A9A",
    "red": "#C0392B",
}

WIDTH = 6.3  # 英寸，约 16 cm，A4 版心宽
OUT = Path(__file__).resolve().parent / "figs"
OUT.mkdir(exist_ok=True)

# ---------------- 数据 ----------------
D = load_attachment1(HERE / "附件1.xlsx")
S = solve_dispatch(D)
n = 144
dt = 1 / 6
edges = np.arange(n + 1) * dt          # 时段边界（小时）
centres = edges[:-1] + dt / 2
q = S.q_to_load + S.q_to_storage
charge = S.pv_to_storage + S.q_to_storage
# ---- 展示用的“光伏优先”归属（不改变任何决策量）----
# 同一时段内光伏与外购电在母线上混合，原 LP 解对“哪部分电来自光伏”的拆分不唯一，
# 这里统一按“光伏先供负载、再充储能；外购电补足其余”重新归属。
L_e, PV_e, d_e = D.load_energy, D.pv_energy, S.discharge
pv_load = np.minimum(PV_e, L_e - d_e)
pv_sto = np.minimum(PV_e - pv_load, charge)
q_sto = charge - pv_sto
q_load = L_e - d_e - pv_load
assert np.allclose(q_load + q_sto, q, atol=1e-6), "重新归属后购电量不一致"
assert np.all(q_load > -1e-6) and np.all(q_sto > -1e-6)
curtail = PV_e - pv_load - pv_sto
assert np.all(curtail < 1e-6)
soc = np.r_[6000.0, S.soc]             # 145 个时刻点
base_q = np.maximum(D.load_energy - D.pv_energy, 0.0)
cost_opt = D.price * q
cost_base = D.price * base_q


def step_xy(values):
    """把逐时段数值转成阶梯折线坐标。"""
    x = np.repeat(edges, 2)[1:-1]
    y = np.repeat(values, 2)
    return x, y


def fmt_time_axis(ax, labels=True):
    ax.set_xlim(0, 24)
    ax.xaxis.set_major_locator(MultipleLocator(4))
    ax.xaxis.set_minor_locator(MultipleLocator(1))
    if labels:
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v)}:00"))
    else:
        ax.tick_params(labelbottom=False)


def panel_label(ax, s, x=0.008, y=0.985):
    ax.text(x, y, s, transform=ax.transAxes, fontsize=9.5,
            va="top", ha="left")


def save(fig, name):
    fig.savefig(OUT / f"{name}.png")
    fig.savefig(OUT / f"{name}.pdf")
    plt.close(fig)


# ================= 图1 输入数据 =================
def fig_inputs():
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(WIDTH, 3.9), sharex=True,
                                 gridspec_kw={"height_ratios": [1.45, 1], "hspace": 0.12})
    L, P = D.load_power, D.pv_power
    a1.fill_between(centres, L, P, where=P > L, interpolate=True,
                    color=C["pv_lt"], alpha=0.75, lw=0)
    a1.plot(centres, L, color=C["load"], lw=1.2, label="小区负载")
    a1.plot(centres, P, color=C["pv"], lw=1.4, label="光伏发电功率")
    surplus = np.maximum(D.pv_energy - D.load_energy, 0).sum()
    a1.annotate(f"光伏盈余电量\n{surplus:,.0f} kWh", xy=(12.2, 6750), xytext=(15.9, 7050),
                fontsize=8, ha="left", va="center",
                arrowprops=dict(arrowstyle="-", lw=0.6, color="#555555"))
    a1.set_ylabel("功率 / kW")
    a1.set_ylim(0, 8800)
    a1.yaxis.set_major_locator(MultipleLocator(2000))
    a1.legend(loc="upper left", bbox_to_anchor=(0.045, 1.0), ncol=2, handlelength=1.8, columnspacing=1.4)
    a1.grid(axis="y", lw=0.4, alpha=0.35)
    panel_label(a1, "(a)")

    x, y = step_xy(D.price)
    a2.plot(x, y, color=C["price"], lw=1.1)
    a2.fill_between(x, y, 0, color=C["price"], alpha=0.08, lw=0)
    a2.set_ylabel("电价 / (元/kWh)")
    a2.set_ylim(0, 1.6)
    a2.yaxis.set_major_locator(MultipleLocator(0.4))
    a2.grid(axis="y", lw=0.4, alpha=0.35)
    fmt_time_axis(a2)
    a2.set_xlabel("时刻")
    panel_label(a2, "(b)")
    save(fig, "图1_典型日负载光伏与电价")


# ================= 图2 能量平衡 =================
def fig_balance():
    fig, ax = plt.subplots(figsize=(WIDTH, 3.3))
    pos = [(pv_load, C["pv"], "光伏直供负载"),
           (q_load, C["q"], "外网直供负载"),
           (S.discharge, C["dis"], "储能放电供负载")]
    neg = [(pv_sto, C["pv_lt"], "光伏充电"),
           (q_sto, C["q_lt"], "外网购电充电")]
    x = np.repeat(edges, 2)[1:-1]
    bottom = np.zeros(n)
    for v, c, lab in pos:
        ax.fill_between(x, np.repeat(bottom, 2), np.repeat(bottom + v, 2),
                        color=c, lw=0, label=lab)
        bottom += v
    bottom = np.zeros(n)
    for v, c, lab in neg:
        ax.fill_between(x, np.repeat(-bottom, 2), np.repeat(-(bottom + v), 2),
                        color=c, lw=0, label=lab)
        bottom += v
    xl, yl = step_xy(D.load_energy)
    ax.plot(xl, yl, color=C["load"], lw=0.9, label="小区负载")
    ax.axhline(0, color="#333333", lw=0.6)
    ax.set_ylabel("电量 / (kWh/10 min)")
    ax.set_ylim(-950, 1150)
    ax.yaxis.set_major_locator(MultipleLocator(250))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{abs(v):.0f}"))
    ax.grid(axis="y", lw=0.4, alpha=0.35)
    ax.text(0.2, 1090, "供电侧", fontsize=8, va="top", color="#444444")
    ax.text(2.4, -900, "储能充电侧", fontsize=8, va="bottom", color="#444444")
    fmt_time_axis(ax)
    ax.set_xlabel("时刻")
    h, l = ax.get_legend_handles_labels()
    order = [5, 0, 1, 2, 3, 4]
    ax.legend([h[i] for i in order], [l[i] for i in order], loc="upper center",
              bbox_to_anchor=(0.5, 1.13), ncol=6, handlelength=1.4,
              columnspacing=1.0, handletextpad=0.5)
    save(fig, "图2_最优调度逐时段能量平衡")


# ================= 图3 储电量轨迹与电价 =================
def phase_runs(min_energy=150.0, max_gap=3):
    """把逐时段充/放电状态合并为主要阶段：同向且间隔不超过 max_gap 个时段的合并，
    能量过小（< min_energy kWh）的零星片段不画阴影。"""
    state = np.where(charge > 1e-6, 1, np.where(S.discharge > 1e-6, -1, 0))
    runs = []
    for t in range(n):
        if state[t] == 0:
            continue
        e = charge[t] if state[t] > 0 else S.discharge[t]
        if runs and runs[-1][0] == state[t] and t - runs[-1][2] <= max_gap + 1:
            runs[-1][2] = t; runs[-1][3] += e
        else:
            runs.append([state[t], t, t, e])
    return [(s, a, b) for s, a, b, e in runs if e >= min_energy]


def fig_soc():
    fig, ax = plt.subplots(figsize=(WIDTH, 3.0))
    for s, a, b in phase_runs():
        ax.axvspan(edges[a], edges[b + 1], color=C["q"] if s > 0 else C["dis"],
                   alpha=0.12 if s > 0 else 0.16, lw=0)
    ax.axhline(10800, color=C["red"], lw=0.7, ls=(0, (4, 3)))
    ax.axhline(1200, color=C["red"], lw=0.7, ls=(0, (4, 3)))
    ax.text(2.3, 10800 + 160, "上限 10 800 kWh", fontsize=7.5, ha="left", va="bottom", color=C["red"])
    ax.text(2.3, 1200 - 160, "下限 1 200 kWh", fontsize=7.5, ha="left", va="top", color=C["red"])

    ax2 = ax.twinx()
    ax2.spines["right"].set_visible(True)
    xp, yp = step_xy(D.price)
    ax2.plot(xp, yp, color=C["price"], lw=0.75, alpha=0.75)
    ax2.set_ylim(0, 2.2)
    ax2.set_ylabel("电价 / (元/kWh)", color=C["price"])
    ax2.tick_params(axis="y", colors=C["price"])
    ax2.spines["right"].set_color(C["price"])
    ax2.yaxis.set_major_locator(MultipleLocator(0.4))

    ax.set_zorder(ax2.get_zorder() + 1); ax.patch.set_visible(False)
    ax.plot(edges, soc, color=C["soc"], lw=1.7, zorder=5)
    ax.plot([0, 24], [6000, 6000], "o", ms=3.4, color=C["soc"], zorder=6, clip_on=False)
    ax.set_ylabel("储电量 / kWh")
    ax.set_ylim(0, 13200)
    ax.yaxis.set_major_locator(MultipleLocator(2000))
    fmt_time_axis(ax)
    ax.set_xlabel("时刻")

    notes = [(0.72, "①谷价\n充电"), (7.65, "②早高峰\n放电"), (12.0, "③光伏与午间\n低谷充电"),
             (19.35, "④晚高峰\n放电"), (22.8, "①谷价\n充电")]
    for xpos, txt in notes:
        ax.text(xpos, 13000, txt, fontsize=7.8, ha="center", va="top", color="#333333",
                linespacing=1.1)

    handles = [Line2D([], [], color=C["soc"], lw=1.7, label="储电量"),
               Line2D([], [], color=C["price"], lw=0.9, label="电价"),
               Patch(color=C["q"], alpha=0.2, lw=0, label="主要充电阶段"),
               Patch(color=C["dis"], alpha=0.26, lw=0, label="主要放电阶段")]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 1.14),
              ncol=4, handlelength=1.6, columnspacing=1.4)
    save(fig, "图3_储能电量轨迹与电价")


# ================= 图4 与无储能方案对比 =================
def fig_compare():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(WIDTH, 2.75),
                                 gridspec_kw={"width_ratios": [1.9, 1], "wspace": 0.3})
    hours = np.arange(24)
    hb = base_q.reshape(24, 6).sum(1)
    ho = q.reshape(24, 6).sum(1)
    w = 0.4
    a1.bar(hours + 0.5 - w / 2, hb, w, color=C["base"], label=f"无储能方案（{base_q.sum():,.0f} kWh）", lw=0)
    a1.bar(hours + 0.5 + w / 2, ho, w, color=C["q"], label=f"优化方案（{q.sum():,.0f} kWh）", lw=0)
    a1.set_xlim(0, 24)
    a1.xaxis.set_major_locator(MultipleLocator(4))
    a1.xaxis.set_minor_locator(MultipleLocator(1))
    a1.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v)}:00"))
    a1.set_xlabel("时刻")
    a1.set_ylabel("每小时购电量 / kWh")
    a1.set_ylim(0, 9600)
    a1.yaxis.set_major_locator(MultipleLocator(2000))
    a1.grid(axis="y", lw=0.4, alpha=0.35)
    a1.legend(loc="upper center", bbox_to_anchor=(0.5, 1.0), ncol=1, handlelength=1.3,
              handletextpad=0.5)
    panel_label(a1, "(a)")

    cb, co = np.cumsum(cost_base), np.cumsum(cost_opt)
    a2.plot(edges, np.r_[0, cb] / 1e4, color=C["base"], lw=1.4, label="无储能方案")
    a2.plot(edges, np.r_[0, co] / 1e4, color=C["q"], lw=1.4, label="优化方案")
    a2.annotate("", xy=(24.6, co[-1] / 1e4), xytext=(24.6, cb[-1] / 1e4),
                arrowprops=dict(arrowstyle="<->", lw=0.7, color="#333333",
                                shrinkA=0, shrinkB=0), annotation_clip=False)
    a2.text(9.5, (cb[-1] + co[-1]) / 2e4 - 0.2,
            f"节省 {cb[-1]-co[-1]:,.0f} 元\n（{(cb[-1]-co[-1])/cb[-1]:.1%}）",
            fontsize=7.8, ha="center", va="center", linespacing=1.2)
    a2.text(1.0, cb[-1] / 1e4 - 0.1, f"{cb[-1]:,.0f} 元", fontsize=7.5, color="#666666", va="top")
    a2.text(1.0, co[-1] / 1e4 - 0.1, f"{co[-1]:,.0f} 元", fontsize=7.5, color=C["q"], va="top")
    a2.axhline(cb[-1] / 1e4, color=C["base"], lw=0.5, ls=":")
    a2.axhline(co[-1] / 1e4, color=C["q"], lw=0.5, ls=":")
    fmt_time_axis(a2)
    a2.xaxis.set_major_locator(MultipleLocator(8))
    a2.set_xlabel("时刻")
    a2.set_ylabel("累计购电费 / 万元")
    a2.set_ylim(0, 5.6)
    a2.grid(axis="y", lw=0.4, alpha=0.35)
    panel_label(a2, "(b)")
    save(fig, "图4_与无储能方案对比")


if __name__ == "__main__":
    fig_inputs(); fig_balance(); fig_soc(); fig_compare()
    print("cost", S.total_cost, "base", cost_base.sum())
