# Job-Sherlock v0.3：工作体验线索与审阅流程

日期：2026-11-15。状态：待实施。依据：[可行性评估](../../research/2026-11-15-job-sherlock-feasibility.md)。执行入口：[开发路线与交接](../plans/2026-11-15-development-roadmap.md)。

## 产品目标

围绕一个具体求职目标，从小红书、牛客、脉脉取得可追溯的工作体验线索，标明原文、评论上下文、访问缺口与待核实项，让用户审阅后形成工作强度、团队氛围报告。首次运行的成功是产生可复查的线索及清晰的渠道状态；不要求每个目标都有可用于结论的体验。

本轮完成范围：两维统一、可复现的评测、三个来源的正文/有限评论、完整部门搜索与显式搜索提示词、可中止的扫描、逐段引用、候选审阅和一个调查入口。保持 CLI + Skill。模型提取通过宿主 Skill 完成，Python 不接入新的模型供应商。

后续再决定：OfferShow/V2EX 扩展、自动组织别名图谱、深层评论全量翻页、OCR、多用户系统和云服务。20例评测决定是否扩大投入；这些项目不是本轮验收条件。

## 全局约束

- Python >=3.11，生产 Python 代码仅使用标准库；在线论坛仍复用 OpenCLI，Node 仅用于已有的可选 DOM 测试。
- 当前产品维度固定为 `workload`、`atmosphere`；新计划、默认报告和示例只介绍这两项。
- 保留旧案例、旧证据与旧命令的读取能力；历史其他维度记录留在背景区，原始文件不自动迁移或删除。
- 默认来源固定为 `xiaohongshu`、`nowcoder`、`maimai`；已有其他来源仍仅在显式选择时运行。
- `scan`、`read`、`run`、候选导出均不写入 `evidence.json`；经过审阅的记录复用 `import_evidence` 串行登记。
- 登录限制、超时、未配置、正文无法识别、成功但无结果分别记录；缺失字段使用 `null`，不得填入调查目标假装来自原文。
- 普通测试全部离线且不使用真实账号；真实案例、原文、会话链接只存 `cases/`、`reports/`，仓库只收虚构夹具与汇总指标。
- 浏览器仅进行读取与必要导航；复用正常页面实际提供的 URL；只清理本轮自己创建的标签页。
- 不增加模型 API Key、Agent 框架或后台常驻服务；执行方式为单模型串行、逐任务提交。

## A. 两维兼容

在 `casebook.py` 增加 `FOCUS_DIMENSIONS = ('workload', 'atmosphere')`；保留 `DIMENSIONS` 六项作为旧证据枚举。`analyze` 的 `dimensions` 固定输出两项；其他维度记录进入 `background`，理由为“非本轮关注维度”。`total_count` 保持所有导入材料数，`eligible_count` 只数两维可用记录，`unknown_dimensions` 为0–2。`write_report` 不再依据有无 scan 切换维度或静默丢弃旧记录。

## B. 统一论坛原文

新增 `forum_content.py`，负责三个核心来源的详情读取与格式转换，不管理搜索或案例持久化。接口：

```python
def thread_key(channel: str, url: str) -> str: ...
def candidate_id_for(thread_key: str, title: str, segments: list[dict]) -> str: ...
def normalize_thread(channel: str, url: str, title: str, body_text: str,
                     comments: list[dict], *, comment_status: str,
                     published_at_raw: str | None, retrieved_at: str) -> dict: ...
def read_forum_thread(channel: str, url: str, *, executable: str,
                      timeout: float, tool) -> dict: ...
```

`thread_key` 从校验过的平台与帖子路径提取原帖 ID：牛客 `/feed/main/detail/<id>` 或 `/discuss/<id>`；小红书 `/explore/<id>`、`/search_result/<id>`、`/note/<id>`；脉脉 `/community/gossip-detail/<id>`。结果为 `平台:帖子ID`，不同平台绝不合并。读取使用原始完整 URL，身份键不用于构造或替换 URL。未支持的路由返回 `unsupported_source`，不猜测 URL。小红书直读需要实际链接的签名参数，不生成签名。

统一记录保留现有 `channel/url/title/text/comments/comment_status/published_at/scope_note`，新增：

