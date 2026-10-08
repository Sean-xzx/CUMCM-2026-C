[English](README.md) | 简体中文

# CUMCM-2026-C

**从负荷与光伏预测出发，将不确定性转化为费用更低的微电网购电与储能调度方案。**

微电网需要在负荷、光伏出力和电价尚未完全确定时，提前安排购电与储能。本竞赛项目把预测、约束优化和实际结算串联起来，评估信息更新如何影响购电费用。在同一334天、固定电价设定下，第三问方案相对第二问**节省48.49万元（3.56%）**。

## 我的贡献

在**三人团队中，我担任队长兼编程手**。模型思路和论文由团队共同完成；我的主要职责是：

- **程序实现与调试**：负责第一至四问的预测、购电和储能优化程序，打通数据处理与数值求解。
- **实验验证与结果交付**：运行、调试实验，开展方案对照，输出并检查结果工作簿，把模型输出转化为可核查的证据。
- **团队协调**：协调各部分进度，衔接建模、代码、实验与论文工作。

## 技术与研究亮点

| 阶段 | 关键方法 | 支撑的决策 |
|---|---|---|
| 第一问 | 十分钟粒度线性规划，纳入能量平衡、储能功率及荷电状态（SOC）约束 | 确定性典型日购电与充放电安排 |
| 第二问 | 历史指数加权预测（EW/EWMA）、经验残差分位数与48小时滚动优化 | 净负荷不确定时的购电计划 |
| 第三问 | 0/6/12/18点光伏预报，与历史预测按误差方差加权融合 | 在调整费用和固定0点基准约束下进行日内更新 |
| 第四问 | 同类型8日EW电价基线（衰减0.8），叠加预测净负荷变化驱动的Ridge回归修正 | 根据预测电价优化购电，按实际电价结算 |

设计上严格限定各决策时刻可获得的信息，用一月选参、二至十二月评价；第二至四问的SOC跨日延续，不逐日重置。[架构与实现边界](docs/ARCHITECTURE.md)解释了预测、风险余量、线性规划与结算如何协作。

## 成果与证据

| 方案 | 评价区间 | 总费用（元） |
|---|---|---:|
| 第一问 | 一个典型日 | 35,126.948589 |
| 第二问 | 2025-02-01至2025-12-31 | 13,634,329.584094 |
| 第三问 | 同一334天，固定电价 | 13,149,460.948548 |
| 第四问-2 | 同一334天，波动电价 | 14,308,775.528818 |
| 第四问-3 | 同一334天，波动电价 | 13,854,618.279093 |

- **固定电价对照**：第三问相对第二问节省484,868.64元（3.56%）。这是完整方案比较，未通过消融实验单独识别各日内更新时刻的贡献。
- **波动电价对照**：最终EW + Ridge方案相对原7日基线 + Ridge，第四问-2／-3分别节省 **34,139.52／39,196.25元**。最终方案已重算；旧基线费用取自[保留的对照CSV](results/reference/q4/EW与7日基线_优化费用对比.csv)。
- **复现核验**：四问当前数值路径均已重算，五份结果表的计划／调整购电量与原结果最大差异 **1.03e-11 kWh**，验收容限为 **1e-4 kWh**；测试 **30项通过、4项明确跳过**。

以上是给定数据上的实验结果，不是实际电网收益。第一问仅为单日结果；固定与波动电价分别作对照。[验证范围与证据](docs/VALIDATION.md) · [五份参考工作簿](results/reference/final)。

![典型日储电量与电价](docs/assets/q1/图3_储能电量轨迹与电价.png)

## 运行最小示例

需要Git、Python 3.12和CPU。完整数值流程在Windows／CPython **3.12.14**上验证；GitHub Actions在Windows／Python **3.12.10**上通过示例与单元检查。安装依赖需要联网，运行可离线；合成示例不需要账号、GPU或官方附件。

```powershell
git clone https://github.com/Sean-xzx/CUMCM-2026-C.git
cd CUMCM-2026-C
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-demo.txt
.\.venv\Scripts\python.exe scripts/run.py check-sources
.\.venv\Scripts\python.exe scripts/run.py demo --out runs/demo
```

预期：`Optimal`、144个时段、费用 **3206.6449614242956元**、末端SOC **6000 kWh**、`synthetic_48h_lp_success: true`。`runs/demo`下生成`demo_dispatch.xlsx`、`demo_dispatch.csv`、`demo_summary.json`，输入为合成数据。费用／SOC容限为`1e-5`元／`1e-6` kWh。

## 复现竞赛实验

单独取得官方附件，按[资源、目录与哈希说明](docs/RESOURCES.md)放入`data/official`。因再分发授权未确认，仓库不包含原始输入。九个资源哈希必须一致，也可指定仓库外的`--data-dir`。

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/run.py check-resources --data-dir data/official
.\.venv\Scripts\python.exe scripts/run.py reproduce --data-dir data/official --out runs/full
.\.venv\Scripts\python.exe scripts/run.py verify --results runs/full
```

输出五份`result*.xlsx`、各问摘要、第四问EW指标及`reference-comparison.json`。`--questions q1 q2`可只运行指定问题。第三问默认冻结参数`A0=0.6, ALO=0.7, AHI=0.9`，`--select-q3`重做一月16组比较；第四问重新执行一月EW选参。实际耗时与数值校验见[验证记录](docs/VALIDATION.md)。

完整依赖锁包含CPU PyTorch／XGBoost及全部已安装依赖；示例文件锁定六项直接依赖。复现已记录环境时使用完整锁。缺少`torch`／`xgboost`时安装完整锁；资源错误时核对哈希。原辅助脚本可能保留作者路径，应通过`scripts/run.py`运行。

## 项目导航

```text
src/                   原第一至四问模型与交付程序
scripts/ 和 tests/     可移植入口与验证
results/reference/     原费用、图表及最终工作簿
experiments/           第一问v2及第三问不同历史方案
docs/                  架构、逐文件说明、资源与验证记录
```

[逐文件说明](docs/FILES.md) · [架构](docs/ARCHITECTURE.md) · [资源使用条件](docs/RESOURCES.md)。94份保留原件的哈希不变；核心代码、输入和参考结果未改写。

## 项目边界、反馈与使用条件

项目是竞赛研究快照。CI检查原件完整性、文档、可运行单元测试和合成示例，官方数据全年计算单独验证。四项原测试因公开资源缺失或写死作者路径而跳过。完整Ridge／XGBoost／GRU对照训练、第三问可选选参及全部历史辅助入口未重跑，其他操作系统未验证；机器学习种子为42。模型假设与其余限制见[验证记录](docs/VALIDATION.md)及[架构](docs/ARCHITECTURE.md)。

通过[Issues](https://github.com/Sean-xzx/CUMCM-2026-C/issues)反馈可复现问题。开发适配层时不要覆盖受保护的原件。**保留所有权利，不添加开源许可证**；使用、修改或再分发请取得许可。官方资源和依赖保留原权利条件，数值工作使用NumPy、pandas、SciPy/HiGHS和scikit-learn；见[来源与致谢](docs/RESOURCES.md)。
