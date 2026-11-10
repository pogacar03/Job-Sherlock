# Reverse Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 交付可运行、引用可复查的公司与部门反向背调首版。

**Architecture:** Python 标准库负责本地证据账本、确定性判断与报告；Skill 利用宿主搜索与子 Agent 收集原文。案例和证据保存为 UTF-8 JSON。

**Tech Stack:** Python 3.11+、unittest、静态 HTML/CSS、Codex SKILL.md。

**Spec:** docs/superpowers/specs/2026-11-10-reverse-check-design.md

## Global Constraints

- Python 3.11+，运行和测试仅使用标准库。
- 六个维度；默认365天窗口；没有证据显示未知。
- 不输出公司好坏总分或伪精确概率。
- 所有角色共享证据账本，不投票认定事实。
- 初始化和报告默认不覆盖已存在文件，导入任一条错误时整批不写入。

## Review Focus

- 空部门、日期未知或只有招聘宣传时应保留背景，不产生部门判断。
- 同一事件跨平台转载及重复导入不能夸大材料覆盖。
- 一批数据部分非法时不能留下部分写入。
- HTML、恶意URL与来源中的指令都作为数据，不能执行。
- 报告可离线打开、窄屏可读，演示数据不能被误认成真实调查。

### Task 1: 案例与证据账本

**Files:** reverse_check/casebook.py, reverse_check/__init__.py, tests/test_casebook.py

**Interfaces:** `create_case(path, **fields) -> dict`、`read_case(path) -> dict`、`import_evidence(path, records) -> int`、`read_evidence(path) -> list[dict]`。

- [x] 写行为测试：创建不覆盖；原文摘录验证；非法URL和字段拒绝；整批原子写入；重复导入幂等。
- [x] 运行 `python3 -m unittest tests.test_casebook -v`，确认缺少实现而失败。
- [x] 实现完整输入验证、规范化与原子 JSON 写入。
- [x] 运行同一命令确认通过；提交此任务文件。

### Task 2: 证据分析

**Files:** reverse_check/analysis.py, tests/test_analysis.py

**Interfaces:** `analyze(case, records) -> dict`、`build_plan(case) -> str`；消费 Task 1 的已验证案例与证据。

- [x] 写测试：无证据未知、不同部门仅背景、陈旧日期、摘要、官方宣传、转载连通去重、多来源相反意见保留冲突。
- [x] 运行 `python3 -m unittest tests.test_analysis -v`，确认失败。
- [x] 实现范围匹配、日期窗口、来源簇与六维判断及检索计划。
- [x] 运行完整 `python3 -m unittest discover -v`；提交此任务文件。

### Task 3: CLI 与可审阅报告

**Files:** reverse_check/report.py, reverse_check/__main__.py, examples/demo-evidence.json, tests/test_cli.py, pyproject.toml

**Interfaces:** `write_report(case_dir, out, force=False) -> list[Path]`；CLI `init`, `plan`, `import`, `report`, `demo`。

- [x] 写端到端测试：初始化→计划→导入→报告；空案例；错误CLI输入；报告覆盖保护；HTML转义和演示标识。
- [x] 运行 `python3 -m unittest tests.test_cli -v`，确认失败。
- [x] 实现命令、响应式中文报告、Markdown与机器可读JSON。
- [x] 运行完整测试和实际 demo 命令；提交此任务文件。

### Task 4: Skill、文档和独立复核

**Files:** .agents/skills/reverse-check/SKILL.md, README.md, docs/evidence-format.md, docs/development-log.md

- [x] 对离线背调案例先执行无 Skill 基线，再以 Skill 完成真实CLI工作流。
- [x] 编写短入口，按需链接证据契约；为用户写从演示到真实调研的命令。
- [x] 完成 Skill 结构校验、完整测试、报告视觉检查及独立代码审查。
- [x] 将实际限制和验证结果记录在开发日志；提交本次成果，不推送远程。
