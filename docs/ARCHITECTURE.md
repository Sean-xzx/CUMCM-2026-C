# Architecture / 架构

The release preserves original algorithms and reference outputs byte-for-byte. `source-manifest.json` records all copied files, their former relative paths, role, and SHA-256. `check-sources` verifies this baseline. The manifest is provenance/integrity evidence, not permission to redistribute third-party resources.

公开副本保留原算法与参考结果字节，清单记录原路径、身份与哈希；完整性清单不代替第三方资源授权。

| Stage | Original implementation | Portable integration |
|---|---|---|
| Q1 | `src/q1/solve_q1.py`, `build_result1.py` | Call `fill_result1` with explicit input/template/output |
| Q2 | `src/q2/q2_pipeline.py` | Original `src/delivery/build_final_answers.py::build_result2`; set its directory globals, derive input CSV schema from verified Excel |
| Q3 | Main notebook under `src/q3` | Stage unchanged Excel inputs and template; execute original cells 2, 16, 18 and original `simulate`/`cost` functions |
| Q4 | `src/q4/q4_pipeline.py`, `q4_ew_compare.py` | Call unchanged `run_compare(base=..., out_dir=...)`; old archived fees serve only as comparison baseline |
| Delivery | `build_final_answers.py` | Call original `copy_and_normalize`; do not modify committed reference workbooks |

Q3 cell identifiers are deliberately tied to the preserved notebook hash; changing its cell layout invalidates the source check. Q3's recorded parameters are used by default; `--select-q3` reruns the original January selection. Q4 always reselects its January EW parameters. Algorithms are not rewritten in the adapter. Temporary generated CSVs, copied inputs and output workbooks remain in ignored `runs/`.

第三问适配层依赖原 Notebook 的单元编号与哈希；默认用冻结参数，可选择重做一月选参。第四问重新执行一月 EW 选参。CSV转换、资源暂存与新结果写入忽略的 `runs/`，不覆盖原资源。

Q2 and Q3's principles reappear independently in Q4. Changing Q2 alone does not automatically alter the later independent implementations. Q1 v2 uses different result attribute names from the current Q1 template filler; it is retained under `experiments/`, not substituted into the main pipeline. Q3's archived stage-recursive comparison is a different method from the final fixed-midnight target and must not be mixed into the final results.

各问有独立实现；仅改一份代码不保证后续同步。第一问v2的字段与当前模板填报函数不同，第三问阶段递推备份也不同于最终固定0点基准，均作为实验保留。

Original `build_notebook.py`, drawing utilities, validation scripts and notebook default paths remain available as historical source. The portable CLI covers the validated numerical path; it does not claim that every historical helper can be run unchanged at any path. No real grid API, secret configuration, model weights or external account is involved.

原辅助脚本保留历史路径，不声称所有辅助入口均无需配置。已验证的是统一数值入口；不需要真实电网接口、秘密配置、模型权重或外部账号。
