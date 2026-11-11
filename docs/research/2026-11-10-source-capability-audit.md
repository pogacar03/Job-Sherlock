# 求职侦探采集能力核查与平台接入调研

核查日期：2026-11-10。代码基线：`0259d74`。本次只核查能力、读取公开资料和记录研究结果，没有新增连接器、安装浏览器扩展或使用用户的社区登录会话。以下优先级是研究后的建议，不能当作已实现功能。

## 当前产品实际做到哪一步

运行 `python3 -m reverse_check --help`，当前子命令为 `init / plan / sources / collect / import / report / demo`。项目已经是 CLI；还没有输入公司后自动发现、读取多个平台内容的 `scan` 功能。

- [来源表](../../reverse_check/data/sources.json)包含 5 个具名平台：牛客、知乎、脉脉、小红书、看准，以及一个通用公开网页回退项。它不是 6 个独立数据连接器。
- 牛客和知乎使用通用 HTTP GET 与可见文本提取，不是专门的站内搜索适配器；是否能读取取决于实际页面。
- 脉脉、小红书、看准是 `manual`，采集器只登记 `manual_required`，不发起读取请求。
- [来源查询代码](../../reverse_check/sources.py)生成 `site:` 检索文本，不执行搜索；[CLI](../../reverse_check/__main__.py)的 `collect` 要求预先提供 `--urls`。
- [正文提取](../../reverse_check/collection.py)只接受 HTML、XHTML、纯文本；没有 JSON 数据接口、PDF/XLSX 解析或 JavaScript 渲染功能。
- 当前线索发现主要依靠宿主搜索工具。网页原文保存、证据导入、报告生成已实现，但不能因此声称已经具备自动多平台背调能力。

## 用现有采集器做的真实请求

测试在临时案例目录调用实际 `collect_sources`，使用真实网络请求，没有替换 fetch。测试案例仅用于能力核查；临时响应没有保留，以下是执行时读出的状态与摘要，不是企业背调结论。

