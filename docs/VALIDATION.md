# Validation evidence / 验证记录

Verification date: 2026-10-08 (Asia/Shanghai). Local platform: Windows, CPython 3.12.14, CPU, a newly created virtual environment with the committed full dependency lock. No global site packages, external services, GPU or private model credentials were used. Official inputs were separately supplied and matched all nine resource hashes.

验证日期为2026-10-08（上海时区）。本地环境为Windows、CPython 3.12.14、CPU和新建虚拟环境，使用仓库完整依赖锁；不依赖全局包、外部服务、GPU或私人模型凭据。官方输入另行提供，九个文件哈希全部匹配。

## Baseline and integrity / 原行为与完整性

Before integration, the four original test files produced **27 passed, 1 failed**. The failure was the final workbook/template test referring to a nonexistent author-specific absolute directory. It was a path/resource failure, not evidence of a failed optimization. All 94 copied original files, including algorithms, tests, method notes and reference artifacts, match their original SHA-256 hashes. No core algorithm/data/reference workbook was rewritten; portable behavior is provided by the added adapter.

整理前四份原测试得到27项通过、1项失败；失败来自作者电脑的固定目录不存在，并非优化失败。94份保留原件的哈希全部一致；核心算法、数据和参考工作簿未改写，新增适配层提供路径配置。

The portable suite has **30 passed, 4 explicitly skipped**. Skipped original tests are:

- `test_real_attachment_has_144_intervals_and_converts_kw_to_kwh`
- `test_pipeline_creates_verified_workbook_json_and_png_files`
- `test_original_ridge_reproduces_existing_notebook`
- `test_filled_workbooks_match_templates_and_have_no_blanks`

These four tests require absent public resources or preserved absolute paths. Public CI does not disguise them as passes. The final EW annual computation and exported workbooks were separately verified locally; the original lag-7 Ridge annual baseline and historical Q1 drawing-helper execution were not rerun by the portable suite.

四项原测试需要未公开资源或历史绝对路径，在公共CI中明确跳过。最终EW全年计算和结果表另行在本地验证；旧7日Ridge全年基线及第一问历史绘图入口未由新测试套件重跑。单元套件通过不代表这四项原测试通过。

## Executed numerical workflow / 实际数值流程

The README synthetic demo ran the real preserved Q1 and shared 48-hour solvers, exported Excel/CSV/JSON, returned `Optimal`, 144 slots, 3206.6449614242956 CNY, and terminal SOC 6000 kWh. Missing-resource input produced exit code 2 with an explicit error before creating output files.

README示例实际调用原求解器，生成Excel/CSV/JSON，得到上述费用和末端储电量；缺失资源返回明确错误及退出码2，未写出伪结果。

All four selected production numerical paths were executed against the hash-verified official bundle. Each annual case covers 2025-02-01 through 2025-12-31 (334 days). Q3 used frozen parameters `A0=0.6, ALO=0.7, AHI=0.9`. Q4 reselected N=8, decay=0.8 using January only, then recomputed the final Q4-2 and Q4-3 EW schemes.

四问当前数值路径均使用哈希验证后的官方附件实际执行；全年区间为2025-02-01至12-31，共334天。第三问使用冻结参数；第四问重新执行一月选参，选出N=8、衰减0.8，并重算最终两个EW方案。

| Case / 问题 | Recomputed total / 重算总费用 (CNY) | Maximum planned/adjusted purchase difference / 最大购电量差 (kWh) |
|---|---:|---:|
| Q1 | 35,126.94858928964 | 0 |
| Q2 | 13,634,329.584093768 | 0 |
| Q3 | 13,149,460.948547978 | 1.023181539494544e-11 |
| Q4-2 | 14,308,775.528818106 | 0 |
| Q4-3 | 13,854,618.27909321 | 8.86757334228605e-12 |

The purchase comparison tolerance is 1e-4 kWh; total costs match recorded values within 1e-4 CNY (the Q2 sum differs by about 1.1e-8 CNY). This is numerical reproduction, not byte-identical Excel ZIP generation. `verify` also checks headers/time labels, annual dates and daily totals, exported charging/discharging limits, endpoint SOC bounds, daily SOC continuity, and emergency-row structure using the preserved validation functions. Exported four-hour totals/endpoints are not proof of every underlying ten-minute constraint; Q4's runtime checks additionally verify all simulated SOC values and LP success.

购电量容限为1e-4 kWh，总费用在1e-4元内一致；第二问求和差约1.1e-8元。核对还复用原校验函数检查表头/时间标签、日期/每日合计、充放电汇总边界、端点SOC、跨日连续性和紧急购电结构。四小时汇总/端点不能证明所有十分钟约束；第四问运行时另检查全部模拟SOC和LP状态。Excel压缩元信息不同不影响数值复现判断。

Q4's ten runtime checks all returned true: same-type scheme and January selection flags, both LP-success checks, both SOC-bound checks, both continuity checks, and both settlement identities. The first two flags are descriptive constants in the original code; original unit tests separately exercise historical-input boundaries. Recomputed price MAE/RMSE: January 0.029511374495434818 / 0.037666477432578324; February–December 0.03603407323629374 / 0.049445856513005836.

第四问原运行校验十项均为真。前两项方案/选参标记是原代码中的说明性常量；历史信息边界另由原单元测试检验。电价MAE/RMSE如上，与参考记录一致。

Q3 + Q4 together took **1211.25 seconds** on this machine. Q1/Q2 were completed in an earlier invocation; their combined timing was not reliably retained. This is an observed duration, not a hardware performance promise. A first invocation hit a Windows output-encoding error after Q2; the new adapter now sets UTF-8 output, and Q3/Q4 were rerun successfully. Original source files were unaffected.

本机第三、四问合计1211.25秒；前两问已在前一轮完成，其合计耗时未可靠保留。首次运行在第二问结束后遇到Windows输出编码问题，新增入口改为UTF-8后第三、四问成功重跑，未改原代码。耗时不作为硬件性能承诺。

## Limits of the evidence / 验证边界

Not rerun: Q3's 16-combination January search (`--select-q3`), full Ridge/XGBoost/GRU benchmark training, historical alternative algorithms, every plotting/notebook-building helper, the old Q4 lag-7 annual baseline, or the unfinished paper build. Saved benchmark results/figures remain historical artifacts. Q4 comparisons read the old baseline costs from the preserved reference CSV rather than recomputing that baseline. Linux/macOS and other Python versions remain unverified. No statistical confidence interval is claimed for stochastic model retraining.

未重跑第三问16组选参、完整Ridge/XGBoost/GRU训练、历史变体、全部绘图/Notebook构建入口、第四问旧7日全年基线或未定稿论文构建。已有对照指标/图表是历史产物，旧费用从原CSV读取；其他系统和Python版本未验证，不声称随机模型重训的统计误差范围。

GitHub CI intentionally uses synthetic data and available unit tests, not private official resources. Remote publication and a clean-clone run are verified during delivery; their commit and CI status are reported in the delivery record rather than assumed from this local test evidence.

GitHub自动检查使用合成数据与可运行单元测试，不使用私人官方资源。远程发布、干净克隆和CI状态在交付时另行核实，不由本地通过推定远程成功。

The added negative test changes an exported SOC endpoint to 0 kWh and confirms that verification rejects it. / 新增错误输入测试把输出SOC端点改为0 kWh，确认校验拒绝越界结果。
