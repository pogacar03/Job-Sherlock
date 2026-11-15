# 阶段 B：来源与查询 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. 单模型串行；每次只加载当前任务相关规格与文件。

**Goal:** 在三个核心来源中保留可引用原文、改善部门检索，并让失败与时间成本可控。

**Architecture:** 新增 forum_content 封装详情格式，queries 封装纯检索规则，budget 管理一轮扫描时限；forums 负责协调与落盘。保留现有浏览器实现及调用注入方式。

**Tech Stack:** Python >=3.11、标准库、现有 OpenCLI、unittest；可选 Node 执行已有形式的 DOM 测试。

**Spec:** [设计规格](../specs/2026-11-15-workplace-evidence-v03-design.md)全局约束和 B/C/D 章节；前置 A1–A2。

## Global Constraints

完整继承规格“全局约束”；默认仅小红书、牛客、脉脉。已知签名 URL 按原样读取；采集只写待审阅数据。上线能力必须有真实读取记录，夹具只证明代码行为。

## Review Focus

- 签名变化不能拆成不同来源，也不能改写取文链接：B1 测 identity 与 fetch URL 分离。
- 正文提问与评论体验不能混成同一作者：B1 测逐段来源与未知字段。
- 完整部门被缩写丢失、提示词被当成已确认归属：B2 测两者隔离。
- 登录/评论失败、预算中断不能丢掉已读正文：B3 测检查点及退出码。
- 静态标题、加载中、推荐区不能被当作评论：B4 保存真实结构证据，B5 测加载竞态和隔离。

## 文件职责

新增 `forum_content.py`（统一读取）、`queries.py`（查询与提示）、`budget.py`（时限）。仅在 `browser_forums.py` 增加有依据的脉脉评论读取。`forums.py` 保留 orchestration；不要重写通用 HTTP 采集器。

---

### B1：统一原文分段与已知链接直读

**Files:**
- Create: `reverse_check/forum_content.py`, `tests/test_forum_content.py`
- Modify: `reverse_check/forums.py`, `reverse_check/__main__.py`
- Modify: `tests/test_forums.py`, `tests/test_cli.py`, `docs/forum-scan.md`

**Interfaces:**
- Consumes: `_tool`, `_allowed`, 当前 nowcoder detail、XHS field/value note、maimai_post、nowcoder_comments 及 XHS comments。
- Produces: 规格 B 的 `thread_key/candidate_id_for/normalize_thread/read_forum_thread`；scan 增加 keyword-only source_urls；run v2 的 candidates；CLI read。
- `read_forum_thread` 接受用于保存原始输出的 tool 包装器；搜索和直读复用同一详情读取代码。原始响应仍进 scans/raw。

- [ ] **1. 写失败测试。** 新测试类 `ForumContentTests`：

```python
self.assertEqual(thread_key('xiaohongshu', 'https://www.xiaohongshu.com/explore/abc?xsec_token=a'),
                 thread_key('xiaohongshu', 'https://www.xiaohongshu.com/search_result/abc?xsec_token=b'))
self.assertNotEqual(thread_key('maimai', 'https://maimai.cn/community/gossip-detail/123'),
                    thread_key('nowcoder', 'https://www.nowcoder.com/discuss/123'))
```

normalize_thread 输入正文“这个团队加班吗？”和评论“我这个月每周两晚加班”，断言两段、不同 kind、正文 author=null、原字段未知仍 null。同文不同作者两条评论保留；同快照 ID 稳定。XHS 用真实 field/value 结构夹具；搜索摘要不进入 segments。正文成功、评论 AUTH_REQUIRED 时仍返回正文和错误。直读只调用详情/评论，不调用 search；外域及错误路由在读前拒绝，原签名原样交给 tool。旧 v1 scan 报告仍可打开。
- [ ] **2. 运行失败测试。** `python3 -m unittest tests.test_forum_content tests.test_forums tests.test_cli -v`。
- [ ] **3. 实现规格 B。** 将现有核心来源详情路径移动到统一读取函数；保留 `_tool` 的错误解析，避免 forum_content 与 forums 循环导入（公共域名验证放 forum_content，由 forums 导入）。新 candidates 包含已读但未命中关键词的原文，现有 documents/leads 作为派生集合。read 接入 source_urls 模式，先校验输入再建目录。
- [ ] **4. 验证。** 上述测试全部通过；用注入 tool 的扫描检查 raw、candidates、documents/leads 与 evidence.json 空数组一致；不通过真实账号运行单测。
- [ ] **5. 提交。** `git diff --check`，commit `feat: preserve forum segments and read known post URLs`；更新 B1。

