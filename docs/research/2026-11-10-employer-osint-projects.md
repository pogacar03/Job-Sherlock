# 反向背调开源项目与真实数据接入核对

核对日期：2026-11-10。范围：官方 GitHub README、名单、文件提交 API、两个连接器源码及政府 API 文档；未运行爬虫或登录社区，未调查具体部门。下列“建议”是产品判断。没有用 star 数量衡量证据质量。

## 结论

补齐来源应优先接入**仓库原始名单、官方结构化记录和用户已获得的原文材料**。OSINT 框架值得借鉴来源插件、失败状态、事件关联和保存出处的设计，但不会自动获得员工体验，也不会验证匿名作者身份。公司级记录需要保留为公司级；只有原文明确部门、城市、岗位及体验时间，才能用于部门判断。

## 七个项目

| 项目 | 已核实能力与可借鉴之处 | 对反向背调的边界 |
|---|---|---|
| [996icu/996.ICU](https://github.com/996icu/996.ICU/blob/master/blacklist/README.md) | `blacklist/README.md` 是可直接读取的 Markdown 表，包含城市、公司、曝光/施行时间、制度描述、证据链接；贡献规则要求提供描述和证据。 | 社区贡献，质量和年代不一；项目自己要求甄别真伪、时效，并明确不同部门不可泛化。应导入线索并回读链接/截图，不能把入榜直接变成当前风险事实。 |
| [formulahendry/955.WLB](https://github.com/formulahendry/955.WLB/blob/master/README.md) | `README.md` 提供公司与城市白名单，可直接解析，不必依赖搜索引擎。 | README 明确准确性不保证，并依赖部门、地区及时间；通常缺少逐项体验日期和证据原文。适合找候选公司及设计核实问题。 |
| [shengxinjing/programmer-job-blacklist](https://github.com/shengxinjing/programmer-job-blacklist/blob/master/README.md) | 汇集求职、欠薪、裁员、合伙权益等事件链接，并接受 issue。 | 作者自述是收藏链接；这是线索目录，不是采集器、结构化数据库或事实认证服务。不能把目录标题当原始证据。 |
| [Sherlock](https://github.com/sherlock-project/sherlock/blob/master/docs/README.md) | 输入用户名，检查多个社交平台账号，支持 TXT/CSV/XLSX。当前 README 实际位于 `docs/README.md`。 | 是用户名 OSINT，不是雇主体验数据集。同名账号不证明同一人，更不证明其任职或所在部门；对部门氛围目标优先级低。 |
| [SpiderFoot](https://github.com/smicallef/spiderfoot/blob/master/README.md) | 有来源模块、发布/订阅事件、SQLite、导出及关联规则；[CommonCrawl 模块源码](https://github.com/smicallef/spiderfoot/blob/master/modules/sfp_commoncrawl.py)实际请求索引并产生 URL 事件，确有连接器实现。 | 主要覆盖域名、IP、邮箱、用户名等网络实体。返回相关 URL 不等于读到了员工原文；模块内的免费/不限量标记也不是外部服务的当前保障。 |
| [theHarvester](https://github.com/laramies/theHarvester/blob/master/README.md) | 聚合域名/组织公开信息；当前 README 描述来源结果、部分成功、失败和保存证据。[CommonCrawl 源码](https://github.com/laramies/theHarvester/blob/master/theHarvester/discovery/commoncrawl.py)读取目录、分页索引并解析主机名。 | 是网络侦察框架，不提供工作强度数据库。可借鉴失败与零结果分开、保留局部结果；不建议为雇主背调开启 DNS/端口等主动功能。 |
| [EdgarTools](https://github.com/dgunning/edgartools/blob/main/README.md) | 解析 SEC EDGAR 申报、财务及申报文本；[URL 构造源码](https://github.com/dgunning/edgartools/blob/main/edgar/urls.py)含 submissions、companyfacts 等真实接口。 | 适合有 SEC 申报的主体，辅助研究经营、重组及公司披露；不是员工评价源，未披露不代表没有裁员。不能覆盖所有中国非上市公司。 |

## 两个名单的当前可读性与字节条目

本次 GitHub 工具成功读取 [996 blacklist raw](https://raw.githubusercontent.com/996icu/996.ICU/master/blacklist/README.md) 和 [955 README raw](https://raw.githubusercontent.com/formulahendry/955.WLB/master/README.md)。生产接入宜保存抓取时间、文件 SHA、原文及条目出处；上游变更应作为新的快照，不能覆写历史观察。

- 996 名单文件最新可见提交：[78c11d1，2025-08-22 06:00:11 UTC](https://github.com/996icu/996.ICU/commit/78c11d11c1aadcc5042d3221aeea295e394964ca)。名单有“北京／字节跳动／2017年7月”条目，附看准、搜狐链接；这是旧公司级线索，本次未核验链接原文，不能据此断言当前字节或某部门实行 996。
- 955 文件最新可见提交：[eff96b0，2025-02-03 05:14:25 UTC](https://github.com/formulahendry/955.WLB/commit/eff96b0b20a5fc71d1d51cd9ff0c225eb5da140e)。当前文件对“字节、Byte、TikTok、抖音、头条”检索无匹配；这只表示名单未收录，不能推导公司实际工时。
- 黑名单 README 的最新可见提交：[8ec837e，2026-02-27](https://github.com/shengxinjing/programmer-job-blacklist/commit/8ec837e7941808d688d9eb8e4b86152c0220c23e)。文件最近修改日期不等于每条事件发生日期。

## 通用搜索之外可以具体接什么

1. **仓库文件与 issue/PR**：先实现上述两个原始文件适配器，证据附件与讨论再独立登记。数据可公开读，但 GitHub API 有平台限制，转载和同一事件须去重，不能把多个仓库视为独立证人。
2. **监管公司记录**：[SEC 官方 API](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)提供无需 key 的申报历史、XBRL JSON 和夜间批量 ZIP；后端直接读取，遵守其访问政策。覆盖的是申报主体与披露，不是部门情绪。[Companies House](https://developer.company-information.service.gov.uk/)提供英国公司实时记录，但[认证文档](https://developer.company-information.service.gov.uk/authentication)要求 API/stream key；不是全球工商接口。
3. **裁员通知附件**：[加州 EDD WARN 页面](https://edd.ca.gov/en/Jobs_and_Training/Layoff_Services_WARN)提供当前 [XLSX](https://edd.ca.gov/siteassets/files/jobs_and_training/warn/warn_report1.xlsx)及历史 PDF，并有记录申请入口。这是可定期解析的文件源，不只是新闻搜索。本次确认下载链接存在，网页工具不支持读取 XLSX，未解析表内数据。它只覆盖当地通知记录，不能外推为全球或全公司裁员总数。
4. **用户已访问的员工原文/访谈**：接收脉脉、看准、Glassdoor 等原文导出、截图或访谈记录，保存权限和出处；本次没有核实这些平台存在可自由调用的员工评论 API，不能承诺自动接入。登录、验证码、限流应记为访问受限，不能记成“没有负面信息”。

建议分两步：先扩充公开文件和监管数据，再做有授权的材料导入。输出应逐条展示“来源说了什么、何时、针对哪个主体/部门、哪些未知”，避免用公司黑白名单给具体团队自动打分。
