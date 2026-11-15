# Sherlock 可借鉴的机制与 Job-Sherlock 的可行性边界

核查日期：2026-11-15。仅使用官方仓库和项目文档，代码固定于当前主分支提交 [c588d7c8（2026-11-01）](https://github.com/sherlock-project/sherlock/commit/c588d7c8b476df9f9c84912a05d1430fb8cdcdae)。本次未运行账号扫描，未测量准确率；下文明确区分事实与推断。

**机制事实。** Sherlock 把用户名代入站点 URL 模板，对主页或专门探针发送 HTTP 请求，再按状态码、错误文本或关闭跳转后的响应分类；单个用户名的并发上限为 20。输出围绕账号链接和探测状态，不包含同名账号属于同一真人的证明，也不解释帖子中的工作经历。[核心源码](https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/sherlock.py#L172-L453)

**数据与扩展事实。** 该提交的 `data.json` 有 481 条站点配置（解析后剔除 `$schema` 计数），保存 URL、判断规则及已占用测试用户名；这不是一份个人资料数据库。符合既有检测方法的站点，主要贡献工作是分析页面、填写配置、验证正反样例。官方要求新增站点检查误报和漏报，并称恢复失效站点是其最大积压之一。[站点配置](https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/resources/data.json)、[添加站点](https://sherlockproject.xyz/adding-sites)、[贡献流程](https://sherlockproject.xyz/contribute)

**维护事实。** 默认从远程 manifest 加载规则，再读取上游误报排除表，因此包内 481 条不等于每次实际有效覆盖。仓库配置了每日误报检查，更新排除表；修改站点配置的 PR 也会触发验证。测试使用随机用户名检查误报、已占用用户名检查漏报，能发现部分退化，但不构成总体准确率测量。[加载逻辑](https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/sites.py#L117-L181)、[每日工作流](https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/.github/workflows/exclusions.yml)、[PR 验证](https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/.github/workflows/validate_modified_targets.yml)、[测试实现](https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/tests/test_validate_targets.py)

**易用性事实。** README 提供 `pipx install sherlock-project`、Docker、dnf 等渠道；安装后 `sherlock user123` 即可执行，支持 CSV／XLSX 导出。普通用户不必改源码，但仍需终端及相应运行环境。README 还警告部分第三方 ParrotOS／Ubuntu 包损坏；不能把“一条查询命令”理解为零安装、零排障成本。[当前 README](https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/docs/README.md)、[安装文档](https://sherlockproject.xyz/installation)

**限制事实与推论。** 当前源码用有限的 WAF 指纹识别拦截；若未命中，错误文本法可能把不含指定错误字样的异常页判为存在，状态码法又可能把 403／429 判为未发现。因此“找到”需人工核实，“未找到”不能证明不存在。历史移除记录包含登录墙、JavaScript／混淆页面、CSRF 变化，也有网站因扫描流量要求移除的例子；这些是带日期的历史记录，不是此次实测的平台现状。[分类代码](https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/sherlock_project/sherlock.py#L379-L453)、[历史移除记录](https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/docs/removed-sites.md)

**成功因素推断。** 基于以上事实，较合理的解释是：问题足够窄，输入短且输出直观；站点贡献可拆成小块；开源、包分发和导出能力方便技术用户采用；持续修复让社区贡献直接改善覆盖。这些只是机制层面的假设，没有证明各因素对增长的因果贡献。GitHub star 只能证明关注，不能替代活跃用户、调查质量或准确率证据。[项目 README](https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/docs/README.md)

**对 Job-Sherlock 的判断。** 数据来源确是难点，但部门氛围／强度调查还必须从“能读到”继续走到“公司、部门、岗位和时间匹配”，识别亲历与转述、合并重复来源、处理矛盾。用户名有相对稳定的 URL 映射，主观经历没有同等确定的判断规则；因此扩大站点列表不能直接扩大有效证据。建议把首次价值定义为得到可复核原文、明确证据缺口和下一步核实问题；这是产品推断，需用真实目标与人工基准验证。

可迁移的机制：

- 单一明确输入、尽快给出可检查结果；站点适配配置化；小规模并发；导出与来源链接。
- 正反样例、站点健康检查、失效排除与社区修复；保存版本、失败状态和证据出处。

不可直接迁移的机制：

- 把用户名替换成公司／部门名，就沿用 URL 模板和 HTTP 状态判断口碑。
- 把站点数量、搜索命中、同名账号或 star 数当作有效证据、身份归因或产品效果。
- 把未命中、被拦截、原文缺失解释为没有问题，或从少数匿名经历推出整个团队结论。
