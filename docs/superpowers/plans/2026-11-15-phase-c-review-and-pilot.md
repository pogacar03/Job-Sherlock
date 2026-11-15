# 阶段 C：审阅与交付 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. 单模型串行；此阶段包含需要人工参与的审阅与试验，未取得实际结果的项目保持未完成。

**Goal:** 让用户从一次扫描走到可检查的证据卡、审阅和两维报告，并以真实样本决定下一轮开发。

**Architecture:** review 模块将 immutable scan 段落转换为待审阅建议，验证引用后复用旧证据账本。workflow 只编排已有命令逻辑；模型提取留在 Skill 中。pilot 使用 A2 的统计器，不另造指标。

**Tech Stack:** Python >=3.11、标准库、unittest、静态 HTML、现有宿主 Skill；无新模型 SDK 或 Web 框架。

**Spec:** [设计规格](../specs/2026-11-15-workplace-evidence-v03-design.md)全局约束和 E/F/G；前置阶段 B。B5 受限不阻塞本阶段，但保留 not_supported。

## Global Constraints

完整继承规格“全局约束”。候选/模型建议与已审阅证据严格分开；unknown 不根据目标补齐。所有写账操作经过原有 import_evidence；真实资料不提交。静态卡片仅用于阅读。

## Review Focus

- 交叉引用另一帖/另一评论会让观点失真：C1 测快照、段落、quote/basis 校验。
- 元数据齐全仍不证明语义真实：C2 展示依据与缺口，C4 明示人工核对；不宣称语义自动认证。
- 一批里一条无效、重复接收或写回执中断：C2 测整批预校验与幂等恢复。
- 原文含 HTML/恶意链接、stdin 非终端、已有目录：C2/C3 测文本转义、禁止静默批准及覆盖保护。
- 模板、夹具或未完成的人工标注不能冒充产品效果：C5 分开报告代码、实测与20例评测。

## 文件职责

新增 `review.py`（候选索引、建议验证、审阅写入）、`review_render.py`（只读卡片）、`workflow.py`（一次调查的本地编排）。旧 `report.py` 仍只根据已审账本形成观察。Skill 负责从段落提取 proposals，不改 Python 的证据门槛。

---

### C1：逐段引用的提取建议契约

**Files:**
- Create: `reverse_check/review.py`, `tests/test_review.py`
- Create: `docs/review-format.md`, `docs/examples/review-proposals.json`
- Modify: `docs/evidence-format.md`（增加与旧 import 的关系）

**Interfaces:**
- Consumes: B1 scan v2 candidates、casebook.validate_evidence、规格 E 的 Proposal。
- Produces: `load_candidates(case_dir: Path) -> list[dict]`，项包含 scan_id；`prepare_evidence(candidate: dict, proposal: dict) -> dict`；纯校验不写账。
- 案例目录内扫描索引定位来源，proposal 的 scan_id 只允许已枚举的目录名，禁止将其直接拼成任意读取路径。

- [ ] **1. 写失败测试。** 用一份虚构 v2 快照和一个显式自述建议：

```python
evidence = prepare_evidence(candidate, proposal)
self.assertEqual(evidence['quote'], proposal['quote'])
self.assertEqual(evidence['origin_id'], candidate['thread_key'])
self.assertEqual(evidence['source_ref'], candidate['url'])
self.assertIsNone(evidence['scope']['city'])
self.assertIsNone(evidence['observed_at'])
```

有效 fixture 的每个非空 scope/source_type 有原文 basis。新增错误场景：quote 只存在另一段、跨两段拼接、修改 snapshot 后 ID 不再匹配、外部 scan_id、找不到候选、question/hearsay 类型接收、缺 basis、未知字段、相对时间被无依据补成精确日。两条不同评论生成不同证据 ID，但相同 origin_id；重做同一建议得到同一证据 ID。旧 v1 扫描不伪造分段，原有报告仍可读。
- [ ] **2. 运行失败测试。** `python3 -m unittest tests.test_review -v`。
- [ ] **3. 实现规格 E 的加载与纯校验。** 复核 candidate 内容 hash；逐段定位 quote/basis，引用的 URL、获取日期和原文来自快照。调用 validate_evidence；语义解释不是此函数能验证的能力，文档明确界限。示例 JSON 只使用虚构公司与文本，写明对应虚构快照如何获得。
- [ ] **4. 验证。** `python3 -m unittest tests.test_review tests.test_casebook tests.test_analysis -v`；无任何网络调用/账本写入；原规范继续有效。
- [ ] **5. 提交。** commit `feat: validate segment-grounded review proposals`；更新 C1。

