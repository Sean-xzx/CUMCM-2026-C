[English](README.md) | 简体中文

# CUMCM-2026-C

由数学建模竞赛项目整理而来的微电网负荷/光伏预测与储能调度实验。

项目包含确定性日前调度（第一问）、仅使用历史信息的预测与经验机会约束（第二问）、光伏预报四阶段更新（第三问），以及波动电价的 EW + Ridge 预测（第四问）。面向希望复现数值实验的开发者；不连接真实电网或交易服务。

## 演示与参考结果

无需账号的合成数据示例调用保留的第一问求解器和共享的48小时优化器，预期输出为：

```json
{
  "solver_status": "Optimal",
  "periods": 144,
  "total_cost_yuan": 3206.6449614242956,
  "total_grid_purchase_kwh": 8016.61240356074,
  "soc_terminal_kwh": 6000.0,
  "synthetic_48h_lp_success": true
}
```

输出文件为 `runs/demo/demo_dispatch.xlsx`、`demo_dispatch.csv` 和 `demo_summary.json`。费用单位为元，电量单位为 kWh。这是合成数据示例，**不是竞赛结果**。

原竞赛结果保存在 [results/reference/final](results/reference/final)。第四问当前采用同类型8日 EW + Ridge；旧的7日价格基线仅作比较。

| 问题 | 时间范围 | 原结果总费用（元） |
|---|---|---:|
| 第一问 | 一个典型日 | 35,126.948589 |
| 第二问 | 2025-02-01 至 2025-12-31 | 13,634,329.584094 |
| 第三问 | 同一334天 | 13,149,460.948548 |
| 第四问-2 | 同一334天 | 14,308,775.528818 |
| 第四问-3 | 同一334天 | 13,854,618.279093 |

实际重算范围与误差容限见 [验证记录](docs/VALIDATION.md)。第一问的单日费用不能直接与334天总费用比较。

![典型日储电量与电价](docs/assets/q1/图3_储能电量轨迹与电价.png)

## 环境要求与快速开始

本地验证环境：Windows、CPython **3.12.14**、CPU、新建虚拟环境。其他操作系统及 Python 版本暂不声称已经验证。需要 Git 和可用的 Python 3.12。运行示例和模型不需要账号、API 密钥、GPU、数据库或付费服务。安装依赖需要联网；依赖与资源准备好后，模型可离线运行。

在希望保存仓库的位置打开 PowerShell：

```powershell
git clone https://github.com/Sean-xzx/CUMCM-2026-C.git
cd CUMCM-2026-C
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-demo.txt
.\.venv\Scripts\python.exe scripts/run.py check-sources
.\.venv\Scripts\python.exe scripts/run.py demo --out runs/demo
```

成功标准为 `Optimal`、144个时段、末端储电量6000 kWh、`synthetic_48h_lp_success: true`，且上述三个文件都存在。示例费用与末端储电量的误差容限分别为 `1e-5` 元、`1e-6` kWh。快速开始不需要官方附件。

运行全部原有单元测试、Notebook和完整复现前，安装已验证的完整依赖锁：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
```

`requirements.txt` 锁定完整安装环境，包括来自官方轮子索引的 CPU PyTorch 和 XGBoost。`requirements-demo.txt` 锁定示例的六项直接依赖，间接依赖由 pip 解析。验证记录使用完整依赖锁所对应的环境。

## 官方资源与完整复现

官方附件及由其转换的输入 CSV **不在仓库中分发**，因为尚未确认其再分发授权。请单独取得 C 题附件包，保持文件不变；来源、目录和哈希说明见 [资源文档](docs/RESOURCES.md)。资源由用户放在本地，本项目不会自动下载。

指定数据目录应包含：

```text
data/official/
  附件1.xlsx
  附件2.xlsx
  附件3.xlsx
  附件4.xlsx
  附件5/
    result1.xlsx
    result2.xlsx
    result3.xlsx
    result4-2.xlsx
    result4-3.xlsx
