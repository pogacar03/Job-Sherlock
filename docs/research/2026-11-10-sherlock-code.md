# Sherlock 实际代码核查与原文采集改造依据

核查日期：2026-11-10。参考对象为用户确认的 [sherlock-project/sherlock](https://github.com/sherlock-project/sherlock)，固定提交 **`c588d7c8b476df9f9c84912a05d1430fb8cdcdae`**，提交信息 `update banner layout`，GitHub 返回提交时间为 2026-11-01T17:41:43Z。[提交记录][C]

本次通过 GitHub 连接器直接读取 `sites.py`、`sherlock.py`、`result.py` 和 `resources/data.json`，以原文件的一基行号建立链接。没有运行上游脚本、安装器、测试或账号探测。下文“代码事实”来自静态阅读，“本项目建议”是针对公司／部门反向背调的设计判断，不是上游已实现的功能，也不构成运行效果验证。

## 核心结论

Sherlock 的实际核心是**站点注册表、并发 HTTP 探测和明确的结果状态**。单个 `sherlock()` 调用按用户名构建各站请求，再分类结果；入口按顺序处理多个用户名。这里没有多 Agent 调研编排。[并发与请求][S1] [多用户名入口][S2]

可借鉴其“数据配置驱动请求、采集过程保留失败状态”的组织方式。公司／部门调查需要读取并保存具体原文，再核实范围、时间和出处；**账号存在、同名账号、HTTP 成功、网站数量，都不是加班或团队氛围证据**。Sherlock 的 `QueryResult` 记录的是用户名、站点、URL、探测状态、耗时和上下文，本身没有员工经历、公司部门匹配或原文支持关系。[结果结构][R1]

## 1. 来源注册表与校验

**代码事实：**

- 默认注册表来自 `https://data.sherlockproject.xyz`；也可指定本地 JSON 或 HTTP 开头的地址。远端请求超时 30 秒，非 200 视为读取失败，JSON 解析异常单独报告；本地文件使用 `json.load`。因此固定代码提交并不固定默认运行时注册表。[来源加载][T1]
- 加载器移除 `$schema` 后直接迭代条目，构造对象时读取 `urlMain`、`url`、`username_claimed`，缺失键抛出 `ValueError`，部分类型错误打印后跳过。**这个运行路径没有调用 JSON Schema 校验器**，也没有在此完整验证 URL 模板、请求方法或探测字段。[构造与校验边界][T2]
- 默认另读实时 `exclusions` 分支的排除列表，超时 10 秒，按名字删掉已知问题站点；显式指定站点可保留。请求异常时打印警告并继续，非 200 则直接不应用列表。它是失效来源的运营机制，但远端排除表不可用会降低这一层保护。[排除表地址][T0] [应用与降级][T3]
- `--local` 使用包内 `resources/data.json` 并关闭排除表；`--json` 还可接受 PR 编号，获取其 head SHA 后拼出注册表地址。因此复现记录应同时保存代码版本、实际注册表与排除表快照／摘要及有效配置。[入口选择][S3]
- `username_claimed` 保存已知占用的样例；`username_unclaimed` 在对象内随机生成。对象构造本身没有联网验证这些正反样例。不能把存在样例字段理解为每次执行已校准探测规则。[样例保存][T4]

代表性字段与实际用途如下，仅列少量条目，不复制整份来源清单。

| 代表条目 | 字段与用途 | 固定版本位置 |
|---|---|---|
| 1337x | `errorType: message`、`errorMsg` 数组、`regexCheck`、`url`、`urlMain`、`username_claimed` | [data.json 3–13 行][D1] |
| Anilist | `request_method: POST`、嵌套 `request_payload`、`urlProbe`；展示页面和探测接口可以不同 | [96–110 行][D2] |
| Avizo | `errorType: response_url`、`errorUrl`；字段存在不等于当前分类器会读取它 | [202–208 行][D3] |
| Discord | 自定义 `headers`、POST payload；`errorMsg` 同时含“用户名未占用”和“被限流”文本 | [722–735 行][D4] |
| Slides | `errorCode: 204`，允许把特定 2xx 状态作为未发现规则 | [2243–2249 行][D5] |

**本项目建议：**注册表应描述来源 ID、域名、原文 URL、读取方式和已知访问限制。输入应是搜索得到或用户提供的文章／帖子地址，而不是把公司名代入个人用户名模板。注册表应独立校验并保留本地版本；未知字段、无效 URL、重复 ID、无效请求配置应在联网前报错。

## 2. 并发请求与数据流

**代码事实：**同一用户名下的并发上限为站点数和 20 的较小值。先遍历所有站点提交 future，再按注册表顺序取 `future.result()`；请求在并行执行，但结果消费没有使用 `as_completed`，前面的慢站点会延迟后面的结果通知。[线程会话][S1] [结果消费][S4]

每站可覆盖请求头，先用 `regexCheck` 排除不合法用户名；URL 插值、探测 URL、请求 payload 分开处理。支持显式 GET／HEAD／POST／PUT；未指定方法时，标量 `status_code` 使用 HEAD，其余使用 GET。`response_url` 禁止自动跳转，其余允许跳转；所有请求传入超时和可选代理。[请求构建][S5]

`SherlockFuturesSession` 在提交前取 `monotonic()`，响应 hook 中重写 `resp.elapsed`。据此推断，该指标可能包含线程池等待时间，不宜直接当成服务器处理时间或完整正文下载耗时。[计时实现][S6]

**本项目建议：**保留“小并发抓取、统一结果结构、串行登记”的分工；标准库 `ThreadPoolExecutor` 和 `urllib` 即可满足首个公开原文采集版本，不必引入整个 Sherlock 依赖树。工作线程只返回采集结果，主线程写日志和快照，审阅后仍使用现有 `import_evidence` 登记证据。并发上限、单次超时、响应体大小和跳转次数应有明确边界；同域请求还应限制频率，避免把全局并发上限误当成站点限速。

## 3. 探测类型与结果状态

`QueryStatus` 定义 `CLAIMED`、`AVAILABLE`、`UNKNOWN`、`ILLEGAL`、`WAF` 五类，含义分别是用户名被探测到、未探测到、探测出错、格式不允许、遭 WAF 阻挡。[状态枚举][R0] `AVAILABLE` 是程序对用户名的分类，不是“站点可访问”，也不是已经证明账号可以注册。

| 探测方式 | 代码中的判定 | 不能忽略的边界 |
|---|---|---|
| `regexCheck` | 正则不匹配直接 `ILLEGAL`，不提交该站请求 | 是输入格式检查，与目标证据是否存在无关。[S5] |
| `message` | 命中任何 `errorMsg` 子串为 `AVAILABLE`；均未命中为 `CLAIMED` | 这个分支没有强制要求 HTTP 2xx；未知错误页、登录壳、变更文案可能被当作存在。[S7] |
| `status_code` | 默认 `CLAIMED`；命中 `errorCode`，或状态不在 `[200,300)`，改为 `AVAILABLE` | 403／429／5xx 也会进入未发现，而不是自动归为网络错误。[S8] |
| `response_url` | 关闭跳转后，原始响应 2xx 为 `CLAIMED`，其余 `AVAILABLE` | 当前实现没有比较返回 URL 或注册表中的 `errorUrl`；正常迁移跳转也可能判未发现。[S5] [S9] |

分类前会先检查四条固定 WAF 内容指纹，命中为 `WAF`；未知 `errorType` 为 `UNKNOWN`。`errorType` 在分类阶段可以是数组，按 message、status_code、response_url 的固定顺序判断，已有 `AVAILABLE` 不再被后续两类覆盖。[预检查与组合规则][S10]

**本项目建议：**借鉴显式状态，重新定义语义。原文采集至少应区分“已获取可读文本、未找到、需登录、被阻挡、限流、超时、网络错误、其他 HTTP 错误、不支持的内容、待人工读取”。只有成功获取可核对原文才进入候选材料；成功仍不等于已核实公司、部门、岗位或观察。不要沿用 `CLAIMED/AVAILABLE` 表示公司口碑。

## 4. 超时、网络错误与失败保存

**代码事实：**探测默认超时 60 秒，CLI 校验超时须大于零；该值传给每个请求。它不是整个调查任务的总时限；取 future 结果时没有额外给 `result()` 设总等待上限。[默认超时][S16] [参数校验][S11] [请求传参][S5] [等待结果][S12]

`get_response()` 捕获 HTTPError、ProxyError、ConnectionError、Timeout、RequestException 和 UnicodeError，返回响应、错误类别和异常文本。分类器初始为 `UNKNOWN`，遇到上述错误保留此状态；最终 `QueryResult.context` 保存错误类别，详细 `exception_text` 未继续写入该对象。没有在这条请求／结果路径中看到重试或退避逻辑。[异常处理][S12] [分类初值][S10] [结果保存][S13]

这里没有调用 `raise_for_status()`；`get_response()` 得到有状态码的 HTTP 响应即清空网络错误上下文。因此不能因存在 `except HTTPError` 就推断 403／429／500 已被单列为访问失败。[S12] [S8]

内存结果含 HTTP 状态和响应文本，`--dump-response` 可打印正文；常规 TXT／CSV／XLSX 导出围绕账号 URL、状态和耗时，不能替代带采集时间、最终 URL、原文与内容摘要的调查快照。[正文与状态保存][S13] [调试输出][S14] [文件导出][S15]

**本项目建议：**每条输入 URL 都要有成功或失败记录。失败保留原因和 HTTP 状态，不能写成“无负面信息”或自动生成中性证据。首版可以不自动重试，但应明确这一限制；若增加重试，应有次数上限并尊重 `Retry-After`，仍无法读取就保留缺口。完整正文成功与否应与网络成功分别判断，HTTP 200 的登录页、验证码页或 JavaScript 空壳应进入待人工读取状态。

## 5. 主要限制与误判风险

以下为依据已核源码做出的风险判断，不是本次实测的误判率。

1. **探测规则依赖页面外观。** 精确子串、状态码和少量 WAF 指纹会随站点变化失效；200 错误页可能假阳性，403／429／5xx 或迁移跳转可能假阴性。[S7] [S8] [S9] [S10]
2. **站点规则会混合“没有”和“读不到”。** Discord 的限流提示也放在 `errorMsg` 中，命中后走 `AVAILABLE`；这说明不能把原规则直接用作调查缺失判定。[D4] [S7]
3. **默认运行结果依赖实时配置。** manifest 与排除表会变化，且排除表失败时继续；仅记 Sherlock 代码版本不足以完整复现。[T0] [T1] [T3]
4. **网络并发不是搜索或事实验证。** 代码对预设站点地址作存在性探测，不提供公司检索、员工身份认证、部门归属判定、时间范围核实、转载血缘合并或原文支持关系审查。[S1] [S5] [R1]
5. **同名不能证明同一主体。** 用户名相同无法推出账号属于某员工，也无法推出其内容描述目标部门；即使读到帖子，仍需现有证据账本的范围、时间、原文与来源关系校验。[R1]

## 6. 对照见的最小可落地改动

此处是实现建议。新增能力必须体现在实际命令和采集产物中，单独修改 README 不算实现。

1. **增加独立采集入口。** 在现有 `init → plan → import → report` 之间增加 `collect`，接受用户／宿主搜索工具已找到的公开原文 URL 清单。不要把它宣传为已内置跨平台搜索；用户名探测不进入调查流程。
2. **增加来源与采集模块。** 小型本地注册表做输入校验，采集模块做有限并发 HTTP 读取和 HTML／文本提取。明确网络状态、内容是否可读及不支持的类型；不强行把无法读取的页面标为全文。首版保持纯标准库即可。
3. **保存原文和完整尝试日志。** 为每个 URL 记录输入／最终地址、采集时间、HTTP 状态、访问分类、失败原因及内容快照位置和 SHA-256。失败也保存一行；成功快照可审阅、重用和核对，避免每次报告重新抓取。
4. **采集与证据登记分开。** `collect` 产生原文候选和待审记录；审阅者补充准确摘录、观察、维度、方向、公司／部门／城市／岗位、观察日期和来源血缘，再调用现有整批校验导入。不要凭站点名称自动填员工经历，不要从公司名搜索词推定具体部门已经匹配。
5. **报告呈现采集缺口。** 将各次成功、受限、限流、超时和其他失败汇总到报告，说明哪些原文尚未读到。报告的证据簇计数仍以已审阅导入的材料为准，不能把请求数或搜索结果数当作独立证据数。
6. **使用本地 HTTP 测试服务验收。** 验证可读 HTML／文本、重定向、404、403、429、500、超时、200 登录／挑战页、编码异常及响应体上限；检查成功和失败均留痕，并确认采集命令不会自行制造加班／氛围结论或直接写入未经审阅的证据。无需运行上游账号探测器。

[C]: https://github.com/sherlock-project/sherlock/commit/c588d7c8b476df9f9c84912a05d1430fb8cdcdae
[T0]: https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/sites.py#L11-L12
[T1]: https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/sites.py#L117-L157
[T2]: https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/sites.py#L159-L203
[T3]: https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/sites.py#L161-L181
[T4]: https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/sites.py#L54-L61
[R0]: https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/result.py#L8-L17
[R1]: https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/result.py#L35-L70
[S1]: https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/sherlock.py#L209-L231
[S2]: https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/sherlock.py#L808-L828
[S3]: https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/sherlock.py#L737-L766
[S4]: https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/sherlock.py#L340-L361
[S5]: https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/sherlock.py#L237-L335
[S6]: https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/sherlock.py#L70-L109
[S7]: https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/sherlock.py#L405-L429
[S8]: https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/sherlock.py#L431-L442
[S9]: https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/sherlock.py#L444-L453
[S10]: https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/sherlock.py#L379-L405
[S11]: https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/sherlock.py#L507-L529
[S12]: https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/sherlock.py#L112-L142
[S13]: https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/sherlock.py#L483-L504
[S14]: https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/sherlock.py#L455-L481
[S15]: https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/sherlock.py#L840-L928
[S16]: https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/sherlock.py#L619-L627
[D1]: https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/resources/data.json#L3-L13
[D2]: https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/resources/data.json#L96-L110
[D3]: https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/resources/data.json#L202-L208
[D4]: https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/resources/data.json#L722-L735
[D5]: https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/resources/data.json#L2243-L2249