| 字段 | 约定 |
|---|---|
| `thread_key` | 上述原帖身份键；一个帖子及其回复保守视为同一来源上下文 |
| `candidate_id` | `c-` + SHA256(thread_key + NUL + 下述内容 JSON)前20位；内容 JSON 仅含 `title, segments`，UTF-8、sort_keys=True、ensure_ascii=False、separators=(',', ':') |
| `retrieved_at` | 上海采集日期 YYYY-MM-DD |
| `published_at_raw` | 实际时间字段转成字符串；不把发布日期当体验日期 |
| `segments` | 按页面顺序的分段，第一段是正文，其后为已读评论 |
| `errors` | 评论等非致命失败的 `{stage,status,reason}` 数组 |

每段固定包含 `id, kind, text, author, author_url, platform_id, parent_id, time_raw`。`kind` 只为 `body/comment`；正文 id=`body`，评论 id=`comment-0001` 起按本次快照顺序编号。平台原 ID 单独保存，缺失为 null；同文不同作者的评论保留。正文与评论分开保存原始提取文本，全文 `text` 仅供兼容检索。搜索摘要、页面导航、快捷回复按钮不进入段落。未知作者保持 null。详情接口没有返回标题时，搜索标题仅用于卡片标题和线索匹配，不作为可引用段落。

已读正文在评论失败时保留，`errors` 记录失败，`comment_status` 为实际失败状态。`not_supported` 仅表示该渠道没有实现评论。既有 `visible_only/bounded` 仍不代表全量评论。

新扫描 `run.json` 使用 `schema_version=2`，保留原字段，新增 `candidates`：三个核心来源所有成功读取的统一记录，含未通过工作词筛选的记录。`documents/leads` 保留原含义，作为兼容派生集合。旧 scan v1 继续可在报告里查看，但不伪造段落供新审阅器引用。

`scan_forums` 原有参数和位置不变，在末尾增加 keyword-only `source_urls=None`。其值为 `{渠道: [实际URL]}`；有值时只读取指定链接、不搜索。最多20个链接，渠道须是三个核心来源且出现在 channels 中。`read CASE URL --source CHANNEL` 调用这一模式，同样存入 scans。正文/评论失败如实登记。

## C. 搜索与匹配提示

新增 `queries.py`：

```python
def build_forum_queries(case: dict, search_terms: list[str] | None = None) -> list[str]: ...
def match_hint(case: dict, candidate: dict, search_terms: list[str] | None = None) -> str: ...
```

默认查询顺序固定：`公司 完整部门`、前者加` 加班`、前者加` 氛围`；公司/部门空白归一，不擅自把部门缩成 CRM。用户可重复提供 `--search-term`，最多3条非空、每条最多80字符，逐条追加 `公司 搜索提示词`，稳定去重，总数最多6。已有显式 `--query` 优先并完整保留；与 `--search-term` 同时给出属于输入错误。

`match_hint` 使用 NFKC、忽略空白和大小写，检查标题及段落；先要求公司或显式公司别名命中。依次返回 `department_mention`、`search_hint`、`company_only`、`unrelated`。其中 department_mention 要求非空完整部门名出现。所有结果都是检索提示，不认证作者或团队归属，不改变 `analysis._reasons` 的证据门槛。提示词写入 run.options，不写回 case.department 或证据 scope。

## D. 总预算与状态

新增 `budget.py`：`Budget(total_seconds: float, *, clock=time.monotonic)`；方法 `remaining() -> float`、`timeout_for(per_call: float) -> float`、`stop() -> None`、`cleanup_timeout() -> float`。计时不读墙上时间；无剩余或已经 stop 时 timeout_for 抛 `FetchError('budget_exhausted', ...)`。正常读取过程中的会话释放计入正常预算，cleanup_timeout 返回 min(5,剩余预算)。stop 幂等地停止新读取并启动**全轮总计最多5秒**的结束清理窗口；窗口用尽时 cleanup_timeout 同样抛 FetchError。自然耗尽时第一次 cleanup_timeout 自动 stop，不给每个标签重新计时。工具包装器遇到 KeyboardInterrupt 时先 stop 再向外传递，使各层 finally 共用同一清理窗口。

`scan_forums` 再增加 keyword-only `total_timeout=180, clock=time.monotonic, search_terms=None`。`--total-timeout` 为1–1800秒有限数，拒绝 bool/NaN/inf；现有 `--timeout` 仍是单次调用预算。所有平台子调用、回退和直接读取通过同一个限时工具包装器，传递 min(单次预算, 剩余总预算)。预算到期不再启动新的搜索/正文/评论读取；允许保存结果和有限清理，不承诺精确到毫秒的进程退出时间。