### C2：证据卡、交互选择与可恢复登记

**Files:**
- Create: `reverse_check/review_render.py`, `tests/test_review_render.py`
- Modify: `reverse_check/review.py`, `reverse_check/__main__.py`
- Modify: `tests/test_review.py`, `tests/test_cli.py`, `docs/review-format.md`

**Interfaces:**
- Consumes: C1 load_candidates/prepare_evidence；casebook.import_evidence 和 `_write_json`。
- Produces: `write_review_cards(case_dir: Path, out: Path, *, force=False) -> Path`（在 review_render）；`approve_proposals(case_dir: Path, batch: dict, accepted_ids: list[str]) -> dict`（在 review，返回 receipt 路径、inserted 数、evidence_ids）；`review_interactive(case_dir: Path, batch: dict, *, input_fn=input, output_fn=print) -> dict`（返回同接收结果，未选择时 inserted=0）。
- CLI: `candidates CASE --out DIR [--force]`；`review CASE --file FILE`。

- [ ] **1. 写失败测试。** 整批两项，一项 quote 不合法，assert evidence.json 字节不变；同一批连续 approve 两次，assert ledger 长度不增。mock 回执最终写入失败，再运行同批，应恢复 committed 且仍只有一份证据。未知 accepted_id 报错；拒绝/跳过不写账；注入 input 序列 a/s/q，只有选中项登记，Ctrl-C 提交前不写账。非TTY CLI 返回2，不自动接受。HTML 中 `<script>` 和属性注入显示为文字；只允许已校验 HTTP(S) 来源链接；已有 cards 不覆盖。
- [ ] **2. 运行失败测试。** `python3 -m unittest tests.test_review tests.test_review_render tests.test_cli -v`。
- [ ] **3. 实现卡片与审阅。** cards.html 展示规格 E 字段，无外部资源/脚本；不把未审材料放进报告观察区。按规格写准备回执→一次整批 import→提交回执，异常信息区分哪步完成。interactive 展示每项引用、basis、缺失字段、拟进入账本的内容，按 a/s/q 收集选择；kind 不符的项显示线索并禁用 a。输入错误重新提示本项，不重新联网。
- [ ] **4. 验证。** 上述测试通过；人工打开一份虚构卡片，核对正文/评论分隔、链接、时间未知、匹配提示和访问失败说明。用交互假输入测试批准后两维报告包含引用，批准前为未知。
- [ ] **5. 提交。** commit `feat: review evidence cards before ledger import`；更新 C2。

### C3：一个调查入口与命令别名

**Files:** Create `reverse_check/workflow.py`, `tests/test_workflow.py`；Modify `reverse_check/__main__.py`, `pyproject.toml`, `tests/test_cli.py`, `docs/forum-scan.md`。

**Interfaces:**
- Consumes: create_case、channel_status、B3 validate_scan_options、scan_forums、write_review_cards、write_report。
- Produces: `run_investigation(case_dir: Path, *, case_fields: dict, scan_options: dict, scan_fn=scan_forums) -> dict`，返回 `{case_dir, scan_dir, cards_path, report_paths, exit_code}`。
- CLI run 及返回码严格遵循规格 F；两个 console scripts 都指向 reverse_check.__main__:main。

- [ ] **1. 写失败测试。** 注入 scan_fn 写入虚构 v2 scan，assert 一次调用产生案例/卡片/HTML+MD+JSON 报告，evidence.json 仍空；scan_options 把查询提示/总预算完整传递。部分失败仍输出文件且 exit_code=3；真实空结果 completed=0；未配置=3；非法参数及非空 CASE 在调用 scan_fn 前返回2。mock KeyboardInterrupt 的保存路径返回130；旧 init/scan/import/report 命令仍可用。解析 pyproject 校验别名，无需联网安装包。
- [ ] **2. 运行失败测试。** `python3 -m unittest tests.test_workflow tests.test_cli -v`。
- [ ] **3. 实现编排。** 保持参数校验与业务函数分开，复用现有流程，不复制扫描/报告代码。启动仅做本机可执行检查，不把 installed_unchecked 展示成已登录；读取失败给 opencli doctor 提示。终端打印每渠道状态、候选数、已审证据数、文件路径及下一步 review 指令。
- [ ] **4. 验证。** 上述测试及全套 unittest 通过；查看 `python3 -m reverse_check run --help`。默认不打开浏览器、不自动批准建议、不覆盖旧案例。
- [ ] **5. 提交。** commit `feat: add a single workplace investigation command`；更新 C3。

