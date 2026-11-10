# 公开来源采集

0.2.0新增实际网络采集。它借鉴Sherlock的来源注册表、有限并发和分类结果，不进行用户名查找，也不会因HTTP200就认定公司体验属实。

## 最短流程

```bash
python3 -m reverse_check sources
python3 -m reverse_check plan cases/target --source nowcoder --source zhihu
python3 -m reverse_check collect cases/target --urls /absolute/path/urls.json
```

案例须先用init创建；已有计划需加 `--force` 才会覆盖。`urls.json` 是1–100个原文URL的数组。搜索引擎结果页应由宿主检索和精读后挑选原始文章链接；collector不会自行枚举站内内容或执行JavaScript。非HTTP(S)、含凭据或控制字符的URL会使输入整批被拒绝，且不会保存可能包含凭据的输入日志。

本地注册表固定随包发布，来源id、域名与读取方式可使用 `sources` 查看。默认nowcoder、zhihu和其他公开网页为public；maimai、xiaohongshu、kanzhun为manual，仅登记，不发起请求。这些模式表示本工具实现范围，不表示平台始终允许或禁止公开访问。

## 注册表

默认文件在 `reverse_check/data/sources.json`，支持复制到项目外后修改。用 `sources --file PATH` 校验、查看；用 `plan --sources PATH` 或 `collect --sources PATH` 选用。

```json
{
  "schema_version": 1,
  "sources": [
    {
      "id": "company-news",
      "name": "待配置的公司公开页面",
      "domains": ["example.com"],
      "mode": "public",
      "query": "site:example.com {company} {department}",
      "blocked_titles": ["访问验证"],
      "login_titles": ["登录"],
      "missing_titles": ["页面不存在"]
    }
  ]
}
```

例中的域名仅示意。每个来源需要id、name、domains、mode；query为文本或null。标题特征可省略并采用内置默认。域名只匹配自身或其子域名，不按任意字符串后缀匹配。空domains表示通用来源，最多一个；没有通用来源时未知域名登记unsupported_source。

检索模板只接受 `{company}`、`{department}`、`{business_unit}`、`{city}`、`{role}`；不允许属性访问、转换或格式指令。同一域名不能重复配置到多个来源，避免public/manual策略随数组顺序变化；更具体的子域名单独配置时采用最长匹配。模板生成的是尚未执行的检索文本，不执行外部命令。运行不自动下载远程来源表。

## 状态

| 状态 | 含义 |
| --- | --- |
| retrieved | 保存了足够的可见文本，仍待审阅 |
| manual_required | 来源配置或跳转目标需要宿主/用户读取 |
| login_required / blocked / rate_limited | 登录、访问拦截/验证码、429限流，分别保留 |
| not_found | 页面404/410，或标题匹配配置的删除/缺页特征；不表示目标公司没有该情况 |
| http_error | 其他非2xx，包括服务器错误 |
| timeout / network_error | 网络读取超时或失败，含正文截断 |
| empty / unsupported_content | 文本不足，或格式/编码/压缩不支持 |
| too_large | 正文超过大小上限 |
| unsafe_url / redirect_limit / unsupported_source | 非公网地址、跳转超限、注册表未支持该来源 |

标题特征是可维护的规则，可能误判，不能替代审阅。HTML200登录页面可能使用未覆盖的标题；抓取为retrieved也只表示文本可读。页面内的脚本不执行，HTML内容只做基本可见文本提取。正文按HTTP声明字符集解码，未声明时用UTF-8；不猜测缺失字符集。

默认4线程、10秒连接/读取预算、1MB正文；可设1–16线程、0–120秒内的正数预算、1–10MB范围内的字节上限（也允许更小的测试或窄文本上限）。DNS解析由系统完成，不承诺其硬实时取消。连接使用已检查的公网IP，TLS验证原始主机名，每次跳转重新执行来源与地址检查，不继承浏览器登录或环境代理。

没有自动重试；错误作为本次结果保留。失败后可以单独再采一次，每次拥有新目录，不覆盖旧日志。每次URL任务与自动读取尝试数单独统计；自动尝试可能在DNS检查前就被拒绝，不等同于实际发送HTTP请求数。多次运行中重复的URL按次统计，不计作独立证据。

去重键移除常见跟踪参数和片段，但网络请求使用选中的原始URL；非跟踪查询参数的顺序、重复键和原始编码均保留，不重排签名或业务参数。跳转后使用最终来源的标题规则，日志分别保存requested_source_id和source_id。已经收到HTTP状态后，即使正文超时仍保留状态；超时中断的无长度正文不能作为完整文本生成草稿。

## 产物与审阅门槛

```text
cases/target/collections/<本次ID>/
├── run.json                   # 输入、最终URL、状态、耗时、提及与SHA256
├── sources.json               # 本次实际来源表，字节SHA256写入run
├── evidence-drafts.json        # 已读取内容的待审阅草稿
└── snapshots/*.body            # 原始响应字节，非可执行扩展名
```

HTTP响应内容可能是正文，也可能是验证码、拦截或错误页；快照都只是资料。草稿只为retrieved结果生成。公司/部门/岗位/城市、来源类型、观察日期、摘录和观察不会照调查目标自动填写；`mentions` 仅表示文本中出现了目标词。

审阅者检查URL、原文、对象归属和时间，再补齐 [证据格式](evidence-format.md) 中的字段，将完成后的JSON数组另存文件并调用import。直接导入草稿会失败，采集不会改写evidence.json。只知道网页发布时间时，不能把它填成体验发生日期。

采集日志属于上层案例，应和 `case.json` 一起保留，以确定演示状态与完整调查范围。对manual等未读取页面的任务，retrieved_at是本次登记日期，final_url仅回填输入定位，不表示曾访问该页面；应结合fetch_attempted与status阅读。待执行检索计划不是调查结论，演示标识以案例和最终报告为准。

报告里的“来源采集记录”独立呈现尝试与错误；六维判断仍只使用已导入并满足条件的证据。原始响应、文本、URL和日志默认只落在本地案例目录，不适合未经审阅直接分享。
