# File guide / 逐文件说明

This guide covers every preserved file in the public release. `source-manifest.json` provides its original relative location and exact hash. Private/excluded originals remain described in the local audit and are not silently deleted. New integration files are listed separately.

本表覆盖公开副本全部保留文件；原位置与哈希见根目录清单。未发布原件保留在本地，其完整说明见本地项目梳理报告。新增入口与配置单独列出。

## Added release files / 新增文件

| File | Content and relationship / 内容及关系 |
|---|---|
| `README.md`, `README.zh-CN.md` | Equivalent English/Chinese installation, demo, reproduction and rights instructions / 中英文等价运行说明 |
| `requirements.txt` | Full verified 67-package environment lock including CPU ML dependencies / 完整验证环境锁 |
| `requirements-demo.txt` | Six direct packages for the account-free synthetic demo / 合成示例六项直接依赖 |
| `scripts/run.py` | Check hashes, invoke unchanged solvers with explicit paths, stage notebook inputs, compare final exports / 哈希检查、原求解器调用、Notebook资源暂存及结果核对 |
| `scripts/check_docs.py` | Check documentation paths, bilingual commands/values and CLI help / 文档路径、双语命令和帮助检查 |
| `tests/test_portable.py` | Real solver demo, protected-source hashes, missing-resource failures and workbook values / 求解示例、原件完整性、缺失资源与结果表校验 |
| `tests/conftest.py` | Explicitly skip four preserved tests requiring absent resources or embedded author paths / 明确标注四项受资源或历史路径限制的测试 |
| `pytest.ini` | Collect original and added tests; expose preserved modules without rewriting imports / 测试发现与原模块路径配置 |
| `.github/workflows/ci.yml` | Windows/Python 3.12 source, docs, unit and synthetic checks / 自动完整性、文档、单元及示例检查 |
| `.gitattributes` | Disable automatic line-ending conversion to preserve original SHA-256 / 禁用自动换行转换，保持原文件哈希 |
| `.gitignore` | Exclude environments, runs, official inputs, caches and secrets / 排除环境、生成结果、官方输入、缓存和秘密 |
| `source-manifest.json` | Map 94 preserved files to originals with SHA-256 / 94个保留原件的映射和哈希 |
| `data/resource-manifest.json` | Record nine externally supplied workbook sizes/hashes without embedding inputs / 九份外部资源的大小和哈希 |
| `docs/ARCHITECTURE.md` | Actual module/adapter cooperation and variant boundaries / 实际模块关系与版本边界 |
| `docs/RESOURCES.md` | Provenance, excluded materials and third-party conditions / 资源来源、排除范围和使用条件 |
| `docs/VALIDATION.md` | Executed checks, numerical comparisons and unverified scope / 实际验证与未验证范围 |
| `docs/FILES.md` | This complete release file guide / 本逐文件说明 |

## Preserved files / 保留原件

