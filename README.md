[简体中文](README.zh-CN.md) | English

# CUMCM-2026-C

**Forecast demand and solar generation, then turn uncertainty into lower-cost microgrid purchasing and battery schedules.**

A microgrid must buy electricity and schedule storage before demand, solar output and prices are fully known. This competition project connects forecasting, constrained optimization and realized settlement to evaluate how updated information changes purchasing costs. Under the fixed-price setting, the Q3 scheme cost **CNY 484,868.64 less (3.56%)** than Q2 over the same 334 days.

## My contribution

In our **three-person team, I served as team lead and programmer**. Model design and the paper were collaborative team work. My responsibilities were:

- **Implementation and debugging:** implement the prediction, electricity-purchasing and storage-optimization programs across Q1–Q4, connecting data processing to numerical solvers.
- **Experiments and delivery:** run/debug experiments, compare schemes, and export/check the result workbooks, connecting model outputs to verifiable evidence.
- **Team coordination:** coordinate progress and the interfaces between modeling, code, experiments and writing.

## Methods and research highlights

| Stage | Key method | Decision it supports |
|---|---|---|
| Q1 | Ten-minute linear programming with energy balance, storage limits and state-of-charge (SOC) constraints | Deterministic typical-day purchasing and battery dispatch |
| Q2 | Exponentially weighted history forecasts (EW/EWMA), empirical residual quantiles and 48-hour rolling optimization | Purchasing under uncertain net load |
| Q3 | PV forecasts released at 0/6/12/18; inverse-error-variance fusion with historical forecasts | Intraday updates subject to adjustment costs and a fixed-midnight reference |
| Q4 | Same-type 8-day EW price baseline, decay 0.8, plus Ridge regression correction from predicted net-load changes | Price-aware purchasing, settled at actual prices |

The design uses only information available at each decision time, selects parameters using January, and evaluates February–December. Q2–Q4 carry battery SOC across days instead of resetting it daily. [Architecture and implementation boundaries](docs/ARCHITECTURE.md) explain how forecasts, risk margins, LP plans and settlement cooperate.

## Results and evidence

| Scheme | Evaluation period | Total cost (CNY) |
|---|---|---:|
| Q1 | One typical day | 35,126.948589 |
| Q2 | 2025-02-01 to 2025-12-31 | 13,634,329.584094 |
| Q3 | Same 334 days, fixed prices | 13,149,460.948548 |
| Q4-2 | Same 334 days, variable prices | 14,308,775.528818 |
| Q4-3 | Same 334 days, variable prices | 13,854,618.279093 |

- **Fixed-price comparison:** Q3 versus Q2 saves CNY 484,868.64 (3.56%). This compares the complete schemes; individual intraday update times were not isolated by ablation.
- **Variable-price comparison:** final EW + Ridge schemes save CNY **34,139.52 / 39,196.25** in Q4-2 / Q4-3 versus the recorded lag-7 + Ridge baseline. The final schemes were rerun; the old baseline costs come from [the preserved comparison CSV](results/reference/q4/EW与7日基线_优化费用对比.csv).
- **Reproduction:** all four current numerical paths were rerun. Planned/adjusted purchases in the five exports differ from the original references by at most **1.03e-11 kWh**; the acceptance tolerance is **1e-4 kWh**. Tests: **30 passed, 4 explicitly skipped**.

These are experimental results for the supplied data, not real-grid savings. Q1 is a single-day case; fixed- and variable-price totals are separate comparisons. [Validation scope and evidence](docs/VALIDATION.md) · [Five reference workbooks](results/reference/final).

![Typical-day storage and price](docs/assets/q1/图3_储能电量轨迹与电价.png)

## Run a small demo

Requires Git, Python 3.12 and CPU. Full numerical runs were verified on Windows/CPython **3.12.14**; GitHub Actions passed demo/unit checks on Windows/Python **3.12.10**. Installation needs internet; execution is offline. The synthetic demo needs no account, GPU or official attachments.

```powershell
git clone https://github.com/Sean-xzx/CUMCM-2026-C.git
cd CUMCM-2026-C
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-demo.txt
.\.venv\Scripts\python.exe scripts/run.py check-sources
.\.venv\Scripts\python.exe scripts/run.py demo --out runs/demo
```

Expected: `Optimal`, 144 slots, cost **3206.6449614242956 CNY**, terminal SOC **6000 kWh**, and `synthetic_48h_lp_success: true`. Files under `runs/demo`: `demo_dispatch.xlsx`, `demo_dispatch.csv`, `demo_summary.json`. This is synthetic data. Cost/SOC tolerances: `1e-5` CNY / `1e-6` kWh.

## Reproduce the competition experiments

Obtain the official attachments separately and arrange them under `data/official` as specified in [resources, layout and hashes](docs/RESOURCES.md). Redistribution permission is unconfirmed, so raw inputs are excluded. All nine resource hashes must match; an external `--data-dir` is supported.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/run.py check-resources --data-dir data/official
.\.venv\Scripts\python.exe scripts/run.py reproduce --data-dir data/official --out runs/full
.\.venv\Scripts\python.exe scripts/run.py verify --results runs/full
```

Outputs: five `result*.xlsx` files, question summaries, Q4 EW metrics and `reference-comparison.json`. Use `--questions q1 q2` for a subset. Q3 defaults to frozen parameters `A0=0.6, ALO=0.7, AHI=0.9`; `--select-q3` reruns its 16 January combinations. Q4 reruns January EW selection. Timing and numerical checks are recorded in [VALIDATION](docs/VALIDATION.md).

The full lock includes CPU PyTorch/XGBoost and all installed dependencies; the demo file pins six direct dependencies. Use the full lock for the recorded environment. Missing `torch`/`xgboost`: install it. Resource errors: check hashes. Original helper paths may be author-specific; run through `scripts/run.py`.

## Navigate the project

```text
src/                   original Q1–Q4 models and delivery routines
scripts/ and tests/    portable entry point and validation
results/reference/     recorded costs, figures and final workbooks
experiments/           Q1 v2 and distinct Q3 historical variants
docs/                  architecture, file guide and resource/evidence notes
```

[File-by-file guide](docs/FILES.md) · [Architecture](docs/ARCHITECTURE.md) · [Resource conditions](docs/RESOURCES.md). The 94 preserved original files retain their hashes; core code, inputs and reference outputs were not rewritten.

## Scope, feedback and rights

This is a competition research snapshot. CI checks source integrity, documentation, available unit tests and the synthetic demo; official-data annual runs are separate. Four original tests are skipped because of absent public resources or embedded author paths. Full Ridge/XGBoost/GRU benchmark training, Q3's optional parameter search and all historical helpers were not rerun; other operating systems are unverified. ML seeds are 42. Model assumptions and remaining limits are in [VALIDATION](docs/VALIDATION.md) and [ARCHITECTURE](docs/ARCHITECTURE.md).

Report reproducible problems through [Issues](https://github.com/Sean-xzx/CUMCM-2026-C/issues). Develop adapters without overwriting the protected baseline. **All rights reserved; no open-source license is granted.** Request permission for use, modification or redistribution. Official resources and dependencies retain their owners' terms; numerical work uses NumPy, pandas, SciPy/HiGHS and scikit-learn. See [sources and acknowledgments](docs/RESOURCES.md).