把输入校验提取为 forums.py 的纯函数 `validate_scan_options(*, channels=None, queries=None, limit=5, timeout=20, topic_ids=None, source_urls=None, total_timeout=180, search_terms=None) -> dict`，返回上述键的规范化值，不读取案例或联网。scan 与后续 run 共用它，保证 run 的非法扫描参数在创建案例前失败。

run v2 添加 `started_at, finished_at, elapsed_ms, status, options, steps`。UTC ISO 时间用于开始/结束，monotonic 计时用于 elapsed_ms。status=`completed/partial/budget_exhausted/interrupted`；选定但因预算未启动的渠道 status=`not_started_budget`。steps 每项含 `channel, stage, query, url, status, elapsed_ms`，query/url 不适用时 null。正文成功、评论失败必须有各自步骤状态。

每完成一次查询或已知链接读取后原子保存检查点；Ctrl-C 保存已完成候选和 interrupted 状态，再清理，CLI 返回130。进行中的详情/评论不承诺形成完整候选，已保存的原始步骤响应仍保留。正常写入失败应报错，不能把没有保存的结果描述为已保存。无网络的缓存 collection 仍可在结束阶段生成，须保持正文快照与 candidates 一致。

## E. 候选、提取建议与审阅

新增 `review.py`：读取新 scan 的 candidates，用 `(scan_id,candidate_id)` 定位不可变快照；旧扫描显示“旧格式，需重新读取后逐段审阅”。首版不对真实原文运行自动分类模型。

提取建议文件格式固定为 `{"schema_version":1,"proposals":[...]}`。每项字段：

```
id, scan_id, candidate_id, segment_id, quote, observation,
kind, source_type, dimension, direction, scope,
observed_at, published_at, basis
```

每批1–100项，id 唯一；`id` 沿用现有80字符标识规则；kind=`experience/question/hearsay/official/unknown`。dimension 只为两维，其余枚举沿用 casebook。scope 必须显式包含 SCOPE_FIELDS，缺失信息写 null。basis 为数组，每项 `{field, segment_id, part, quote}`，field 只允许 `source_type`、`observed_at`、`published_at` 或 `scope.<字段名>`。part=`text/time_raw`；只有 published_at 的依据允许引用 time_raw，其他字段均引用 text。正文 time_raw 使用 published_at_raw，评论保留自己的时间原文。

`prepare_evidence(candidate: dict, proposal: dict) -> dict` 负责：

1. 拒绝未知字段、错误快照或段落 ID；quote 必须是指定段落的原样非空子串，不能横跨正文/评论；basis 引用也必须逐段存在。
2. 论坛建议仅 kind=experience 且 source_type=employee_account 可走新审阅器的接收路径；问题、转述与宣传保留为线索。用户访谈仍走旧 import 的 user_interview，旧 import 对背景材料的能力保留。
3. 所有非空 scope 字段、source_type 及非空日期必须各有对应 basis。这只验证出处存在，语义和日期解释仍由审阅者核对；相对时间无法确定具体日期时留 null。
4. `source_ref/title/retrieved_at` 从快照取得，`source_text` 由该快照各段原文按顺序以两个换行拼接，`access='full_text'`、`origin_id=thread_key`。scope、观察日期和判断绝不从 case 自动补齐。
5. evidence id=`r-` + SHA256(除 id 外的标准证据 JSON)前20位，JSON 序列化规则同 B。复用 `validate_evidence`，不放宽原有范围/日期/引用校验。

review.py 接口：`load_candidates(case_dir: Path) -> list[dict]`（返回项额外包含 scan_id）；`approve_proposals(case_dir: Path, batch: dict, accepted_ids: list[str]) -> dict`。review_render.py 提供 `write_review_cards(case_dir: Path, out: Path, *, force=False) -> Path`。加载候选使用 candidate_id_for 复核内容，不接受修改内容后仍保留旧 ID 的快照。

`approve_proposals` 先整批校验所有选中项，再写 `reviews/<batch_digest>.json` 准备记录，调用一次 import_evidence，最后把记录标为 committed 并保留 evidence IDs。准备记录失败则不导入；登记后回执失败则明确提示中断。相同内容重试必须幂等，先核对已经登记的 ID/内容，再补回执；不得生成重复证据。未选中的建议不改变账本。

