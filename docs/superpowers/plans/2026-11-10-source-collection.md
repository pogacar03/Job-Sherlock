# Sherlock-informed Source Collection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 将真实Sherlock的来源配置与并发状态机制落到公司原文采集代码中。

**Architecture:** 三个模块分别处理来源清单、受限公开HTTP读取、并发采集及落盘；原有证据导入仍是审阅门槛。CLI与报告使用同一份采集记录。

**Tech Stack:** Python3.11+标准库、ThreadPoolExecutor、http.client、unittest。

**Spec:** docs/superpowers/specs/2026-11-10-source-collection-design.md

## Global Constraints

- Python3.11+标准库；版本0.2.0。
- 单批最多100个URL、1–16线程；默认4线程、10秒连接/读取预算、1MB正文上限。
- 仅公开HTTP(S) GET，逐跳阻止私网地址，不执行脚本或绕过登录。
- 抓取结果只能生成待审阅草稿，不自动增加证据。
- 旧案例格式与离线流程保持兼容。

## Review Focus

- HTTP200验证码/登录页与403/429/5xx不得解释为目标不存在。
- 私网解析、混合公网私网DNS答案、跳转与凭据URL必须在访问前拒绝。
- 大正文、未知编码、重定向循环与空HTML不能卡住整个批次。
- 完成顺序变化不能改变URL与原文/快照的对应关系。
- 来源配置自定义后仍可复查，报告不能混淆采集次数和已审阅证据数量。

### Task 1: 来源配置与公开HTTP读取

**Files:** reverse_check/sources.py, reverse_check/http_source.py, reverse_check/data/sources.json, tests/test_sources.py, tests/test_http_source.py

**Interfaces:** `load_sources(path=None) -> dict`、`source_for_url(registry, url) -> dict | None`、`source_queries(case, registry, selected=None) -> list[dict]`、`public_fetch(url, timeout, max_bytes) -> FetchedPage`；`FetchError`携带分类、HTTP码与最终URL。

- [x] 写来源注册、主机后缀、模板未知字段/格式、HTTP URL与解析安全行为测试并观察失败。
- [x] 实现固定清单、编码检索模板、固定公网IP的GET和逐跳检查。
- [x] 运行相关测试及完整测试；提交实现。

### Task 2: 并发采集与待审阅产物

**Files:** reverse_check/collection.py, tests/test_collection.py

**Interfaces:** `collect_sources(case_dir, urls, registry=None, workers=4, timeout=10, max_bytes=1000000, fetch=public_fetch) -> Path`、`collection_summary(case_dir) -> dict`。

- [x] 写真实线程协同行为、逐项失败、软登录/验证码、去重、快照哈希与草稿不能直接导入测试并观察失败。
- [x] 实现分类、有限HTML文本提取、来源快照、逐次run及报告摘要。
- [x] 运行相关测试及完整测试；提交实现。

### Task 3: CLI、报告与使用契约

**Files:** reverse_check/__main__.py, reverse_check/analysis.py, reverse_check/report.py, README.md, docs/collection.md, tests/test_cli.py

**Interfaces:** CLI `sources`与`collect`；`plan`增加来源筛选；报告新增独立collection字段和可读概况。

- [x] 写CLI端到端、未审阅数据不进入维度判断、报告转义及错误输入测试并观察失败。
- [x] 集成命令、报告与0.2.0版本；更新Skill中的采集入口和审阅要求。
- [x] 完整测试、公开URL只读烟测、打包运行、独立审查与必要修复；记录验证并提交，不推送。
