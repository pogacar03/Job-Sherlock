# 脉脉职言公开读取核查（2026-11-11）

范围：Job-Sherlock 的部门氛围、工作强度线索。仅查询公开网页与上游源码；未使用浏览器、用户账号、Cookie、私有接口或认证逆向。本文不调查薪资，也不根据示例文章判断任何公司的实际情况。

## 结论

**存在可由宿主网页读取工具读取的官方公开帖子详情页；尚未验证可靠的原生职言搜索和完整评论采集。** 可采用“站外搜索发现链接 → 公开详情读取 → 人工核实出处”的受限路径。不能将现有 OpenCLI 的 `maimai search-talents` 当成职言搜索。公开详情可读也不意味着已实现直接 HTTP 批量采集。

## 已验证与边界

| 对象 | 本次观察 | 可用范围 |
| --- | --- | --- |
| `/community/gossip-detail/{id}?egid={opaque}` | 宿主 `web.open` 成功返回帖子作者、页面日期和正文，页面同时显示“未登录”。[实例一](https://maimai.cn/community/gossip-detail/37784691?egid=5fc4ab7fc22946fc8d3dc870b4e3786f)、[实例二](https://maimai.cn/community/gossip-detail/37913420?egid=ea2f7f9a526c4f21ab701cb7d09f8f7c)。 | 可作公开社区原文入口；保留搜索发现的完整 URL，不猜测或生成 `egid`。示例只有月日，不能自行补年份。 |
| 同一详情页的评论 | 实例一正文可读，但本次 `web.open` 评论区显示“加载中”；搜索结果曾展示评论文本。 | 不承诺完整评论、回复链或分页。搜索摘要中的评论只作线索，需另行读到原文才登记证据。[原页](https://maimai.cn/community/gossip-detail/37784691?egid=5fc4ab7fc22946fc8d3dc870b4e3786f) |
| `/article/detail?efid={opaque}&fid={id}` | 无账号的宿主读取返回标题、作者、日期和正文；页面有“登录 / 注册”入口仍展示内容。[已打开实例](https://maimai.cn/article/detail?efid=bNWDuTyEj1s0R7SFu8C_aw&fid=1885410573) | 公开文章/帖文呈现页是另一条可用读取路径；不能因此宣称覆盖全部匿名职言。平台声明内容也可能整编自互联网，需追溯原创。 |
| 职言导航 | 从公开详情页的“职言”链接得到 `/community/home/gossip`，宿主读取报告 restricted URL。 | 确认导航存在，未验证列表内容、搜索参数、筛选、分页或登录要求。[链接出处](https://maimai.cn/community/gossip-detail/37784691?egid=5fc4ab7fc22946fc8d3dc870b4e3786f) |
| 原生搜索 | 公开详情页有搜索输入框，但没有可读取的查询提交链接；检索 `site:maimai.cn/community/search` 没有验证出搜索契约。 | 不编造 `search` 命令、查询参数或接口。 |

宿主工具本次同时报告部分 `maimai.cn/community` / `web/gossip_detail` 路径存在 robots 或 restricted 限制，而上述具体公开详情 URL 能返回正文。返回结果标注抓取日期，可能使用索引/缓存；这仅证明**本次宿主可读**，未实测无 Cookie 的本地 HTTP 实时抓取、JavaScript 渲染或自动化端到端采集。遇到限制应保留访问状态，不据此认定没有相关帖子。

## OpenCLI 与已有实现

上游 [maimai 适配器文档](https://github.com/jackwener/OpenCLI/blob/main/docs/adapters/browser/maimai.md)只列出人才搜索。上游 [search-talents.js](https://github.com/jackwener/OpenCLI/blob/main/clis/maimai/search-talents.js) 明确声明候选人搜索、Cookie 策略和浏览器要求，导航到招聘端人才发现页，输出职位、公司、学校等人才字段。读取源码不等于调用其接口；本次没有执行该适配器。登录状态命令也不提供职言内容读取能力。

检索到的第三方 [HideinbushZY/maimai-skill](https://github.com/HideinbushZY/maimai-skill) 同样面向招聘者找人和触达，要求登录招聘者账号，不能作为公开职言采集实现。有限检索未找到经本次验证的、可直接复用的公开职言搜索适配器；这不是“全网不存在”的证明。

## 对当前实现的建议

1. 将脉脉保留为核心资料来源，能力标注为“公开链接读取可用；原生搜索未验证”，与小红书、牛客分别报告状态。
2. 用宿主站外搜索查询 `site:maimai.cn/community/gossip-detail 公司 部门 加班` 和 `site:maimai.cn/article/detail 公司 部门 氛围` 发现链接；站外搜索覆盖不完整，相关性和时间范围需逐篇审阅。
3. 只在读到正文后建立证据；保存完整 URL、获取方式、实际可见日期、原文摘录和访问限制。公开文章、招聘宣传、泛职场建议与员工亲历分开标注，未知部门/岗位保持未知。
4. 当前不要宣称“OpenCLI 已接通脉脉职言搜索”；增加浏览器或登录态实现前另做明确范围的验证。本次仅提交研究记录，没有改动代码。