| 请求 | HTTP / 类型 | 现有程序结果 | 说明 |
|---|---|---|---|
| [955.WLB 原始 README](https://raw.githubusercontent.com/formulahendry/955.WLB/master/README.md) | 200 / text/plain | `retrieved` | 已知 URL 的原文读取可用，但没有公司条目解析器，也不会主动发现名单。 |
| [Greenhouse Airbnb 招聘列表](https://boards-api.greenhouse.io/v1/boards/airbnb/jobs) | 200 / application/json | `unsupported_content` | 响应实际包含 205 条职位；测试脚本另行解析快照确认。现有产品尚不能消费这些结构化记录。职位数量是此次快照，随时间变化。 |
| [Lever 文档示例组织的招聘列表](https://api.lever.co/v0/postings/lever?mode=json) | 200 / application/json | `unsupported_content` | 响应是空数组。合法空结果和无法解析是两回事，未来连接器应分别报告。 |
| [Greenhouse 文档示例 vaulttec](https://boards-api.greenhouse.io/v1/boards/vaulttec/jobs) | 404 / application/json | `not_found` | 文档中的演示组织不保证是真实可用的数据板；不能用演示 URL 判断服务是否可用。 |

Greenhouse 的[官方 Job Board API 文档](https://docs.greenhouse.io/job-board)明确 GET 公开岗位接口不需要认证，提供职位、办公室和部门数据。[Lever Postings API](https://github.com/lever/postings-api)和 [Ashby 公开职位 API](https://developers.ashbyhq.com/docs/public-job-posting-api)也有真实结构化接入路线。本次未实测 Ashby。这些来源适合确认岗位、团队称呼、地点与公司公开要求，不能据此推断实际下班时间、人员流失原因或领导风格。

## 比继续增加搜索模板更有价值的项目

### OpenCLI：优先核查的平台读取后端

[官方仓库 jackwener/OpenCLI](https://github.com/jackwener/OpenCLI)通过 Chrome 扩展和本地 daemon 提供浏览器操作与站点命令。已查看实际适配器，而非只看支持平台列表：

- [牛客 search](https://github.com/jackwener/OpenCLI/blob/main/clis/nowcoder/search.js)有关键词、类型和数量参数，输出帖子 URL、标题、内容、时间、评论数等字段；[detail](https://github.com/jackwener/OpenCLI/blob/main/clis/nowcoder/detail.js)按搜索返回的 ID/URL 读取详情。源码声明 browser 与 COOKIE 策略。
- [知乎 search](https://github.com/jackwener/OpenCLI/blob/main/clis/zhihu/search.js)确有站内搜索结果解析和访问失败处理；目录还有回答详情与评论读取命令。
- [小红书 search](https://github.com/jackwener/OpenCLI/blob/main/clis/xiaohongshu/search.js)从站内渲染 DOM 读取结果，并区分登录墙与安全限制；[note](https://github.com/jackwener/OpenCLI/blob/main/clis/xiaohongshu/note.js)读取笔记内容，目录另有 comments。
- [脉脉 search-talents](https://github.com/jackwener/OpenCLI/blob/main/clis/maimai/search-talents.js)是候选人检索，不是职言/匿名帖子搜索。不能因为存在 maimai 目录，就声称能查脉脉工作氛围。

这条路线能获取通用搜索没有索引的站内结果，但需要本地运行条件、适当的登录会话，并受平台限制。当前机器未找到 `opencli` 命令，本次没有运行上述平台命令，因此只能声称“源码支持”，不能声称已接通或稳定可用。上游[许可证](https://github.com/jackwener/OpenCLI/blob/main/LICENSE)为 Apache-2.0。

### Agent-Reach：平台工具的安装、诊断和路由

[官方 README](https://github.com/Panniantong/Agent-Reach)区分默认、可选及实验渠道，描述 V2EX、GitHub、视频字幕、Reddit、小红书等读取入口；部分渠道需要登录或外部服务密钥。其[小红书渠道源码](https://github.com/Panniantong/Agent-Reach/blob/main/agent_reach/channels/xiaohongshu.py)实际调用 OpenCLI 的 search/note 等命令，不是一个额外独立的员工证据来源。

适合参考渠道状态诊断和后端路由；不应在求职侦探中重复安装同一后端。当前机器未找到 `agent-reach` 命令，本次没有安装，也没有运行渠道体检。

### MediaCrawler：采集搜索结果、正文和评论

[官方 README](https://github.com/NanmiCoder/MediaCrawler)和源码描述小红书、知乎、微博、B 站等平台搜索、帖子、评论及浏览器登录态。这比 `site:` 搜索模板更接近平台采集器，但没有因此自动得到可信的部门判断。[当前许可证](https://github.com/NanmiCoder/MediaCrawler/blob/main/LICENSE)限制为非商业学习研究用途，不能直接当作可任意商业集成的依赖。本次没有安装或运行。

### JobSpy：岗位聚合，不能替代员工评论

[官方 README](https://github.com/speedyapply/JobSpy)提供 Python 库、CLI 和 MCP 接入，聚合 LinkedIn、Indeed、Glassdoor 等平台的职位。已核对目录确有各站点适配器。这里的 Glassdoor 支持指招聘岗位，不是已经获得员工评价；不能把职位抓取能力宣传成氛围背调能力。本次只读源码，未执行采集。

### 其他对照

- [Sherlock](https://github.com/sherlock-project/sherlock/blob/master/docs/README.md)：`sherlock user123` 的确是终端命令；源码使用站点 URL 规则及响应判定。任务是用户名对应账号的发现，不能直接解决部门体验调查。
- [Maigret](https://github.com/soxoj/maigret)：用户名检索、站点筛选、资料提取和报告，仍是个人账号 OSINT，对当前雇主体验目标不是优先数据源。
- [SpiderFoot](https://github.com/smicallef/spiderfoot)：适合参考独立来源模块、事件关联、状态与出处保存；域名/IP 等侦察结果不等于员工体验。
- [career-radar](https://github.com/Lyb-L-dev/career-radar/blob/master/README.md)：更接近求职场景，README 描述官网岗位监测，以及借助 Agent-Reach/OpenCLI 的手动触发口碑调查。本次只核对 README，未运行其实现，不据此推荐成熟度。

名单、公司监管记录、裁员通知等来源详见[另一份项目核查](2026-11-10-employer-osint-projects.md)。

## 建议的实施次序与验收依据

1. **先补员工原文发现与读取。** 首选核实牛客、知乎、小红书的 OpenCLI 读取链路；脉脉职言、看准仍明确标记未接通，保留授权材料导入。验收是给定关键词返回真实原文 URL、正文及可用时间信息，不能只返回搜索链接。
2. **再补直接文件与岗位 API。** 解析 955/996 名单条目、证据链接、时间和原始文件版本；实现公开岗位 JSON 适配器。名单只生成待核实线索，官方 JD 只支持官方表述相关观察。
3. **补充公司风险背景。** 对适用主体读取监管记录、裁员通知文件，按法定主体和地区匹配；不将集团记录归因到某个团队。经营风险与工作氛围分别呈现。
4. **统一 CLI 调度。** 在现有命令上增加自动发现与读取的入口，先检查各后端是否安装、连接、登录，再运行可用来源。报告分别列出：已成功查询但零结果、访问受限、未配置、待审阅、已用于结论；这些状态不能合并。

来源模块应各自负责发现、原文读取、标准化和状态记录，保存出处及快照。对同一帖子被搜索、OpenCLI、转载名单重复返回的情况按原始来源去重。扩大来源后仍须匹配公司别名、业务线、部门、城市、岗位和体验时间；多来源不自动等于多份独立证据。

Multi-agent 可以分工读取和核验，但不会扩大任何工具自身的访问能力。当前最需要补的是接入和解析，而不是增加 Agent 数量。
