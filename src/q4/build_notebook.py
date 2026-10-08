from pathlib import Path
import nbformat as nbf

nb=nbf.v4.new_notebook()
nb["metadata"]={"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"},"language_info":{"name":"python","version":"3.11"}}
nb["cells"]=[
 nbf.v4.new_markdown_cell(r"""# 问题四：波动电价耦合预测与优化

本Notebook可从头执行。问题4-2的EW/EWMA净负荷、机会约束、储能与结算口径**与问题二一致**；问题4-3的卡尔曼融合、固定基准不调整带和四阶段48小时优化**与问题三一致**。本问只新增偏相关诊断、无泄漏电价预测，以及“预测价规划、真实价结算”。"""),
 nbf.v4.new_markdown_cell(r"""## 1 信息边界与单向耦合

在决策时刻仅使用过去已经揭晓的价格。先得到问题二/三的净负荷预测，再以7日前同一目标时段价格为基线。历史样本也必须使用当时发布的净负荷预测版本。唯一特征为

$$x=\hat N(\mathrm{target}\mid\mathrm{cutoff})-N(\mathrm{target}-7\mathrm d).$$

对过去至多42天的合法历史执行 StandardScaler + Ridge($\alpha=1$)，一月14—31日只比较 $\gamma\in\{0,0.25,0.5,0.75,1\}$：

$$\hat C=C_{-7\mathrm d}+\gamma\,\widehat{\Delta C}_{\mathrm{Ridge}}.$$

真实目标时段电价不进入预测、选参或LP；只在执行后计算计划、调整和紧急购电费用。"""),
 nbf.v4.new_code_cell("""from pathlib import Path
import json
import pandas as pd
from IPython.display import display, Image
from q4_pipeline import run_pipeline

OUT=Path.cwd()
R=run_pipeline(out_dir=OUT, bootstrap=400)
print('流水线已从原始附件完整执行。')"""),
 nbf.v4.new_markdown_cell("## 2 偏相关：控制共同时间结构"),
 nbf.v4.new_code_cell("""dep=pd.DataFrame([{'范围':'全年',**R['dependence_all']},{'范围':'一月',**R['dependence_jan']}])
display(dep)
print('控制项：144时段、星期、年内sin/cos和线性趋势；置信区间按整日block bootstrap。相关只表示增量关联，不解释为因果。')"""),
 nbf.v4.new_markdown_cell("## 3 一月收缩选择与样本外价格预测"),
 nbf.v4.new_code_cell("""display(R['price_selection'])
display(R['price_metrics'])
print('冻结gamma=',R['checks']['price_gamma'],'；Ridge alpha=',R['checks']['ridge_alpha'])
display(Image(filename=str(OUT/'图表'/'问题四_典型日电价预测.png')))"""),
 nbf.v4.new_markdown_cell(r"""## 4 预测电价驱动的48小时优化

每个LP的目标函数使用对应发布时刻生成的 $\hat C$。问题4-2每天0:00优化288个10分钟时段；问题4-3在0:00、6:00、12:00、18:00用卡尔曼更新后的净负荷重新驱动电价预测，并沿用问题三的固定基准不调整带。SOC状态方程、容量、功率限制与问题二/三一致。"""),
 nbf.v4.new_markdown_cell("## 5 平行消融与真实价结算"),
 nbf.v4.new_code_cell("""display(R['ablation'])
display(R['costs'])
display(Image(filename=str(OUT/'图表'/'问题四_费用构成.png')))
print('两组消融共用净负荷预测、优化器、参数、初始SOC和真实价结算；唯一变化是gamma。')"""),
 nbf.v4.new_markdown_cell("## 6 验证与交付"),
 nbf.v4.new_code_cell("""display(pd.Series(R['checks'],name='验证结果'))
assert all(R['checks'][k] for k in ['q2_lp_all_success','q3_lp_all_success','q2_soc_bounds','q3_soc_bounds','q2_soc_continuity','q3_soc_continuity','q2_cost_identity','q3_cost_identity'])
for stem in ('result4-2','result4-3'):
    assert all(R['checks'][stem].values())
print('验证通过：无泄漏模型口径、严格48小时、全部LP、SOC边界/连续性、费用恒等式和Excel结构/日期/非空。')"""),
 nbf.v4.new_markdown_cell(r"""## 7 边界与限制

继承问题二/三的实现没有设置硬终端SOC等式；48小时后半段用于约束当前储能安排，但滚动执行时只执行到下一决策时刻。代表日检查显示48小时规划末SOC常落在1200 kWh下界，这是未设置终端价值的真实窗口末端效应，不写成已解决。最后一个部署日超出数据年的未来部分由当时合法历史信息外推，仅服务于边界规划，不进入真实费用结算。后续应比较“终端SOC=窗口初值”或加入终端价值的敏感性。"""),
 nbf.v4.new_markdown_cell(r"""## 8 结论

结论数值以上述运行对象为准。耦合模型保持单向：净负荷预测影响电价预测，真实目标电价不会反向修正净负荷或影响决策。gamma=0与冻结gamma的平行消融用于识别价格耦合本身的决策价值。""")]
nbf.write(nb,Path('问题四_波动电价耦合预测与优化.ipynb'))
print('Notebook built')
