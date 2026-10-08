# Resources and release scope / 资源与发布范围

## Required external resources

The local team archive identifies its input as CUMCM 2026 Problem C. The competition's website is [mcm.edu.cn](https://www.mcm.edu.cn/). A specific public download and redistribution grant for this supplied bundle have **not** been established by this release. Obtain the exact attachments through the competition organizers or the team's authorized copy; access may depend on their distribution policy. We do not promise that a public download is available or free, and this project performs no purchase.

队伍本地归档把输入标为2026国赛C题，赛事网站为上述链接。本次没有确认该附件包的具体公共下载入口和再分发许可。请从组织方或队伍合法副本取得相同附件；取得条件以发布方为准，不承诺公开可下载或免费，不代用户购买。

`data/resource-manifest.json` records nine original Excel files with exact byte sizes and SHA-256. The four inputs contain typical-day load/PV/prices, annual actual load/PV, hourly **PV power forecasts**, and annual prices. The five templates define output sheets. Put them under the layout in the README or pass an external directory. `check-resources` validates all nine before reproduction; converted CSVs are generated from this verified bundle inside `runs/`.

资源清单记录四份原输入及五个结果模板的大小和哈希。附件3是小时级光伏功率预报。统一入口先检查九个哈希，再在 `runs/` 中生成所需CSV；不改原Excel。

Times denote interval ends: `2025-02-01 00:00` belongs to January 31's last ten minutes. One year's data has 365×144 slots. Forecast release timestamps remain distinct from target timestamps; never deduplicate multiple releases merely by target hour.

时刻是区间终点，二月1日0点属于一月31日最后十分钟；全年365×144点。同一目标时刻可能有不同发布时刻的预报，不能只按目标时刻去重。

## Included team artifacts

- Preserved primary code, notebook sources/saved outputs and tests.
- Five final workbook references and the requested-date summary workbook.
- Archived numerical metrics, plots, method notes and feature-analysis handover.
- Q1 v2 and Q3 archived variants retained as distinct experiments.

保留主代码、Notebook和测试、六份结果工作簿、指标/图表/方法与特征交接材料，以及有意义的历史算法版本。结果是团队产物，原输入单独获取；发布许可不扩展至第三方材料。

## Excluded from the public repository

Official problem PDFs, input spreadsheets/derived raw-input CSVs, third-party research papers and textbooks, generic third-party LaTeX templates, administrative registration spreadsheets, signed/named commitment forms, teacher screenshots, AI chat exports, editor locks, interpreter/test caches, duplicate ZIP snapshots, and the unfinished paper PDF are not published. Original files remain in the local project and its external backup. Exclusion is not deletion.

未公开官方题面/输入及转换输入CSV、第三方文献/教材/模板、报名与承诺书、老师截图、AI对话、锁文件/缓存、重复压缩包和未定稿论文。它们仍在本地原目录及外部备份中，未删除。

The original paper contains a placeholder title, an incorrect Q3 percentage and an older Q4 results table. Its statements must not supersede current reference data. Q3 cost reduction relative to Q2 is about **484,868.64 CNY (3.56%)**, not 48.48%. Q4 final total costs are the values listed in both READMEs. Reference docs may retain editing remarks; they are labeled original rather than presented as polished current instructions.

原稿有标题占位、第三问百分比错误和旧第四问表格。第三问相对第二问节省约484868.64元（3.56%），不是48.48%。最终第四问费用以双语README与参考数据为准，保留原说明仅作追溯。

## Resource use conditions

External official resources and third-party literature retain the owners' original terms. This release contains no grant to redistribute them. Dependency licenses remain with their respective projects. The owner's project-license choice applies only to the authorized team code/documents/artifacts to which that license is applicable.

官方资源和第三方文献保留原权利条件；本项目不给予再分发许可。依赖遵循各自许可证，项目许可证仅适用于有权授权的团队材料。