| File | Content / 内容 | Role and flow / 身份及关联 |
|---|---|
| [docs/assets/q1/图1_典型日负载光伏与电价.png](../docs/assets/q1/图1_典型日负载光伏与电价.png) | Recorded plot / 原图: 图1_典型日负载光伏与电价 | Team illustration / 队伍插图; assets |
| [docs/assets/q1/图3_储能电量轨迹与电价.png](../docs/assets/q1/图3_储能电量轨迹与电价.png) | Recorded plot / 原图: 图3_储能电量轨迹与电价 | Team illustration / 队伍插图; assets |
| [docs/assets/q1/图4_与无储能方案对比.png](../docs/assets/q1/图4_与无储能方案对比.png) | Recorded plot / 原图: 图4_与无储能方案对比 | Team illustration / 队伍插图; assets |
| [docs/feature_analysis/00_交接说明.md](../docs/feature_analysis/00_交接说明.md) | Historical documentation / 原说明: 问题 2 · 特征分析交接说明（交论文手） | Feature-analysis handover / 特征分析交接; feature_analysis |
| [docs/feature_analysis/01_特征分析结论.md](../docs/feature_analysis/01_特征分析结论.md) | Historical documentation / 原说明: 问题 2 · 特征分析结论（可直接写论文） | Feature-analysis handover / 特征分析交接; feature_analysis |
| [docs/feature_analysis/02_特征分析数值表.xlsx](../docs/feature_analysis/02_特征分析数值表.xlsx) | Workbook / 工作簿: 说明 (11×3), 表1_互信息 (7×3), 表2_偏相关 (6×3), 表3_负载ACF (16×3), 表4_负载周期图 (8×6), 表5_负载MSTL (7×2), 表6_尖峰诊断汇总 (9×3), 表7_光伏周期图 (4×4), 表8_光伏STL (7×2), 表9_逐日变异系数 (5×5), 表10_尖峰事件明细 (38×9) | Feature-analysis handover / 特征分析交接; feature_analysis |
| [docs/original/core_code_excerpt.md](../docs/original/core_code_excerpt.md) | Historical documentation / 原说明: 四问预测与优化核心代码汇总 | Extracted reading reference / 代码阅读摘录; original |
| [docs/original/q2/README.md](../docs/original/q2/README.md) | Historical documentation / 原说明: 问题二运行说明 | Historical method note / 原方法说明; original |
| [docs/original/q2/问题二_论文建模思路.md](../docs/original/q2/问题二_论文建模思路.md) | Historical documentation / 原说明: 问题二：逐日滚动预测与机会约束购电优化 | Historical method note / 原方法说明; original |
| [docs/original/q3/问题三_论文建模思路.md](../docs/original/q3/问题三_论文建模思路.md) | Historical documentation / 原说明: 问题三：含日内预报更新的多阶段购电策略 | Historical method note / 原方法说明; original |
| [docs/original/q4/问题四_EW耦合预测与优化_论文建模思路.md](../docs/original/q4/问题四_EW耦合预测与优化_论文建模思路.md) | Historical documentation / 原说明: 问题四：同类型 EW 电价基线—净负荷变化 Ridge 耦合预测与优化 | Historical method note / 原方法说明; original |
| [experiments/q1_v2/make_figures.py](../experiments/q1_v2/make_figures.py) | 问题1 论文插图：基于建模手的 solve_q1.py 求解结果重新绘制。; definitions: step_xy, fmt_time_axis, panel_label, save, fig_inputs, fig_balance, phase_runs, fig_soc, fig_compare | Distinct historical algorithm / 历史算法版本 |
| [experiments/q1_v2/sensitivity_q1.py](../experiments/q1_v2/sensitivity_q1.py) | 问题1 敏感性分析：初始储电量、充放电效率及效率口径。; definitions: solve_general | Distinct historical algorithm / 历史算法版本 |
| [experiments/q1_v2/solve_q1.py](../experiments/q1_v2/solve_q1.py) | 2026 年国赛 C 题问题 1：微网计划购电优化。; definitions: DispatchData, DispatchSolution, _normalise_end_time, interval_labels_from_end_times, interval_plot_coordinates, load_attachment1, solve_dispatch, validate_solution, build_summary, _set_chinese_plot_style, export_workbook, plot_overview… | Distinct historical algorithm / 历史算法版本 |
| [experiments/q1_v2/test_solve_q1.py](../experiments/q1_v2/test_solve_q1.py) | test_solve_q1; definitions: TestQuestion1Solver | Distinct historical algorithm / 历史算法版本 |
| [experiments/q1_v2/数学模型.md](../experiments/q1_v2/数学模型.md) | Historical documentation / 原说明: 数学模型（问题1） | Distinct historical algorithm / 历史算法版本 |
| [experiments/q1_v2/问题1_关键指标.json](../experiments/q1_v2/问题1_关键指标.json) | Recorded JSON / 原记录; keys: solver_status, solver_message, periods, total_cost_yuan, total_purchase_q_kwh, q_to_load_kwh, q_to_storage_kwh, total_load_kwh, total_pv_available_kwh, total_pv_used_kwh | Distinct historical algorithm / 历史算法版本 |
| [experiments/q1_v2/问题1_敏感性分析.json](../experiments/q1_v2/问题1_敏感性分析.json) | Recorded JSON / 原记录; keys: baseline, S0, S0_free, eta_symmetric, eta_definition | Distinct historical algorithm / 历史算法版本 |
| [experiments/q1_v2/问题1_论文材料包.md](../experiments/q1_v2/问题1_论文材料包.md) | Historical documentation / 原说明: 问题1 论文材料包（交论文手） | Distinct historical algorithm / 历史算法版本 |
| [experiments/q3_archive/问题3_求解_旧版.ipynb](../experiments/q3_archive/问题3_求解_旧版.ipynb) | Notebook: 7 code cells, 8 text cells; source/saved outputs preserved / 原代码与已有输出保留 | Distinct historical algorithm / 历史算法版本 |
| [experiments/q3_archive/问题三_论文建模思路_修改前备份.md](../experiments/q3_archive/问题三_论文建模思路_修改前备份.md) | Historical documentation / 原说明: 问题三：含日内预报更新的多阶段购电策略 | Distinct historical algorithm / 历史算法版本 |
| [experiments/q3_archive/问题三_论文建模思路_阶段递推版备份.md](../experiments/q3_archive/问题三_论文建模思路_阶段递推版备份.md) | Historical documentation / 原说明: 问题三：含日内预报更新的多阶段购电策略 | Distinct historical algorithm / 历史算法版本 |
| [experiments/q3_archive/问题三_预测与优化_修改前备份.ipynb](../experiments/q3_archive/问题三_预测与优化_修改前备份.ipynb) | Notebook: 9 code cells, 11 text cells; source/saved outputs preserved / 原代码与已有输出保留 | Distinct historical algorithm / 历史算法版本 |
| [experiments/q3_archive/问题三_预测与优化_阶段递推版备份.ipynb](../experiments/q3_archive/问题三_预测与优化_阶段递推版备份.ipynb) | Notebook: 9 code cells, 11 text cells; source/saved outputs preserved / 原代码与已有输出保留 | Distinct historical algorithm / 历史算法版本 |
| [results/reference/final/result1.xlsx](../results/reference/final/result1.xlsx) | Workbook / 工作簿: 计划购电量 (145×146), 充放电量 (7×5) | Recorded reference output / 原参考产物; reference |
| [results/reference/final/result2.xlsx](../results/reference/final/result2.xlsx) | Workbook / 工作簿: 计划购电量 (335×147), 充放电量 (2005×6), 紧急购电量 (1003×3) | Recorded reference output / 原参考产物; reference |
| [results/reference/final/result3.xlsx](../results/reference/final/result3.xlsx) | Workbook / 工作簿: 计划购电量 (335×147), 调整购电量 (335×147), 充放电量 (2005×6), 紧急购电量 (1003×3) | Recorded reference output / 原参考产物; reference |
| [results/reference/final/result4-2.xlsx](../results/reference/final/result4-2.xlsx) | Workbook / 工作簿: 计划购电量 (335×147), 充放电量 (2005×6), 紧急购电量 (1003×3) | Recorded reference output / 原参考产物; reference |
| [results/reference/final/result4-3.xlsx](../results/reference/final/result4-3.xlsx) | Workbook / 工作簿: 计划购电量 (335×147), 调整购电量 (335×147), 充放电量 (2005×6), 紧急购电量 (1003×3) | Recorded reference output / 原参考产物; reference |
| [results/reference/final/交付验证.json](../results/reference/final/交付验证.json) | Recorded JSON / 原记录; keys: result1, result2, result3, result4-2, result4-3, q2_lp_all_success, q2_soc_bounds, q2_soc_continuity, required_tables_exists | Recorded reference output / 原参考产物; reference |
| [results/reference/final/残差清理报告.json](../results/reference/final/残差清理报告.json) | Recorded JSON / 原记录; keys: result1, result2, result3, result4-2, result4-3 | Recorded reference output / 原参考产物; reference |
| [results/reference/final/深度校验.json](../results/reference/final/深度校验.json) | Recorded JSON / 原记录; keys: result1, result2, result3, result4-2, result4-3, all_checks_passed | Recorded reference output / 原参考产物; reference |
| [results/reference/final/问题4独立运行验证.json](../results/reference/final/问题4独立运行验证.json) | Recorded JSON / 原记录; keys: checks, cost_q42, cost_q43 | Recorded reference output / 原参考产物; reference |
| [results/reference/final/题目要求汇总表.xlsx](../results/reference/final/题目要求汇总表.xlsx) | Workbook / 工作簿: 填写说明 (6×2), 表1_购电量 (26×11), 表2_充放电 (18×16), 表3_紧急购电 (17×4) | Recorded reference output / 原参考产物; reference |
| [results/reference/q1/result1_验证.json](../results/reference/q1/result1_验证.json) | Recorded JSON / 原记录; keys: output, solver_status, periods, total_purchase_kWh, total_cost_yuan, max_constraint_residual_kWh, time_slot_rule, power_limit_assumption | Recorded reference output / 原参考产物; Q1 |
| [results/reference/q2/2至12月_CCP费用对比.csv](../results/reference/q2/2至12月_CCP费用对比.csv) | 4 rows / 行; columns: 模型, 计划购电费_万元, 紧急购电费_万元, 其中惩罚增量_万元, 总费用_万元, 紧急购电量_kWh, 惩罚天数, 优化失败天数, 相对最低总费用_% | Recorded reference output / 原参考产物; Q2 |
| [results/reference/q2/2至12月_事后模型评价.csv](../results/reference/q2/2至12月_事后模型评价.csv) | 4 rows / 行; columns: 模型, 逐时段RMSE, 平均日电量绝对误差, 平均日Pinball损失, 平均最大累计缺口, 最大累计缺口P95 | Recorded reference output / 原参考产物; Q2 |
| [results/reference/q2/一月EW_EWMA净负荷残差分布.png](../results/reference/q2/一月EW_EWMA净负荷残差分布.png) | Recorded plot / 原图: 一月EW_EWMA净负荷残差分布 | Recorded reference output / 原参考产物; Q2 |
| [results/reference/q2/一月模型评价.csv](../results/reference/q2/一月模型评价.csv) | 4 rows / 行; columns: 模型, 逐时段RMSE, 平均日电量绝对误差, 平均日Pinball损失, 平均最大累计缺口, 最大累计缺口P95 | Recorded reference output / 原参考产物; Q2 |
| [results/reference/q2/数据质量摘要.csv](../results/reference/q2/数据质量摘要.csv) | 5 rows / 行; columns: 项目, 结果 | Recorded reference output / 原参考产物; Q2 |
| [results/reference/q2/模型评价与费用对比.png](../results/reference/q2/模型评价与费用对比.png) | Recorded plot / 原图: 模型评价与费用对比 | Recorded reference output / 原参考产物; Q2 |
| [results/reference/q3/图表/问题三_典型日四阶段调整图.png](../results/reference/q3/图表/问题三_典型日四阶段调整图.png) | Recorded plot / 原图: 问题三_典型日四阶段调整图 | Recorded reference output / 原参考产物; Q3 |
| [results/reference/q3/图表/问题三_典型日四阶段调整图.svg](../results/reference/q3/图表/问题三_典型日四阶段调整图.svg) | Recorded plot / 原图: 问题三_典型日四阶段调整图 | Recorded reference output / 原参考产物; Q3 |
| [results/reference/q3/图表/问题三_卡尔曼增益曲线.png](../results/reference/q3/图表/问题三_卡尔曼增益曲线.png) | Recorded plot / 原图: 问题三_卡尔曼增益曲线 | Recorded reference output / 原参考产物; Q3 |
| [results/reference/q3/图表/问题三_卡尔曼增益曲线.svg](../results/reference/q3/图表/问题三_卡尔曼增益曲线.svg) | Recorded plot / 原图: 问题三_卡尔曼增益曲线 | Recorded reference output / 原参考产物; Q3 |
| [results/reference/q3/图表/问题三_预报误差随提前时长.png](../results/reference/q3/图表/问题三_预报误差随提前时长.png) | Recorded plot / 原图: 问题三_预报误差随提前时长 | Recorded reference output / 原参考产物; Q3 |
| [results/reference/q3/图表/问题三_预报误差随提前时长.svg](../results/reference/q3/图表/问题三_预报误差随提前时长.svg) | Recorded plot / 原图: 问题三_预报误差随提前时长 | Recorded reference output / 原参考产物; Q3 |
| [results/reference/q4/EW一月选参.csv](../results/reference/q4/EW一月选参.csv) | 9 rows / 行; columns: 历史同类型日数N, 衰减系数lambda, 一月14—31日MAE, 一月14—31日RMSE | Recorded reference output / 原参考产物; Q4 |
| [results/reference/q4/EW与7日基线_优化费用对比.csv](../results/reference/q4/EW与7日基线_优化费用对比.csv) | 4 rows / 行; columns: 方案, 价格模型, 总费用_元, 相对旧模型节省_元 | Recorded reference output / 原参考产物; Q4 |
| [results/reference/q4/EW价格预测指标.csv](../results/reference/q4/EW价格预测指标.csv) | 2 rows / 行; columns: 评价期, 同类型EW_Ridge_MAE, 同类型EW_Ridge_RMSE | Recorded reference output / 原参考产物; Q4 |
| [results/reference/q4/EW方案运行验证.json](../results/reference/q4/EW方案运行验证.json) | Recorded JSON / 原记录; keys: same_type_price_ew, selection_uses_january_only, q2_lp_all_success, q3_lp_all_success, q2_soc_bounds, q3_soc_bounds, q2_soc_continuity, q3_soc_continuity, q2_cost_identity, q3_cost_identity | Recorded reference output / 原参考产物; Q4 |
| [results/reference/q4/EW费用核验.json](../results/reference/q4/EW费用核验.json) | Recorded JSON / 原记录; keys: cost_q42, cost_q43, emergency_kwh_q42, emergency_kwh_q43 | Recorded reference output / 原参考产物; Q4 |
| [results/reference/q4/一月价格模型选参.csv](../results/reference/q4/一月价格模型选参.csv) | 5 rows / 行; columns: gamma, 一月14—31日MAE | Recorded reference output / 原参考产物; Q4 |
| [results/reference/q4/价格预测指标.csv](../results/reference/q4/价格预测指标.csv) | 2 rows / 行; columns: 评价期, lag7_MAE, 耦合预测_MAE, 耦合预测_RMSE | Recorded reference output / 原参考产物; Q4 |
| [results/reference/q4/偏相关指标.csv](../results/reference/q4/偏相关指标.csv) | 2 rows / 行; columns: 范围, raw_pearson, raw_spearman, partial_pearson, partial_spearman, ci_low, ci_high, bootstrap_days | Recorded reference output / 原参考产物; Q4 |
| [results/reference/q4/图表/问题四_EW与7日基线费用对比.png](../results/reference/q4/图表/问题四_EW与7日基线费用对比.png) | Recorded plot / 原图: 问题四_EW与7日基线费用对比 | Recorded reference output / 原参考产物; Q4 |
| [results/reference/q4/图表/问题四_一月电价分类型日内分布.png](../results/reference/q4/图表/问题四_一月电价分类型日内分布.png) | Recorded plot / 原图: 问题四_一月电价分类型日内分布 | Recorded reference output / 原参考产物; Q4 |
| [results/reference/q4/图表/问题四_一月电价分类型日内分布.svg](../results/reference/q4/图表/问题四_一月电价分类型日内分布.svg) | Recorded plot / 原图: 问题四_一月电价分类型日内分布 | Recorded reference output / 原参考产物; Q4 |
| [results/reference/q4/图表/问题四_一月电价分类型日内分布_双图无编号.png](../results/reference/q4/图表/问题四_一月电价分类型日内分布_双图无编号.png) | Recorded plot / 原图: 问题四_一月电价分类型日内分布_双图无编号 | Recorded reference output / 原参考产物; Q4 |
| [results/reference/q4/图表/问题四_一月电价分类型日内分布_双图无编号.svg](../results/reference/q4/图表/问题四_一月电价分类型日内分布_双图无编号.svg) | Recorded plot / 原图: 问题四_一月电价分类型日内分布_双图无编号 | Recorded reference output / 原参考产物; Q4 |
| [results/reference/q4/图表/问题四_一月电价日内分布.png](../results/reference/q4/图表/问题四_一月电价日内分布.png) | Recorded plot / 原图: 问题四_一月电价日内分布 | Recorded reference output / 原参考产物; Q4 |
| [results/reference/q4/图表/问题四_一月电价日内分布.svg](../results/reference/q4/图表/问题四_一月电价日内分布.svg) | Recorded plot / 原图: 问题四_一月电价日内分布 | Recorded reference output / 原参考产物; Q4 |
| [results/reference/q4/图表/问题四_一月电价日内分布_验证.json](../results/reference/q4/图表/问题四_一月电价日内分布_验证.json) | Recorded JSON / 原记录; keys: input_shape, days, slots_per_day, min_yuan_per_kWh, max_yuan_per_kWh, mean_yuan_per_kWh, font, png, svg, typed_png | Recorded reference output / 原参考产物; Q4 |
| [results/reference/q4/图表/问题四_典型日电价预测.png](../results/reference/q4/图表/问题四_典型日电价预测.png) | Recorded plot / 原图: 问题四_典型日电价预测 | Recorded reference output / 原参考产物; Q4 |
| [results/reference/q4/图表/问题四_典型日电价预测.svg](../results/reference/q4/图表/问题四_典型日电价预测.svg) | Recorded plot / 原图: 问题四_典型日电价预测 | Recorded reference output / 原参考产物; Q4 |
| [results/reference/q4/图表/问题四_费用构成.png](../results/reference/q4/图表/问题四_费用构成.png) | Recorded plot / 原图: 问题四_费用构成 | Recorded reference output / 原参考产物; Q4 |
| [results/reference/q4/图表/问题四_费用构成.svg](../results/reference/q4/图表/问题四_费用构成.svg) | Recorded plot / 原图: 问题四_费用构成 | Recorded reference output / 原参考产物; Q4 |
| [results/reference/q4/运行验证.json](../results/reference/q4/运行验证.json) | Recorded JSON / 原记录; keys: price_gamma, ridge_alpha, q2_lp_all_success, q3_lp_all_success, q2_soc_bounds, q3_soc_bounds, q2_soc_continuity, q3_soc_continuity, q2_cost_identity, q2_terminal_soc_at_lower_share | Recorded reference output / 原参考产物; Q4 |
| [results/reference/q4/问题四_gamma平行消融.csv](../results/reference/q4/问题四_gamma平行消融.csv) | 4 rows / 行; columns: 方案, gamma, 价格方案, 总费用_元, 相对lag7节省_元 | Recorded reference output / 原参考产物; Q4 |
| [results/reference/q4/问题四_同类型EW费用明细.csv](../results/reference/q4/问题四_同类型EW费用明细.csv) | 8 rows / 行; columns: 方案, 费用项, 金额_元, 金额_万元 | Recorded reference output / 原参考产物; Q4 |
| [results/reference/q4/问题四_费用与求解指标.csv](../results/reference/q4/问题四_费用与求解指标.csv) | 2 rows / 行; columns: 方案, 价格方案, 计划购电费_元, 紧急购电费_元, 总费用_元, 紧急购电量_kWh, LP成功数, 调增费_元, 调减退费_元 | Recorded reference output / 原参考产物; Q4 |
| [src/delivery/build_final_answers.py](../src/delivery/build_final_answers.py) | 生成并核验2026国赛C题的5个官方结果文件与题目指定汇总表。; definitions: as_date, interval_label, contiguous_emergency, fill_dense_plan_sheet, fill_storage_sheet, fill_emergency_sheet, build_result2, read_emergency_matrix, copy_and_normalize, workbook_summary, build_required_tables, validate_result… | Preserved main source/test / 原主程序或测试; delivery |
| [src/delivery/clean_tiny_residuals.py](../src/delivery/clean_tiny_residuals.py) | 清理交付工作簿中的LP数值残差（\|v\|<1e-9 视为0），并同步重算全天购电量列。; definitions: main | Preserved main source/test / 原主程序或测试; delivery |
| [src/delivery/deep_validate.py](../src/delivery/deep_validate.py) | 对最终5个官方工作簿做结构、时间、数值和储能约束深度校验。; definitions: dval, finite_nonneg, compare_headers, plan_check, storage_check, emergency_check, main | Preserved main source/test / 原主程序或测试; delivery |
| [src/delivery/verify_q4_runtime.py](../src/delivery/verify_q4_runtime.py) | 独立运行并核验问题4最终EW方案，不改写原项目文件。; definitions: plan_matrix, main | Preserved main source/test / 原主程序或测试; delivery |
| [src/q1/build_result1.py](../src/q1/build_result1.py) | 按官方模板填写问题1 result1.xlsx，并核验时间槽与约束。; definitions: fill_result1, main | Preserved main source/test / 原主程序或测试; q1 |
| [src/q1/solve_q1.py](../src/q1/solve_q1.py) | 2026 年国赛 C 题问题 1：微网计划购电优化。; definitions: DispatchData, DispatchSolution, _normalise_end_time, interval_labels_from_end_times, interval_plot_coordinates, load_attachment1, solve_dispatch, validate_solution, build_summary, _set_chinese_plot_style, export_workbook, plot_overview… | Preserved main source/test / 原主程序或测试; q1 |
| [src/q1/test_solve_q1.py](../src/q1/test_solve_q1.py) | test_solve_q1; definitions: TestQuestion1Solver | Preserved main source/test / 原主程序或测试; q1 |
| [src/q2/build_notebook.py](../src/q2/build_notebook.py) | build_notebook; definitions:  | Preserved main source/test / 原主程序或测试; q2 |
| [src/q2/q2_pipeline.py](../src/q2/q2_pipeline.py) | q2_pipeline; definitions: read_csv_auto, to_daily_matrices, load_project_data, low_load_day, _date_features, build_features_for_day, _training_xy, make_model, _force_nonnegative, rolling_ml_forecasts, _original_ridge_fourier, _original_ridge_same_type_mean… | Preserved main source/test / 原主程序或测试; q2 |
| [src/q2/tests/test_q2_pipeline.py](../src/q2/tests/test_q2_pipeline.py) | test_q2_pipeline; definitions: TestQ2Pipeline | Preserved main source/test / 原主程序或测试; q2 |
| [src/q2/问题二_逐日滚动预测与CCP优化.ipynb](../src/q2/问题二_逐日滚动预测与CCP优化.ipynb) | Notebook: 7 code cells, 9 text cells; source/saved outputs preserved / 原代码与已有输出保留 | Preserved main source/test / 原主程序或测试; q2 |
| [src/q3/问题三_预测与优化.ipynb](../src/q3/问题三_预测与优化.ipynb) | Notebook: 9 code cells, 11 text cells; source/saved outputs preserved / 原代码与已有输出保留 | Preserved main source/test / 原主程序或测试; q3 |
| [src/q4/build_final_ew_notebook.py](../src/q4/build_final_ew_notebook.py) | build_final_ew_notebook; definitions:  | Preserved main source/test / 原主程序或测试; q4 |
| [src/q4/build_notebook.py](../src/q4/build_notebook.py) | build_notebook; definitions:  | Preserved main source/test / 原主程序或测试; q4 |
| [src/q4/draw_january_price_profile.py](../src/q4/draw_january_price_profile.py) | 绘制2025年1月电价的日内分布（31条逐日曲线+中位数/IQR）。; definitions: choose_chinese_font, main | Preserved main source/test / 原主程序或测试; q4 |
| [src/q4/draw_january_price_profile_two_panel.py](../src/q4/draw_january_price_profile_two_panel.py) | 绘制问题四1月电价两类日型双面板图（无图号、无(a)(b)）。; definitions:  | Preserved main source/test / 原主程序或测试; q4 |
| [src/q4/q4_ew_compare.py](../src/q4/q4_ew_compare.py) | q4_ew_compare; definitions: ew_history_profile, ew_coupled_price_forecast, EWPriceEngine, price_metrics, select_ew_parameters, run_compare | Preserved main source/test / 原主程序或测试; q4 |
| [src/q4/q4_pipeline.py](../src/q4/q4_pipeline.py) | q4_pipeline; definitions: DataBundle, load_official_data, low_load_day, _weights, ew_day, ew_net48, _default_historical_net_hat, _fit_price_correction, coupled_price_forecast, select_price_gamma, price_metrics, _controls… | Preserved main source/test / 原主程序或测试; q4 |
| [src/q4/refresh_q4_figures.py](../src/q4/refresh_q4_figures.py) | 用同类型EW方案的结果刷新问题四图表与费用明细，不重跑LP。; definitions: plan_matrix, emergency_matrix, main | Preserved main source/test / 原主程序或测试; q4 |
| [src/q4/tests/test_q4_ew_compare.py](../src/q4/tests/test_q4_ew_compare.py) | test_q4_ew_compare; definitions: synthetic, test_ew_profile_uses_only_values_before_release_for_full_48h, test_ew_profile_uses_same_load_type_days, test_ew_coupled_price_forecast_is_future_blind | Preserved main source/test / 原主程序或测试; q4 |
| [src/q4/tests/test_q4_pipeline.py](../src/q4/tests/test_q4_pipeline.py) | test_q4_pipeline; definitions: synthetic_history, test_price_forecast_is_strictly_history_only, test_january_selection_only_compares_declared_shrinkage_grid, test_future_netload_update_changes_price_forecast_not_history_fit, test_partial_dependence_returns_computed_ci_and_large_residual_relation, test_stage_optimizer_requires_exact_48_hours_and_respects_soc, test_q2_solver_preserves_load_pv_split_and_48h_contract, test_settlement_soc_continuity_and_cost_identities, test_ablation_table_reports_parallel_lag7_and_coupled_savings, test_filled_workbooks_match_templates_and_have_no_blanks | Preserved main source/test / 原主程序或测试; q4 |
| [src/q4/问题四_EW耦合预测与优化.ipynb](../src/q4/问题四_EW耦合预测与优化.ipynb) | Notebook: 9 code cells, 14 text cells; source/saved outputs preserved / 原代码与已有输出保留 | Preserved main source/test / 原主程序或测试; q4 |
| [src/q4/问题四_波动电价耦合预测与优化.ipynb](../src/q4/问题四_波动电价耦合预测与优化.ipynb) | Notebook: 5 code cells, 9 text cells; source/saved outputs preserved / 原代码与已有输出保留 | Preserved main source/test / 原主程序或测试; q4 |
