"""绘制问题四1月电价两类日型双面板图（无图号、无(a)(b)）。"""
from pathlib import Path
import sys
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "图表"
BASE = Path(r"C:\Users\12055\Desktop\2026 国赛")
sys.path.insert(0, str(HERE))
from q4_pipeline import load_official_data

available = {f.name for f in font_manager.fontManager.ttflist}
font = next((x for x in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC") if x in available), "DejaVu Sans")

data = load_official_data(BASE)
jan = np.asarray(data.price[:31], float)
weekdays = np.asarray(data.dates[:31].dayofweek)
low_mask = np.isin(weekdays, [4, 5])
high, low = jan[~low_mask], jan[low_mask]
x = (np.arange(144) + 0.5) / 6

with mpl.rc_context({
    "font.sans-serif": [font, "SimHei", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#333333", "axes.linewidth": 0.8,
    "font.size": 9, "svg.fonttype": "none",
}):
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.35), sharex=True, sharey=True)
    fig.subplots_adjust(left=0.075, right=0.985, bottom=0.16, top=0.76, wspace=0.08)
    groups = [("高负荷型（22天）", high, "#3C5488"),
              ("低负荷型（9天）", low, "#E87525")]
    ymin = max(0, jan.min() - 0.05 * np.ptp(jan))
    ymax = jan.max() + 0.04 * np.ptp(jan)
    for ax, (label, arr, color) in zip(axes, groups):
        for row in arr:
            ax.plot(x, row, color=color, lw=0.68, alpha=0.20, zorder=1)
        q25, q75 = np.quantile(arr, [0.25, 0.75], axis=0)
        ax.fill_between(x, q25, q75, color=color, alpha=0.13,
                        linewidth=0, label="25%–75%分位区间", zorder=2)
        ax.plot(x, np.median(arr, axis=0), color=color, lw=2.0,
                label="时段中位数", zorder=4)
        ax.plot(x, arr.mean(axis=0), color="#222222", lw=1.35,
                ls="--", label="时段均值", zorder=3)
        ax.set_title(label, loc="left", fontsize=10.2, fontweight="bold", pad=7)
        ax.set_xlim(0, 24); ax.set_ylim(ymin, ymax)
        ax.set_xticks(np.arange(0, 25, 4))
        ax.set_xticklabels([f"{h}:00" for h in range(0, 25, 4)])
        ax.set_xlabel("时刻", fontsize=9.5)
        ax.grid(axis="y", color="#D9D9D9", lw=0.55, alpha=0.62, ls="--")
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("电价（元/kWh）", fontsize=9.5)
    axes[0].legend(loc="upper left", frameon=False, fontsize=7.5)
    fig.text(0.075, 0.945, "2025年1月不同负荷日型的电价日内分布",
             ha="left", va="top", fontsize=12.2, fontweight="bold")
    fig.text(0.075, 0.875,
             "日型沿用问题二：周五—周六为低负荷型，其余为高负荷型；预测时只使用相同日型的历史电价。",
             ha="left", va="top", fontsize=8.0, color="#5F6368")
    fig.text(0.985, 0.035, "数据来源：附件4；按10分钟时段整理。",
             ha="right", va="bottom", fontsize=7.2, color="#6B7280")
    png = OUT / "问题四_一月电价分类型日内分布_双图无编号.png"
    svg = OUT / "问题四_一月电价分类型日内分布_双图无编号.svg"
    fig.savefig(png, dpi=350, bbox_inches="tight", facecolor="white")
    fig.savefig(svg, bbox_inches="tight", facecolor="white")
    plt.close(fig)

print(png)
print(svg)