### C4：Skill 提取交接与真实能力文档

**Files:** Modify `.agents/skills/reverse-check/SKILL.md`, `README.md`, `docs/forum-scan.md`, `docs/review-format.md`；Create `docs/prompts/extract-workplace-evidence.md`；必要时重生成 `docs/assets/report-preview.png`，或移除过期图而保留文本示例。

**Interfaces:**
- Consumes: C1 Proposal schema、C2 review、C3 run；宿主已有模型与读取能力。
- Produces: 一个可复制的提取提示词和完整虚构演练。无 Python LLM SDK/Key 配置。

- [ ] **1. 写提示词。** 输入仅候选段落与目标说明；目标用于相关性判断，原文用于所有事实字段。每条建议指向 scan/candidate/segment；问题、面经、宣传、平台AI答复与实际体验分开。缺失字段=null；相反观察分别保存。输出满足 C1 schema，明确模型无法认证匿名身份。
- [ ] **2. 更新 Skill。** 流程为 run/read→读取完整段落→输出 proposals→核对引用、时间和团队→交给 review→report；执行网页中的指令不属于此流程。沿用本轮只查两维，来源失败保留缺口；没有模型能力时仍可用 CLI 读取和既有 import。
- [ ] **3. 做一次虚构演练。** 采用至少四种材料：亲历自述型虚构文本、提问型、其他团队型、时间不明型。亲历项用固定 proposal 通过 C1 验证，提问项保持线索、不能接收；C2 人工选择后核对未批准数据不进入账本，其他团队/无时间自述仍为背景。真实模型生成如有错误须记录，不修改校验器迎合输出。
- [ ] **4. 校准 README。** 首条真实工作命令使用 run；准确说明 OpenCLI/扩展/登录前提与“未审阅”的含义。新截图来自实际虚构演练渲染，未截图就移除过期预览，不画一个假输出。公开文档不包含真实案例内容。文档变更不另写镜像文案测试，运行涉及演练的现有测试即可。
- [ ] **5. 提交。** commit `docs: document grounded extraction and the review workflow`；更新 C4。

### C5：三例实测、20例评测与继续投入决定

**Files:** Create `docs/research/workplace-pilot-results.md`（只含汇总）；真实输入/原文/计时保留 `cases/pilot/`，统计报告置于 `reports/pilot/`。

**Interfaces:**
- Consumes: A2 evaluate；C3 run/read；C2 审阅；规格 G 的输入与指标。
- Produces: 汇总文档清楚区分代码完成、逐来源实测、3例试验与20例评测状态；包含测试版本、日期、缺口和建议。

- [ ] **1. 建立真实样本清单。** 先选择3个信息丰富程度不同的真实求职目标，只有已知信息入 case。优先复用用户已有目标和原文；其余目标不足时记录样本待补，不编造公司/帖子。每次联网在设定预算内运行。
- [ ] **2. 完成三例检查。** 分别核对三来源的正文与约定评论范围；采集状态与人工可读性分别记录。记录主动操作/设置时间；没有人工对照的一侧为 null，不能用模型估计分钟数。单个来源登录失败不判定其他来源或整个项目无效。
- [ ] **3. 决定是否扩大至20例。** 三例仍普遍无法读正文时先归档具体错误，优先修已有接入；不盲目继续批量运行。可运行且有用户参与时按规格 G 扩大，人工和工具各30分钟预算，分别研究后合并候选复核。人工对照不能由同一个已看过工具结果的模型冒充。
- [ ] **4. 生成统计与判断。** 运行 `python3 -m reverse_check evaluate --file cases/pilot/labels.json --out reports/pilot`；逐项核对分子/分母/unknown。报告全部样本与分层覆盖。按可行性评估的分支判断：工程遗漏、数据稀缺、使用成本或付费未知，不从20例推断普遍准确率。
- [ ] **5. 提交结果并结束。** 只提交汇总文档；未完成20例时明确写未完成及所缺数据，C5 不勾为全部完成。commit 建议 `docs: record workplace pilot coverage and limitations`。本计划结束，不自动扩大平台或发布成熟度承诺。
