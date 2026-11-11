# 工作氛围与强度：论坛扫描

只发现和读取工作体验材料，不查询薪资。首次使用：

```bash
python3 -m reverse_check channels
python3 -m reverse_check init cases/target --company 字节跳动 --department "国际化广告 CRM 与交易" --company-alias ByteDance --company-alias TikTok
python3 -m reverse_check scan cases/target --limit 5 --timeout 20
python3 -m reverse_check report cases/target
```

有扫描记录的报告只展示工作强度和团队氛围两个维度。旧案例没有扫描记录时仍使用原有六维报告。扫描不会自动导入证据；正文、体验日期、摘录和部门归属需要审阅。

## 渠道范围

| 渠道 | 实际接入 | 限制 |
|---|---|---|
| V2EX | 原生公开 JSON：最近主题、指定主题及首批回复 | 最近主题不是全站历史搜索；不需要配置 API 2.0 token；旧公开接口可能不可用 |
| 牛客 | OpenCLI search → detail | 需要 OpenCLI、浏览器桥接和适用会话 |
| 知乎 | OpenCLI search → answer-detail | 当前只读取搜索返回的回答；文章、问题不作为已读正文 |
| 小红书 | OpenCLI search → note | 需要浏览器连接、登录；不绕过验证码 |
| 脉脉 | 人工提供职言工作体验原文 | 上游人才搜索不能替代职言；未实现自动读取 |
| OfferShow | 人工提供氛围、强度讨论原文 | 未核实公开讨论 API，不查询薪资 |
| 看准 | 人工提供员工工作体验原文 | 未实现自动读取 |

仅查指定渠道或指定 V2EX 帖子：

```bash
python3 -m reverse_check scan cases/target --source nowcoder --source zhihu --query "字节跳动 国际化 CRM 加班"
python3 -m reverse_check scan cases/target --source v2ex --topic-id 123456
```

示例主题 ID 需要替换为真实目标。每个 OpenCLI 渠道默认两组搜索词；每组最多读取 limit 条候选详情，最多保存 limit 篇相关原文。timeout 是单次调用预算，不是整轮扫描的总时限。V2EX 最多检查100条列表记录；回复只读第一页、最多100条，不能声称已读完所有评论。

## OpenCLI 准备

根据 [OpenCLI 官方说明](https://github.com/jackwener/OpenCLI)安装命令与浏览器扩展。当前开发环境已安装 CLI 2.0.3；2026-11-11 doctor 确认扩展连接，牛客搜索与正文读取已经实测成功。知乎返回 AUTH_REQUIRED，小红书站内跳转超时；连接扩展不表示每个平台都已登录。

```bash
npm install -g @jackwener/opencli
opencli doctor
```

channels 的 installed_unchecked 只说明找到可执行文件，不说明浏览器已连接或平台已登录。软件不复制登录会话，不输出 Cookie，不运行评论、发帖或点赞命令。

## 记录与证据

`cases/target/scans/<ID>/run.json` 保存渠道状态、范围、匹配记录和对应 collection 位置；raw 保存 API 响应或 OpenCLI 的结构化输出。原生响应另外保留请求 URL、最终 URL、状态码及内容类型。读取失败后已经拿到的材料仍可保留，并标为 partial。

正文要求同时命中公司/别名与工作体验词；这是线索筛选，不是身份认证、部门匹配或语义判定。帖子和回复构成同一来源上下文，不自动按回复数量增加独立证人。纯薪资帖不作为目标，混合帖只用于后续提取工作体验段落。

读取到的原文通过现有采集流程生成 collections/<ID>/evidence-drafts.json，仍需逐条补充元数据并审阅后 import。接口返回异常、超时、未配置、登录限制和成功查询但未命中分别保留。HTML、Markdown、JSON 报告均展示扫描状态；零材料时两个维度仍为待核实。

人工材料使用原有 import 证据格式，见 [证据格式](evidence-format.md)。OfferShow 若没有可分享 URL，可使用 user-provided: 前缀定位用户提供的材料；保留原文出处、体验时间，并只摘录氛围或强度信息。

## 本轮核查

V2EX 两个域名的真实请求均超时；此环境不能据此确认实际服务可用性。测试使用固定论坛响应验证了主题/回复关联、纯薪资过滤、详情读取、域名限制、失败与未命中区分，以及证据隔离。固定响应测试不代表所有真实平台已接通。2026-11-11 新增真实核查：牛客找到并读取正文，知乎明确返回登录要求，小红书两次跳转超时，部分牛客候选被上游内容归属校验拒绝。工具现在解析 stdout 中的结构化错误代码，登录要求不再被归为通用错误；失败和零结果分别记录。
