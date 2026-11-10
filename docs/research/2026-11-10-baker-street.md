# Baker Street／“福尔摩斯项目”只读核查笔记

> 参考对象更正（2026-11-10）：用户已确认所指项目为 [sherlock-project/sherlock](https://github.com/sherlock-project/sherlock)。本文保留此前对同名候选的调研，不再将 Baker-Street 视作用户指定的参考项目。正确对象的 README 观察见 [Sherlock 调研记录](2026-11-10-sherlock-readme.md)。下文保留初次核查时的身份不确定性记录。

核查日期：2026-11-10。用途：为公司／部门工作氛围、工作强度反向背调项目提炼可借鉴的调查与审查机制。未执行上游安装器、技能、Python 工具或测试；以下不构成其运行效果验证。

## 结论与身份边界

`tywinlu1988/Baker-Street` 的中文 README 标题为“贝克街 221B — 福尔摩斯多视角分析框架”，技能入口名为 `sherlock`。它符合“福尔摩斯项目”的一种解释，但用户尚未提供唯一链接确认身份，不能把本次候选核查写成已确认来源。[中文 README][S1] [技能入口][S3]

本次将 `main` 固定在 **`a9a4d5828451c2c5efaa681c9d4ca242caa255aa`**，提交信息 `chore: bump version to 0.8.0`，提交时间 2026-09-03T08:08:12Z；`package.json` 版本为 0.8.0。除同名项目对照外，本文链接均固定在该提交，避免后续 main 改变造成描述漂移。[提交][S0] [包元数据][S13]

最重要的差异是：**README 的“并行独立角色分析”不是当前主技能的完整行为。v0.8 主技能要求规划角色依次执行，后续角色看到前序角色已经认领的研究方向，并避免重复；只有后面的评审轮明确并行。**因此只能说“角色使用独立 agent／fresh context”，不能说全流程严格相互盲法。[英文 README 第 39–51 行][S2] [主技能第 173–187、239–252 行][S3]

## 证据标签

- **仓库声明**：README、说明文档或注释声称的定位、架构、测试效果；不是本次测得结果。
- **执行规范**：`skill.md`、persona 和 prompt 中实际写出的指令；证明规则存在，不证明宿主代理始终遵守。
- **代码证实**：直接阅读安装器、打包器、harness 得到的确定性行为；本次未执行，不能进一步声称测试通过。
- **本项目推断／建议**：依据源码边界，为反向背调任务做出的设计判断，不归于上游作者。

## 文件索引

| 文件 | 本次核查内容 |
|---|---|
| [README_CN.md][S1]、[README.md][S2] | 定位、七种视角、独立分析声明、旧流程及评估说明 |
| [.claude/skills/sherlock/skill.md][S3] | 当前主编排、失败降级、证据编号、合成与打包 |
| [scout-prompt.md][S4] | 侦察的问题解构与未知项 |
| [research-prompt.md][S5] | 事实 JSON、来源、置信度、反证、增量保存 |
| [personas/holmes.md][P1]、[watson.md][P2]、[mycroft.md][P3]、[moriarty.md][P4]、[adler.md][P5]、[lestrade.md][P6]、[hound.md][P7] | 视角、盲点、事实约束、规划卡、数据评审 |
| [quantitative-agent-prompt.md][S6] | 可复现计算、输入假设、限制与部分完成 |
| [tools/packaging/make_run_package.py][S7] | F 编号、来源清单、原始产物归档 |
| [tools/testing/pipeline_harness.py][S8] | 产物结构、覆盖、标注、多样性与计算检查 |
| [tools/verification/fact_verifier.py][S9] | 来源字段、置信度与反证比例的基础统计 |
| [judge.md][S10]、[validate.md][S11] | LLM 评分、基线／单提示词／完整管道对照方案 |
| [CROSS_PLATFORM.md][S12]、[install.js][S14]、[tool-map.json][S15]、[platforms/codex.json][S16] | 平台声明与安装实际行为 |
| [LICENSE][S17] | MIT 条款 |

## 当前主技能要求的编排步骤

以下是**执行规范**，不是在本机重现的实际运行记录。主编排集中在 Markdown 指令中；检查到的 Python 负责计算、产物校验和打包，安装器负责复制技能目录，不能把此仓库当成已经独立实现的通用 agent runtime。[主技能][S3] [仓库树][S18]

1. **双轨摄入（Phase 0）**：一轨澄清问题、建议深度与角色，另一轨立即派一个 scout。scout 只列最多 5 个子问题、关键未知、建议角度，不形成答案；查找超过 30 秒则记未知项。普通模式要求配置确认、合并问题图后再次确认；`--auto` 跳过对话，但仍派 scout，并直接进入研究。[主技能第 21–66 行][S3] [scout][S4]
2. **形成研究任务（Phase 1.1）**：从问题图合成简报，列 2–4 个优先事实领域、具体问题和覆盖要求；检查每个 scout 子问题是否覆盖，未覆盖项在报告中明示。只传合成简报，不直接把 scout 原文当研究指令。[主技能第 87–97 行][S3]
3. **调研与门禁（Phase 1.2–1.3）**：`light/standard/deep` 对应 1／2／3 个研究 agent；每个目标 15–30 条 JSON 事实。要求 JSON 可解析、每 agent 至少 5 条、至少 60% 有来源、平均置信度至少 0.5。失败时合并可用部分、最多一次研究重派，或降级为空事实库并明示。[主技能第 99–135 行][S3]
4. **共享事实库（Phase 1.4）**：合并、语义去重、保留较高置信度项，再输出规范的 `fact-base.json` 和 `sources.md`。每条事实分配 `F001…`；所有角色获得完整事实库。反证占比不足 8% 时加派一次专门寻找反证的研究 agent；仍不足就记录缺口。语义去重是编排器的指令，打包代码本身没有实现语义去重。[主技能第 137–155 行][S3] [打包器第 63–83 行][S7]
5. **角色规划（Phase 2）**：按问题类型选 quick 2 个、standard 3 个、deep 全部 7 个角色；完整传递 persona 文件。v0.8 按调度表顺序逐个运行，每个输出 2–3 个研究／计算方向和预期分歧，后序角色接收已认领方向列表，重复不可避免则标 `[ECHO]`。无角色 baseline 与第一个角色并行，接受同一原问题及事实库。将各规划卡去重合成 `quant-demands.json`，合并需求保留所有发起角色。[主技能第 157–193 行][S3]
6. **量化及独立复算（Phase 3／3.5）**：单个量化 agent 在需求表完成后执行计算，写带 `Q001…` 的共享分析包；允许一次仅针对遗漏需求的重试，保留 partial 状态。另派验证 agent 选 1–3 个对结论最关键的结果，用不同方法重新推导，结果标 `verified/diverged/unverifiable`，分歧不得隐藏。这里的“独立复算”主要校验计算，不等于独立验证原始输入来源。[主技能第 195–237 行][S3] [量化 prompt][S6]
7. **角色数据评审（Phase 4）**：每角色一个 fresh agent，并行接收完整 persona、自己的规划卡、分析包及原问题；每方向写短评，标 `[DATA: CONFIRMED]`、`[DATA: REVISED]` 或 `[DATA: UNSUPPORTED]`。缺失需求必须 UNSUPPORTED；评审失败不重试，报告列出未复核角色。主技能此处的派发清单未再次明确列出共享事实库，尽管此前全局规定和 persona 约束要求事实只能来自该库；实现时需要显式补齐上下文合同。[主技能第 239–252 行][S3] [Holmes 的事实约束][P1]
8. **追加量化（Phase 4.5）**：除主量化包完全不可用外，v0.8 要求恰好一轮 consolidation。有角色 follow-up 就执行，没有则编排器从分歧／缺口提炼一个需求。新结果追加 Q 编号，但不会重新经过 Phase 3.5 验证，应标 unverified。[主技能第 254–270 行][S3]
9. **合成（Phase 5）**：列最关键的 2–3 个实质分歧，分别写两种立场与能判别它们的 F/Q 证据；证据无法判别就说明无法判别。无实质分歧时承认可能共识清楚、框架增益有限。汇总没有角色覆盖的维度，同时检查 baseline 是否包含角色都遗漏的角度，再给下一步动作。[主技能第 272–307 行][S3]
10. **报告与归档（Phase 6–7）**：报告含 baseline 对照、证据附录、失败和覆盖信息、质量限制。每条核心结论映射 F-id／Q-id；无法溯源的写“模型推断，无事实库支撑”。交付后将报告、来源、研究原稿、规划卡、评审、量化包和日志归档到 `sherlock-runs/<时间戳>/`，并处理可能迟到的 agent 产物。[主技能第 309–493 行][S3] [打包器第 98–171 行][S7]

## 共享证据与“独立分析”究竟保障了什么

**执行规范**：研究 agent 不给建议，只收集带 `claim/source/confidence` 的可核查陈述，可另加 `type: counter-evidence`；敏感于时间的陈述应含日期。每人至少两条挑战提问前提的反证；每完成一个研究领域便增量保存。persona 的事实约束禁止用训练记忆补充具体领域事实，缺失项列为 gap，0.5–0.6 置信度只视为提示性材料。[研究 prompt 第 13–45 行][S5] [persona 事实约束示例][P1]

**限制**：该事实 JSON 同时容纳“合理推断”“猜测”等低置信度项，`source` 也可写 `computed`，并非所有记录都是已验证事实。它没有强制保存原文摘录、网页发布时间、采集时间、公司／部门／地点／岗位、观察区间或转载关系；这些缺口不能靠字段名 `fact` 或高置信度消除。[研究 prompt 第 13–33 行][S5]

**独立性分层**：研究层有多个 agent，但简报及事实库是共享的；规划层 v0.8 共享前序研究方向，存在顺序依赖；评审层是 fresh agent 并行，但全部看到同一个量化包。后者有利于对同一证据校验立场，不提供完全独立的证据发现。README 的“互不知道对方想什么”应当降格为历史设计声明。[主技能第 106–114、173–187、241–248 行][S3] [README 第 47 行][S2]

**规范内部张力**：Adler 的工具建议允许事实库缺少社交资料时自行查找；同一文件又禁止把事实库以外的领域事实作为证据。主技能没有明确新增证据如何重新入库、审查、编号再广播。因此本项目应统一为“新增来源先进入待审证据池，通过后生成新版本事实库”，不能由某个角色直接悄悄扩展自己的事实前提。[Adler 第 28–43 行][P5]

## 七个 persona 的作用与局限

下表是对各 persona 的**执行规范概括**；最后一列是**本项目建议**，不表示角色能诊断个人动机或证明组织事实。

| persona | 上游视角及自认盲点 | 可改写为反向背调检查问题 |
|---|---|---|
| Holmes | 多假设排除、异常与证据链；弱于情感和常识 | 同名公司／业务线是否混淆？加班传闻还有什么解释？[P1] |
| Watson | 日常经验、普通解释；易漏罕见情况 | 真实一周怎样安排？岗位职责和通勤如何影响体验？[P2] |
| Mycroft | 系统、激励、结构；易漏执行细节和个体差异 | 问题来自公司制度、业务周期还是某部门管理？[P3] |
| Moriarty | 激励与对抗性压力测试；偏向恶意／自利假设 | 招聘宣传和匿名差评分别有什么选择性表达动机？[P4] |
| Adler | 关系、权力、未表明的需求；可能过度心理化 | 汇报关系、决策方式、跨团队冲突有什么可观察证据？[P5] |
| Lestrade | 可证实、可执行、流程；可能排斥无先例信息 | 哪个结论仍需面试追问或可重复核查？[P6] |
| Hound | 恐惧、偏见、群体思维；可能制造过度猜疑 | 用户是否只搜到负面材料？缺少哪些反例或普通样本？[P7] |

不宜直接继承“推断隐藏动机”“默认恶意”等角色语言来评价具体员工或部门。更可取的是保留可证伪的检查问题、观察边界与证据要求；这是本项目的设计判断。[Moriarty 盲点][P4] [Adler 方法与盲点][P5] [Hound 盲点][P7]

## 冲突处理与质量校验：指令、代码与空白

**证据冲突与观点冲突要分开。** README 将观点分歧分为假设、权重与因果解读，并写有 Top-2 冲突回注；当前主技能则以规划卡预期分歧、数据评审标注、追加计算和判别证据为中心，未规定 README 所述双方互相反驳的独立回注轮。不能把旧 README 的 rebuttal 流程当成 v0.8 已要求步骤。[中文 README 第 94–104、359–377 行][S1] [主技能 Phase 4.5–5][S3]

**代码证实的检查范围：**

- `fact_verifier.py` 实际检查来源字段是否非空且不是 `computed`、置信度分布、反证标签比例、声明前 8 个空白分隔词的粗略重复指纹。它不会发起网络请求，不会检查 URL 可访问、原文是否支持陈述、来源是否可信，也没有实现注释声称的实质跨事实一致性核查。[第 12–57 行][S9]
- `make_run_package.py` 按置信度排序并分配 F 编号，写来源表；打包时保留各研究 agent 原始 JSON、事实库、需求、量化包、日志、baseline、scout、角色产物和已声明脚本。它并不核实来源真实性。[第 20–83、98–171 行][S7]
- F 编号是该次事实库生成时的排序编号。每次重新生成都会重排／重写，不是跨版本永久稳定的证据主键。用于本项目时应另设不可变 source／claim ID，再给单次报告分配显示编号。[第 63–83 行][S7]
- `pipeline_harness.py` 检查需求形状和发起角色覆盖、量化包基本字段、规划卡存在且不超过 600 个空白分隔词、评审是否存在且至少有一处 DATA 标注。它没有逐条核实每个方向都得到正确 DATA 标注；量化需求覆盖在这里主要按 `requested_by` 的角色计算，不等于逐项 demand ID 校验。[第 36–93、271–315 行][S8]
- 多样性程序将方向转为字符二元组，按 containment ≥0.65 贪心聚类，明确称为措辞差异下限；语义多样性是编排器另写 JSON，harness 检查其计数一致性，不能称为客观证明了语义独立。[第 319–361、455–478 行][S8]
- 数值检查包括部分概率字段范围、分位数顺序和均值区间等；`check_run` 会记录量化不变量、验证状态和语义多样性，但这些在该函数中未并入 overall pass。`pass: true` 不代表所有数量检查、事实真实性或独立复算都通过。[第 386–478、504–545 行][S8]

**仓库声明／评估方案**：`judge.md` 让 LLM 评新颖性、角色保真度、严谨性、冲突、行动性等；`validate.md` 设计裸模型、单提示词多视角、standard／deep 管道等对照，并报告 harness 失败。README 还提供旧版实测数字，但本次未找到并复核其完整原始运行包，未重做测试，因此不把成功率、增益率或“证明质量更好”当成已核实结论。部分文件仍标 v0.7.x，README 也保留旧流程，迁移时以固定版本逐文件核对。[judge][S10] [validate][S11] [README_CN 评估章节][S1]

## 平台支持核查

| 层面 | 核查结果 |
|---|---|
| 仓库声明 | `CROSS_PLATFORM.md` 列 Claude Code、Codex CLI、Antigravity、Cursor，声称通过通用工具名和映射支持平台。[S12] |
| 代码证实 | `install.js` 解析 `--platform`，选择用户家目录下对应 skills/sherlock 路径，递归复制同一套技能文件，读取 tool-map 并打印两项映射；已有目录且未 force 时退出。没有模板替换、API 调用转换或 agent 调度实现。[第 24–34、61–114 行][S14] |
| 静态配置 | `tool-map.json` 有四平台工具映射，`platforms/codex.json` 指向 `skill.md`，但 Codex manifest 仍标 0.6.3。[S15] [S16] |
| 本项目判断 | 这些文件证明有安装路径与适配意图，不能证明本次 Codex desktop 的工具名、权限、并行机制、引用接口与上游假设兼容。本次没有安装或进行任何平台端到端验收。 |

`CROSS_PLATFORM.md` 声称所有 prompt 没有平台专用工具名，但研究和 scout prompt 仍列 `Read`，旧 README 也使用 WebFetch/Bash 等。主技能还假设仓库相对路径 `.claude/skills/sherlock/`；安装到家目录后如何解析，需要宿主适配。不能依赖“换个平台名称就可运行”的文档表述。[跨平台说明第 16、69–71 行][S12] [research 第 9 行][S5] [scout 第 7 行][S4] [主技能路径约定][S3]

## 对反向背调项目的取舍建议

以下全部是**本项目推断／建议**，不是上游已有功能。

适合借鉴：

1. **问题拆解先于结论**：先锁定公司实体、城市、部门、岗位、时间范围、用户最在意的工作体验，再分配来源任务；不全凭公司名输出泛化评分。参考 scout 与简报覆盖检查。[S3] [S4]
2. **证据收集和立场分析分离**：先生成共享证据版本，再让工作强度、管理／协作、薪酬兑现、偏差审查等维度分析。每个分析使用同一版本证据，新增材料进入待审池。[S3] [S5]
3. **结论到来源的可检查链**：结论挂 claim ID、原文摘录、来源地址、发布时间、采集时间、适用实体／部门／岗位／观察区间；标直接观察、转述、推断及核查状态。F/Q 形式可借，字段要补充。[S5] [S7]
4. **不足即不足**：保留 UNKNOWN／UNSUPPORTED／冲突未解决，列“什么新证据会改变结论”和可以在面试中验证的问题；失败和缺口属于交付的一部分。[S3] [P6]
5. **保存原始材料与运行日志**：在输出可读报告之外，保存来源快照元数据、提取记录、去重关系、分析版本与失败日志，允许重查。上游归档方式提供了小规模原型。[S7]
6. **验证多角色是否值得**：用同一证据版本的直接分析作 baseline，检查多角色是否增加了真实部门差异、反例和可核查问题，不以字数、分歧数量或工具次数奖励复杂度。[S3] [S11]

不宜直接照搬：

1. **固定反证比例和事实条数**：8%、15–30 条及“至少两条反证”只能作查找提醒。它们没有度量真实性、独立来源数、时效与相关性；为了过门禁凑反证会扭曲背调。应检查是否充分检索相反解释，并允许“未找到可靠反例”。[S3] [S5]
2. **公司官方来源自动高置信度**：research 的评分表将官方公司陈述列在 0.9–1.0 档，但官方宣传可可靠证明“公司这样说”，未必能证明“实际加班少”。匿名经历也要单独判断岗位、时间、可核查细节及转载关系；来源权威和陈述支持程度应分开。[S5]
3. **低信息情境强制量化**：v0.8 除无主包外总要追加一轮计算，可能把零散评论转换成看似精确的概率。反向背调应先检查样本／分母／观察区间；没有可算数据就停止量化，保留定性证据边界。[S3] [S6]
4. **用调度制造“独立”或分歧**：后序角色为避免重复而放弃最强方向，会产生顺序效应；共享包也会形成共同锚点。若产品承诺独立审查，应先盲法出稿、冻结，再互审；不要强行制造与证据无关的争议。[S3]
5. **语义去重只留最高置信度项**：部门、岗位和时间差异可能只是表面相似；转载还可能制造虚假多源。应保留原始记录、来源血缘及支持／冲突关系，聚合时按适用范围合并，不覆盖异议。[S3] [S7]
6. **信任字段或通过标志替代核查**：非空 source、作者自评 confidence、harness pass、LLM-as-Judge 分数不能替代“原文是否真正支持这条结论”的检查。[S8] [S9] [S10]
7. **共享 skill 目录作为运行工作区**：上游先把产物写在 `.claude/skills/sherlock/` 再移动。多份背调同时执行时应从开始就分离 run ID 目录，避免覆盖、串案和迟到写入；此为根据路径与迟到 agent 处理规定推得的并发风险，并非本次复现的缺陷。[S3] [S7]

## 许可证

固定提交的 `LICENSE` 为 MIT，署名 `Copyright (c) 2026 Tywin Lu`；复用其代码或实质性文档内容，应按许可证保留版权及许可声明。该许可证覆盖仓库软件及文档，不代表能据此转载外部网站的评论内容。[许可证原文][S17]

## 两个同名项目：只作定位排除

- **`trilogy-group/cc-skills-sherlock`**：搜索引擎缓存的第一方 GitHub README 将其称为 Sherlock V2／V2.1，定位是 Claude Code 深度调研插件，以 beads 依赖图并行调查、验证 claims、输出有来源的 Markdown／CSV，支持恢复与转向。它更接近“调查编排”，不是 Baker Street 的七角色思考框架。**当前核查受限**：GitHub connector `get_repo` 返回 404，直接网页 open 和 main 原始 README 也 404，公开 API shell 返回限流；无法取得当前 commit，不能确认仓库仍公开、现状或运行实现。这里只依据搜索缓存中的仓库 README 做低强度定位，不能据此确证用户所指项目。[仓库页／缓存索引入口](https://github.com/trilogy-group/cc-skills-sherlock)
- **`sherlock-project/sherlock`**：当前可读固定提交为 `c588d7c8b476df9f9c84912a05d1430fb8cdcdae`，第一方 `docs/README.md` 定位是跨社交平台按用户名查找账户的命令行工具；它不是公司氛围调研、多角色分析或事实审查框架。此项目不应被混同为本任务所需的“福尔摩斯”方案。[固定版本 README](https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/docs/README.md)

## 获取方式与未完成的验证

主要材料通过已连接的 GitHub 工具读取固定提交的文件与递归树；同名项目读取失败后，只读访问公开网页、搜索缓存及 `urllib` 获取原始地址。未复制或运行上游安装命令，未安装 beads／gogcli 等依赖，未对真实公司或个人开展调查，未执行上游测试，也未验证模型质量承诺。身份确认仍需要用户提供原项目链接或明确项目特征。

[S0]: https://github.com/tywinlu1988/Baker-Street/commit/a9a4d5828451c2c5efaa681c9d4ca242caa255aa
[S1]: https://github.com/tywinlu1988/Baker-Street/blob/a9a4d5828451c2c5efaa681c9d4ca242caa255aa/README_CN.md
[S2]: https://github.com/tywinlu1988/Baker-Street/blob/a9a4d5828451c2c5efaa681c9d4ca242caa255aa/README.md
[S3]: https://github.com/tywinlu1988/Baker-Street/blob/a9a4d5828451c2c5efaa681c9d4ca242caa255aa/.claude/skills/sherlock/skill.md
[S4]: https://github.com/tywinlu1988/Baker-Street/blob/a9a4d5828451c2c5efaa681c9d4ca242caa255aa/.claude/skills/sherlock/scout-prompt.md
[S5]: https://github.com/tywinlu1988/Baker-Street/blob/a9a4d5828451c2c5efaa681c9d4ca242caa255aa/.claude/skills/sherlock/research-prompt.md
[S6]: https://github.com/tywinlu1988/Baker-Street/blob/a9a4d5828451c2c5efaa681c9d4ca242caa255aa/.claude/skills/sherlock/quantitative-agent-prompt.md
[S7]: https://github.com/tywinlu1988/Baker-Street/blob/a9a4d5828451c2c5efaa681c9d4ca242caa255aa/.claude/skills/sherlock/tools/packaging/make_run_package.py
[S8]: https://github.com/tywinlu1988/Baker-Street/blob/a9a4d5828451c2c5efaa681c9d4ca242caa255aa/.claude/skills/sherlock/tools/testing/pipeline_harness.py
[S9]: https://github.com/tywinlu1988/Baker-Street/blob/a9a4d5828451c2c5efaa681c9d4ca242caa255aa/.claude/skills/sherlock/tools/verification/fact_verifier.py
[S10]: https://github.com/tywinlu1988/Baker-Street/blob/a9a4d5828451c2c5efaa681c9d4ca242caa255aa/.claude/skills/sherlock/judge.md
[S11]: https://github.com/tywinlu1988/Baker-Street/blob/a9a4d5828451c2c5efaa681c9d4ca242caa255aa/.claude/skills/sherlock/validate.md
[S12]: https://github.com/tywinlu1988/Baker-Street/blob/a9a4d5828451c2c5efaa681c9d4ca242caa255aa/CROSS_PLATFORM.md
[S13]: https://github.com/tywinlu1988/Baker-Street/blob/a9a4d5828451c2c5efaa681c9d4ca242caa255aa/package.json
[S14]: https://github.com/tywinlu1988/Baker-Street/blob/a9a4d5828451c2c5efaa681c9d4ca242caa255aa/install.js
[S15]: https://github.com/tywinlu1988/Baker-Street/blob/a9a4d5828451c2c5efaa681c9d4ca242caa255aa/.claude/skills/sherlock/tool-map.json
[S16]: https://github.com/tywinlu1988/Baker-Street/blob/a9a4d5828451c2c5efaa681c9d4ca242caa255aa/.claude/skills/sherlock/platforms/codex.json
[S17]: https://github.com/tywinlu1988/Baker-Street/blob/a9a4d5828451c2c5efaa681c9d4ca242caa255aa/LICENSE
[S18]: https://github.com/tywinlu1988/Baker-Street/tree/a9a4d5828451c2c5efaa681c9d4ca242caa255aa
[P1]: https://github.com/tywinlu1988/Baker-Street/blob/a9a4d5828451c2c5efaa681c9d4ca242caa255aa/.claude/skills/sherlock/personas/holmes.md
[P2]: https://github.com/tywinlu1988/Baker-Street/blob/a9a4d5828451c2c5efaa681c9d4ca242caa255aa/.claude/skills/sherlock/personas/watson.md
[P3]: https://github.com/tywinlu1988/Baker-Street/blob/a9a4d5828451c2c5efaa681c9d4ca242caa255aa/.claude/skills/sherlock/personas/mycroft.md
[P4]: https://github.com/tywinlu1988/Baker-Street/blob/a9a4d5828451c2c5efaa681c9d4ca242caa255aa/.claude/skills/sherlock/personas/moriarty.md
[P5]: https://github.com/tywinlu1988/Baker-Street/blob/a9a4d5828451c2c5efaa681c9d4ca242caa255aa/.claude/skills/sherlock/personas/adler.md
[P6]: https://github.com/tywinlu1988/Baker-Street/blob/a9a4d5828451c2c5efaa681c9d4ca242caa255aa/.claude/skills/sherlock/personas/lestrade.md
[P7]: https://github.com/tywinlu1988/Baker-Street/blob/a9a4d5828451c2c5efaa681c9d4ca242caa255aa/.claude/skills/sherlock/personas/hound.md