CLI：`candidates CASE --out reports/cards` 生成只读 HTML 卡片；`review CASE --file proposals.json` 逐条展示原文、解释、依据和缺失项，询问 `a接收/s跳过/q结束`。只有 a 明确选择的项才交给 approve_proposals；q 保存此前已经选择的项；Ctrl-C 在提交前取消本轮选择。非交互 stdin 提示需终端审阅，返回2；不默认接收。测试注入 input/output，不打开浏览器。

HTML 对原文及属性转义，不执行嵌入内容，不加载外部脚本。每张卡片展示原帖、段落、日期原文、匹配提示及评论读取范围；候选数量与证据数量分别展示。

## F. 单入口与 Skill

`run CASE --company C --department D [--city ... --role ... --company-alias ... --search-term ... --source ... --limit 5 --timeout 20 --total-timeout 180]`：只接受新/空案例目录，复用 init 的其他目标参数；创建案例→扫描→候选卡片→两维报告。生成文件置于该案例下 `review/` 和 `report/`。输入校验先于写入；已有非空案例提示改用 scan/read，不覆盖。CLI 不自动启动浏览器，不自动批准提取建议。

启动前使用既有 channel_status 检查工具是否存在；installed_unchecked 只说明 CLI 已安装。终端明确说明连接/登录状态以实际读取为准，失败时提示 `opencli doctor`，不新增一套猜测上游输出的 doctor 解析器。

返回码：0=所选扫描完成（包括真实空结果）；3=部分失败、预算耗尽或未配置；2=输入/本地文件错误；130=中断。部分成功也生成卡片与报告。scan 已保存 interrupted 时，run 使用本轮扫描生成卡片/报告后返回130；中断早于扫描目录创建时只输出保留的案例路径，cards_path 为 null、report_paths 为空数组。pyproject 添加 `job-sherlock` console script，与原 reverse-check 指向同一 main；原命令保留。

Skill 使用 run/read→读候选段落→生成上述 proposals→逐项复核→用户在 review 接收→生成报告。无模型运行环境时，CLI 的扫描、卡片、既有手工 import 仍可用。仓库给一个虚构 proposals 示例及提取提示词，说明错误类型，不捆绑模型 SDK。

## G. 评测协议

新增 `pilot.py` 的 `evaluate_pilot(data: dict) -> dict` 和 CLI `evaluate --file INPUT --out reports/pilot`。输入：

- 顶层 `schema_version=1, cases=[], read_checks=[]`。
- case：`id, stratum(rich/sparse/ambiguous), manual, tool, top10, review_errors`。manual/tool 各为 `{eligible_origins: list[str]|null, active_seconds: number|null, setup_seconds: number|null}`；原始来源簇 ID 去重。null=未完成，空列表=审阅后无可用体验。
- top10 为最多10项 `{ref, team_relevant: bool|null, experience: bool|null}`；review_errors 为 `{wrong_team: int|null, question_as_fact: int|null, untraceable_quote: int|null}`。
- read_check：`id, channel, manual_readable: bool|null, body_ok: bool|null, comments_expected: bool, comments_ok: bool|null`。数值有限且非负，bool 不算数值，ID 不重复。

输出每个比率均含 numerator/denominator/unknown_count/value；分母0时 value=null。分别计算人工可读已判定样本的正文成功率、预期有评论且人工可读样本的评论成功率、已审 top10 相关率、全部已审 tool 案例覆盖率、人工有有效体验且双方已审的案例中 tool 的覆盖率。分层覆盖也必须输出。时间为有效成对样本的 `median(1-tool.active_seconds/manual.active_seconds)`，只计人工主动时间>0；首次设置时间单独统计。三个错误总数分别输出已审数与未审数。

虚构测试验证统计逻辑，不代表真实评测。真实试验先做3例可行性检查，再扩至20例；两边统一30分钟研究预算，记录首次设置成本，合并候选后人工复核。无参与者/账号/原文时记录未完成，不能编造分数。探索性继续投入参考门槛是：人工阳性案例中工具覆盖>=70%、主动时间中位减少>=30%、引用可回查、审阅未见跨团队归属及问句事实化；这是决策假设，不能保证总体可靠性。

## 完成状态

代码完成、平台实测通过、20例评测完成分开登记。脉脉评论布局未能验证时允许交付明确的 not_supported 状态，相关任务记为受限而非通过；其他来源和离线功能仍可继续。产品是否继续扩大投入，以真实评测为依据。
