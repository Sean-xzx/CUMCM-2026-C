"""绘制2025年1月电价的日内分布（31条逐日曲线+中位数/IQR）。"""
from __future__ import annotations

from pathlib import Path
import json
import sys

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

HERE = Path(__file__).resolve().parent
BASE = Path(r"C:\Users\12055\Desktop\2026 国赛")
OUT = HERE / "图表"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(HERE))
from q4_pipeline import load_official_data


def choose_chinese_font() -> str:
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Source Han Sans SC"):
        if name in available:
            return name
    return "DejaVu Sans"


def main() -> None:
    data = load_official_data(BASE)
    january = np.asarray(data.price[:31], dtype=float)
    if january.shape != (31, 144):
        raise AssertionError(f"1月电价矩阵应为(31,144)，实际为{january.shape}")
    if not np.isfinite(january).all() or (january < 0).any():
        raise AssertionError("1月电价包含非有限值或负值")

    median = np.median(january, axis=0)
    q25, q75 = np.quantile(january, [0.25, 0.75], axis=0)
    mean = january.mean(axis=0)
    x = (np.arange(144) + 0.5) / 6  # 各10分钟时段的中心时刻

    font = choose_chinese_font()
    with mpl.rc_context({
        "font.sans-serif": [font, "SimHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.edgecolor": "#333333",
        "axes.linewidth": 0.8,
        "font.size": 9,
        "axes.titlesize": 11,
        "axes.labelsize": 9.5,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "legend.fontsize": 8,
        "svg.fonttype": "none",
    }):
        fig, ax = plt.subplots(figsize=(8.0, 4.5), constrained_layout=True)

        # 31条逐日曲线只用于表现离散程度，不逐条放入图例。
        for row in january:
            ax.plot(x, row, color="#9AA0A6", lw=0.65, alpha=0.24, zorder=1)
        ax.fill_between(x, q25, q75, color="#56B4E9", alpha=0.23,
                        linewidth=0, label="25%–75%分位区间", zorder=2)
        ax.plot(x, median, color="#0072B2", lw=2.0, label="时段中位数", zorder=4)
        ax.plot(x, mean, color="#D55E00", lw=1.45, ls="--", label="时段均值", zorder=3)

        ax.set_title("2025年1月电价日内分布", loc="left", fontweight="bold", pad=30)
        ax.text(0, 1.015, "灰线为31天逐日曲线；横轴表示一天内的实际时段",
                transform=ax.transAxes, ha="left", va="bottom", fontsize=8.2,
                color="#5F6368")
        ax.set_xlabel("时刻")
        ax.set_ylabel("电价（元/kWh）")
        ax.set_xlim(0, 24)
        ax.set_xticks(np.arange(0, 25, 4))
        ax.set_xticklabels([f"{h}:00" for h in range(0, 25, 4)])
        ax.set_ylim(bottom=max(0, january.min() - 0.05 * np.ptp(january)))
        ax.grid(axis="y", color="#D9D9D9", lw=0.55, alpha=0.6, ls="--")
        ax.grid(axis="x", visible=False)
        ax.legend(loc="upper left", frameon=False, ncol=3)
        ax.text(1, -0.19, "数据来源：附件4；按10分钟时段整理。",
                transform=ax.transAxes, ha="right", va="top", fontsize=7.6,
                color="#6B7280")

        png = OUT / "问题四_一月电价日内分布.png"
        svg = OUT / "问题四_一月电价日内分布.svg"
        fig.savefig(png, dpi=350, bbox_inches="tight", facecolor="white")
        fig.savefig(svg, bbox_inches="tight", facecolor="white")
        plt.close(fig)

        # 按问题二的经验日型再画一版：周五、周六为低负荷型，
        # 周日至周四为高负荷型；该分组也用于价格同类型EW模型。
        weekdays = np.asarray(data.dates[:31].dayofweek)
        low_mask = np.isin(weekdays, [4, 5])
        high = january[~low_mask]
        low = january[low_mask]
        # 与问题二参考图一致：CV按“每日平均电价”的跨日波动计算，
        # 不把一天内峰谷波动混入日际CV。
        high_daily = high.mean(axis=1)
        low_daily = low.mean(axis=1)
        high_cv = high_daily.std(ddof=1) / high_daily.mean()
        low_cv = low_daily.std(ddof=1) / low_daily.mean()

        fig, ax = plt.subplots(figsize=(6.3, 6.0), constrained_layout=True)
        for row in high:
            ax.plot(x, row, color="#EF4B4F", lw=0.75, alpha=0.17, zorder=1)
        for row in low:
            ax.plot(x, row, color="#3B6FD8", lw=0.75, alpha=0.18, zorder=1)
        ax.plot(x, high.mean(axis=0), color="#E84246", lw=3.0,
                label=f"高负荷型：周日至周四（{len(high)}天）", zorder=4)
        ax.plot(x, low.mean(axis=0), color="#3367D6", lw=3.0,
                label=f"低负荷型：周五、周六（{len(low)}天）", zorder=4)

        ax.set_title("(a) 1月电价的两类日型", loc="left",
                     fontsize=15, fontweight="bold", pad=12)
        ax.set_xlabel("时刻", fontsize=12)
        ax.set_ylabel("电价 /（元/kWh）", fontsize=12)
        ax.set_xlim(0, 24)
        ax.set_xticks(np.arange(0, 25, 4))
        ax.set_xticklabels([f"{h}:00" for h in range(0, 25, 4)])
        ax.set_ylim(max(0, january.min() - 0.08 * np.ptp(january)),
                    january.max() + 0.18 * np.ptp(january))
        ax.grid(axis="y", color="#D7DBE2", lw=0.8, alpha=0.85, ls="--")
        ax.grid(axis="x", visible=False)
        ax.legend(loc="upper left", bbox_to_anchor=(0.01, 0.985),
                  frameon=False, fontsize=9.8, handlelength=2.0)
        ax.text(0.025, 0.755,
                f"高负荷型 日均电价CV = {high_cv:.2%}\n"
                f"低负荷型 日均电价CV = {low_cv:.2%}",
                transform=ax.transAxes, ha="left", va="top",
                fontsize=10.5, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.38", facecolor="white",
                          edgecolor="#252A34", linewidth=1.1, alpha=0.96))
        fig.text(0.99, -0.005,
                 "注：日型沿用问题二，并用于价格同类型EW预测。数据来源：附件4。",
                 ha="right", va="top", fontsize=7.2, color="#6B7280")
        typed_png = OUT / "问题四_一月电价分类型日内分布.png"
        typed_svg = OUT / "问题四_一月电价分类型日内分布.svg"
        fig.savefig(typed_png, dpi=350, bbox_inches="tight", facecolor="white")
        fig.savefig(typed_svg, bbox_inches="tight", facecolor="white")
        plt.close(fig)

    report = {
        "input_shape": list(january.shape),
        "days": 31,
        "slots_per_day": 144,
        "min_yuan_per_kWh": float(january.min()),
        "max_yuan_per_kWh": float(january.max()),
        "mean_yuan_per_kWh": float(january.mean()),
        "font": font,
        "png": str(png),
        "svg": str(svg),
        "typed_png": str(typed_png),
        "typed_svg": str(typed_svg),
        "high_load_type_days": int((~low_mask).sum()),
        "low_load_type_days": int(low_mask.sum()),
        "high_load_type_daily_mean_price_cv": float(high_cv),
        "low_load_type_daily_mean_price_cv": float(low_cv),
        "price_model": "最近8个同负荷类型日、同目标时段的有限窗EW基线（decay=0.8）+滚动Ridge修正（alpha=1）",
        "terminology": "严格区分时称EW；它不是递归、无限记忆的EWMA。",
    }
    (OUT / "问题四_一月电价日内分布_验证.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
