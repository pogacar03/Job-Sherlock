# 阶段 A：范围与评测 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. 按交接选择单模型串行执行；复选框逐项记录，不自动创建子 Agent。

**Goal:** 让所有默认流程统一为工作强度/氛围，并建立不会把未知算作成功的评测统计器。

**Architecture:** 在现有分析和报告流程上收敛默认维度，保留旧账本格式。评测使用独立纯函数处理人工标注文件，与论坛联网完全分开。

**Tech Stack:** Python >=3.11、标准库、unittest。

**Spec:** [设计规格](../specs/2026-11-15-workplace-evidence-v03-design.md)的全局约束、A/G 章节。

## Global Constraints

完整继承规格“全局约束”；本阶段仅实现两维统一与离线评测。保留旧案例/证据和原命令；`cases/`、`reports/` 不提交。没有真实标注时结果为未知。

## Review Focus

- 旧六维证据不能静默丢失：A1 增加背景保留和原文件不变测试。
- 有无 scan 不应改变默认维度：A1 比较两种案例报告。
- 未完成标注不能变成零次错误/零条体验：A2 测 null 与空数组区别。
- 零分母、无配对用时不能输出虚假比率：A2 测 value=null。
- 布尔数值、重复 ID 和部分标注会扭曲统计：A2 测严格校验及 unknown_count。

## 文件职责

修改 `casebook.py/analysis.py/report.py` 统一关注范围；新增 `pilot.py` 只做评测校验与统计；`__main__.py` 仅解析新 evaluate 参数与调用。`docs/evaluation.md` 记录人工如何提供标注。

---

### A1：统一两维，同时保留历史数据

**Files:**
- Modify: `reverse_check/casebook.py` 的 DIMENSIONS 附近
- Modify: `reverse_check/analysis.py` 的 `_reasons/analyze/build_plan`
- Modify: `reverse_check/report.py` 的 `write_report`
- Modify: `tests/test_analysis.py`, `tests/test_cli.py`, `README.md`, `docs/forum-scan.md`

**Interfaces:**
- Consumes: `validate_case`, `validate_evidence`, `analyze(case, records)`, `write_report(case_dir,out,force=False)`。
- Produces: `casebook.FOCUS_DIMENSIONS = ('workload','atmosphere')`；现有函数签名不变，analyze 默认两维。

- [ ] **1. 写失败测试。** 把旧的“空案例六维未知”测试改名并改为两维，新增旧维度保留背景测试。

```python
report = self.assess(record(dimension='growth'))
self.assertEqual(set(report['dimensions']), {'workload', 'atmosphere'})
self.assertEqual(report['summary']['unknown_dimensions'], 2)
self.assertEqual(report['summary']['total_count'], 1)
self.assertEqual(report['summary']['eligible_count'], 0)
self.assertIn('非本轮关注维度', report['background'][0]['reasons'])
```

CLI 测试同时覆盖有 scan/无 scan 两种情况，调用 report 前后对 evidence.json 字节做相等断言。build_plan 不再产生旧四维章节；旧记录仍能 import。

- [ ] **2. 运行失败测试。** `python3 -m unittest tests.test_analysis tests.test_cli -v`；预期因仍输出六维或丢弃旧记录失败，不能因拼写/导入错误冒充行为失败。
- [ ] **3. 最小实现规格 A。** 保留 DIMENSIONS 原枚举；新增关注常量，范围外记录分类为背景。删除 write_report 按 scan 有无过滤 rows/维度的分支；build_plan 只生成两维问题。README 当前能力/示例统一两维，旧报告截图暂标注历史演示，C4 再更新。
- [ ] **4. 验证。** `python3 -m unittest tests.test_analysis tests.test_cli tests.test_casebook tests.test_forums -v` 全部通过；核对 README 的六维承诺已更新，历史记录说明保留。
- [ ] **5. 提交。** `git diff --check` 通过，只 add 上述改动；commit 建议 `feat: focus workplace reports on workload and atmosphere`。更新路线图 A1。

### A2：可复查的评测输入、统计和空模板

**Files:**
- Create: `reverse_check/pilot.py`, `tests/test_pilot.py`
- Create: `docs/evaluation.md`, `docs/examples/pilot-template.json`
- Modify: `reverse_check/__main__.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: 规格 G 的 JSON 输入；不读取真实论坛、模型或 evidence.json。
- Produces: `evaluate_pilot(data: dict) -> dict`；`write_pilot_report(data: dict, out: Path, *, force=False) -> list[Path]`。
- 输出键：`metrics` 含 `body_read_rate/comment_read_rate/related_rate/tool_case_coverage/manual_positive_tool_coverage`；每项固定 numerator/denominator/unknown_count/value。另有 `strata`（各组 tool_case_coverage）、`active_time_reduction`（value, paired_count）、`setup_time`（manual/tool 各 median, count）、`errors`（各类型 sum, reviewed_count, unknown_count）。
- CLI: `evaluate --file INPUT --out DIR [--force]`；输出 `evaluation.json/evaluation.md`。

- [ ] **1. 写失败测试。** `test_empty_evaluation_is_unknown`：

```python
result = evaluate_pilot({'schema_version': 1, 'cases': [], 'read_checks': []})
self.assertIsNone(result['metrics']['tool_case_coverage']['value'])
self.assertEqual(result['metrics']['tool_case_coverage']['denominator'], 0)
self.assertIsNone(result['active_time_reduction']['value'])
```

另造虚构三例：manual 阳性/tool 阳性，manual 阳性/tool 空数组，双方未标注。应得人工阳性覆盖1/2、未知1；原始来源 ID 重复不增加证据数。时间100→60与200→100的配对 median reduction=0.45；人工时间0或任一 null 排除。人工不可读页面不纳入读取率；comments_expected=false 不纳入评论率。拒绝 bool/NaN/负数/重复 ID/超过10条 top10；缺标错误次数保持 unknown。CLI 验证空模板输出成功、旧文件不覆盖、非法输入返回2且无 traceback。

- [ ] **2. 运行失败测试。** `python3 -m unittest tests.test_pilot tests.test_cli -v`；应因新接口或上述行为尚未实现而失败。
- [ ] **3. 实现纯函数与命令。** 严格按规格 G 校验；使用 statistics.median，分母0返回 None。未知项计数定义：先确定适用总体，再计缺失的判定。manual_positive_tool_coverage：manual=null 或 manual阳性/tool=null 时计未知；manual空数组属于已确认不适用，不论tool是否完成都排除；双方已审且manual阳性才进分母。人工不可读的 read_check 排除，manual_readable未知则计未知；评论不在约定范围时排除。模板只含空数组，不放真实得分；文档给另外的明确虚构示例。
- [ ] **4. 验证。** `python3 -m unittest tests.test_pilot tests.test_cli -v`，再运行 `python3 -m unittest discover -q`。用模板生成 `reports/pilot-template-check`，核对 JSON null 与 Markdown“尚未评测”一致，已有目录拒绝覆盖。
- [ ] **5. 提交并结束本阶段。** `git diff --check`；commit 建议 `feat: add offline workplace pilot evaluation`。更新 A2，报告实际测试数；不要开始 B，也不要把空模板当真实试验。