### B2：完整部门查询和可解释的匹配提示

**Files:** Create `reverse_check/queries.py`, `tests/test_queries.py`；Modify `forums.py`, `__main__.py`, `tests/test_forums.py`, `tests/test_cli.py`, `docs/forum-scan.md`。

**Interfaces:**
- Consumes: case 字段与 B1 candidates。
- Produces: 规格 C 的 `build_forum_queries/match_hint`；scan keyword-only search_terms；每个 candidate 增加 match_hint；CLI --search-term。

- [ ] **1. 写失败测试。**

```python
case = {'company': '示例科技', 'department': '国际化广告 CRM 与交易', 'company_aliases': []}
queries = build_forum_queries(case, ['CRM平台'])
self.assertEqual(queries[0], '示例科技 国际化广告 CRM 与交易')
self.assertEqual(len(queries), 4)
self.assertEqual(queries[-1], '示例科技 CRM平台')
```

另测 NFKC/空白/大小写、重复词稳定去重、最多3条提示/6条查询；缺部门不返回 department_mention；单独 CRM、其他公司、公司级泛帖分别得预期提示。调用 match_hint 前后 case/证据对象不变；显式 query 与 search-term 冲突在写目录前报错。
- [ ] **2. 运行失败测试。** `python3 -m unittest tests.test_queries tests.test_forums tests.test_cli -v`。
- [ ] **3. 实现规格 C。** 删除默认只取英文缩写的逻辑；提示值只作为候选标签，不修改分析规则。options 同时记录实际执行查询和输入提示词，显式 --query 原样保留。
- [ ] **4. 验证。** 上述测试通过，扫描仍默认三个核心来源；已有手工指定 --query 测试保留。
- [ ] **5. 提交。** commit `feat: retain department names in forum discovery`；更新 B2。

### B3：总预算、步骤状态和部分结果检查点

**Files:** Create `reverse_check/budget.py`, `tests/test_budget.py`；Modify `forums.py`, `__main__.py`, `tests/test_forums.py`, `tests/test_cli.py`, `docs/forum-scan.md`。

**Interfaces:**
- Consumes: B1 统一读取和 B2 查询；现有工具注入和 `_write_json`。
- Produces: 规格 D 的 Budget 四个方法、`validate_scan_options(...) -> dict` 纯校验；scan keyword-only total_timeout/clock；run v2 的状态、options、steps 与检查点。

- [ ] **1. 写失败测试。** 使用可推进的 fake clock，不进行真实 sleep：

```python
ticks = [0.0]
budget = Budget(10, clock=lambda: ticks[0])
ticks[0] = 8.0
self.assertEqual(budget.timeout_for(20), 2.0)
ticks[0] = 10.0
with self.assertRaises(FetchError) as caught:
    budget.timeout_for(20)
self.assertEqual(caught.exception.status, 'budget_exhausted')
```

集成测试：第一篇正文成功后评论耗尽预算，正文仍在 candidates、其他渠道 not_started_budget、停止新读取、evidence 不变。第二查询失败不抹去第一查询结果。Ctrl-C 保存 interrupted 和已完成候选，CLI=130。正常详情后的关闭计入正常预算；stop 后两次清理共享5秒窗口，重复 stop 不续期。拒绝 bool/NaN/inf/0/1801；单次 timeout 不超过剩余预算；空结果 completed 与登录失败 partial 区分。
- [ ] **2. 运行失败测试。** `python3 -m unittest tests.test_budget tests.test_forums tests.test_cli -v`。
- [ ] **3. 实现规格 D。** 先抽出 validate_scan_options，让 scan 和 C3 的 run 共用无副作用校验。外层 scan 创建一次 Budget，包装工具与 native fetch，内部回退/评论共享预算；清理识别 browser close 与本轮 tabs.remove，按规格区分正常预算和 stop 后窗口。每个查询/直读完成后原子落盘；工具包装器遇 KeyboardInterrupt 先 stop，外层保存检查点后向 CLI 传递中断。无法保存时输出本地写入错误。所有提前结束仍产生可解释的渠道结果。
- [ ] **4. 验证。** 上述测试及 `tests.test_collection` 通过；检查日志 elapsed_ms 非负，未知错误不变成 no_results，stdout 不打印原始响应或签名内容。
- [ ] **5. 提交。** commit `feat: bound scans and preserve partial results`；更新 B3。