```

```powershell
.\.venv\Scripts\python.exe scripts/run.py check-resources --data-dir data/official
.\.venv\Scripts\python.exe scripts/run.py reproduce --data-dir data/official --out runs/full
.\.venv\Scripts\python.exe scripts/run.py verify --results runs/full
```

也可以指定仓库外的目录；路径含空格时加引号。九个 SHA-256 必须与 [资源清单](data/resource-manifest.json) 一致。文件缺失或内容改变会明确报错，并返回非零退出码。不要把无关文件改名来绕过检查。

复现流程在 `runs/full` 下新生成五份 `result*.xlsx`、各问摘要、第四问 EW 指标和运行汇总；最后一条命令生成 `reference-comparison.json`。已提交的原参考结果保持不变。成功要求计划/调整购电量与参考值的差异不超过 **1e-4 kWh**。Excel ZIP 的元信息可能变化，因此不以文件字节相同判断数值复现成功。

使用 `--questions q1 q2` 可只运行指定问题；添加 `--select-q3` 会重新比较第三问一月的16组参数。默认第三问使用原记录中的冻结参数 `A0=0.6, ALO=0.7, AHI=0.9`，第四问会重新执行一月 EW 选参。完整运行明显比最小示例耗时，实际时间记录在验证文档中，不作为性能承诺。

## 结构与数据流

```text
scripts/run.py           可移植入口和资源检查
src/q1/                 保留的确定性求解器和测试
src/q2/                 保留的预测/CCP库、Notebook、测试
src/q3/                 保留的四阶段主Notebook
src/q4/                 保留的共享引擎、EW方案、Notebook、测试
src/delivery/           保留的模板填报与校验程序
tests/                  新增的可移植性和输入输出检查
results/reference/      原指标、图表与最终工作簿
docs/                   架构、资源和验证文档
experiments/            有价值的第一问v2和第三问历史方案
data/resource-manifest.json  仅资源哈希，不含官方原始数据
source-manifest.json    原始文件映射及SHA-256
```

负荷/光伏数据经过预测、历史误差余量、储能线性规划和实际结算产生结果。第三问加入每日0/6/12/18点发布的小时级**光伏**预报，插值到十分钟，并只调整尚未执行的决策。第四问用同类型 EW 价格基线，加上由预测净负荷变化驱动的 Ridge 修正；预测电价进入优化，实际电价用于结算。交付函数负责模板填报与结果规范化。

各问继承方法，但第三、四问分别保留部分独立实现，不是逐级直接导入的程序链。适配方式见 [架构及原文件保留原则](docs/ARCHITECTURE.md)和[逐文件说明](docs/FILES.md)。原核心代码、数据和参考结果没有改写。入口通过显式参数配置路径，并在临时工作目录执行第三问原代码单元。部分原文件仍保留作者电脑的绝对路径，运行时应使用统一入口，避免直接使用其历史默认入口。

## 测试、限制与开发

- GitHub Actions 在 Windows/Python 3.12 上检查原文件完整性、合成数据示例、可运行的原单元测试及文档；不会训练四种候选预测模型或执行需要官方数据的全年计算。
- 四项原测试依赖公开仓库未提供的资源或写死的作者路径，公共 CI 明确跳过；官方数据的实际执行证据由复现/核对命令提供。单元测试通过不等于全年结果已经复现。
- 第二问部署模型为仅根据一月选出的 EW/EWMA。Ridge/XGBoost/GRU 的对照训练是另一项实验，不声称已经重新训练其全年结果。保留的机器学习实现种子为42，随机结果仍可能随环境变化。
- 研究假设包括单向充/放电效率0.9、第二至四问在2月1日将SOC初始化为6000 kWh一次，以及48小时规划没有硬终端SOC等式。这些不是实际运行保障。
- 原论文未加入发布包，因为标题和部分百分比、第四问表格尚未统一。原方法文档作为历史证据保留，可能含编辑备注；当前运行说明和参考结果优先。

常见问题：导入第二问提示缺少 `torch`/`xgboost` 时安装完整依赖锁；全年计算失败时检查资源哈希；使用 Python 3.12 和上述命令，不要在任意目录直接运行 Notebook。原绘图程序中的中文标签可能需要 CJK 字体，数值入口的核对不要求生成这些图片。

项目是竞赛研究快照，没有持续维护或技术支持承诺。问题反馈入口为 [Issues](https://github.com/Sean-xzx/CUMCM-2026-C/issues)，请提供命令、Python/依赖版本及去除秘密后的错误信息；不要附带凭据或私人取得的资源。开发适配层时保留基线清单；如需改变原算法，应建立明确标注的研究分支。

## 许可证、来源与致谢

按所有者要求，保留所有权利，不添加开源许可证。公开可查看不代表普遍授予使用、修改或再分发许可；如需此类使用，请取得权利人的许可。第三方资源保留原使用条件，本仓库不会重新授权。来源及未发布材料见 [资源文档](docs/RESOURCES.md)。保留的代码来自队伍本地 CUMCM 项目，数值计算使用 NumPy、pandas、SciPy/HiGHS、scikit-learn，以及适用的原机器学习依赖。介绍结果时请注明项目及相关原方法来源。