### B4：只读核查脉脉评论契约

**Files:** Create `docs/research/maimai-comments-contract.md`；真实快照仅保存 `cases/platform-probes/maimai-comments/`。

**Interfaces:**
- Consumes: 当前连接浏览器、真实打开的脉脉职言帖子；已有 browser_forums.py 页面对齐和租约清理方式。
- Produces: 文档字段 `status=verified|limited`、核查日期、识别到的评论容器/文本/作者/父回复/时间、ready/empty/loading/login 信号、覆盖范围、匿名化 DOM 结构及局限。B5 只采用 verified 的结构。

- [ ] **1. 检查环境。** 运行 `opencli doctor`，记录可执行/连接状态；连接成功不等于脉脉登录。已有会话能读时继续，不重复要求用户登录。
- [ ] **2. 有限探测。** 最多3条公开或用户授权的实际职言链接，每条最多60秒；读取正常页面可见评论及加载状态。记录哪些节点是真评论、哪些为推荐/AI答复/导航。页面不可读、仅图片或无法区分节点时如实记录。
- [ ] **3. 形成可复查契约。** 存真实快照于忽略目录；将最小 DOM 结构人工脱敏为虚构文字后写文档。选择器必须来自观察。未找到可验证结构就 status=limited，列出已试路径和阻碍，不猜私有接口。
- [ ] **4. 验证文档边界。** 区分已读评论、加载中和无评论；没有验证全量分页就写 visible_only。确认没有 Cookie、真实会话链接或用户案例原文进入 Git diff。
- [ ] **5. 提交。** 仅提交契约文档；commit `docs: record observed Maimai comment contract`。路线图 B4 写 verified 或 limited 及原因。此任务不需要增加镜像实现的单元测试。

### B5：按已验证契约接入有限评论

**Files:** Modify `reverse_check/browser_forums.py`, `reverse_check/forum_content.py`, `tests/test_forum_content.py`, `tests/test_forums.py`, `docs/forum-scan.md`；Create `tests/data/maimai-comments.html`（仅虚构内容且结构来自 B4）。

**Interfaces:**
- Consumes: B4 verified 契约；B3 限时 tool。
- Produces: `maimai_comments(executable, url, timeout, tool) -> list[dict]`，字段与 nowcoder_comments 同类；成功后 read_forum_thread 标 visible_only。

- [ ] **1. 检查前提。** B4=limited 时保留 maimai 的 not_supported，更新 B5 为“受限，未实现”，记录原因后直接进入阶段结项；不创建假通过测试或占位成功实现。
- [ ] **2. 写并运行失败测试。** 覆盖延迟加载、明确空状态、外域跳转、推荐区排除、正文成功但评论超时、只关闭自建标签页。运行 `python3 -m unittest tests.test_forum_content tests.test_forums -v`，确认新行为失败。DOM 测试采用现有可选 Node 形式，断言原文和父回复数据，不能只 stub Python 返回最终数组。
- [ ] **3. 实现真实结构读取。** 最多40条当前可见评论；等待真实节点或已验证空状态，静态标题不算 ready。不点击发布、点赞或发送按钮。复用本轮预算和 finally 清理；不明确的时间/身份为 null。
- [ ] **4. 验证并实测。** 上述测试通过；最多两条已知原帖核对正文、评论、覆盖限制与失败状态。不将样本读取成功升级为平台全量可用。真实状态写文档，虚构夹具写明来源为结构脱敏。
- [ ] **5. 提交并结束阶段。** commit `feat: read verified visible Maimai comments`（仅实际实现时）；`python3 -m unittest discover -q`。更新 B5 的代码和实测两个状态，列明受限项，停止于此。
