# 工作氛围与强度：论坛扫描

只发现和读取工作体验材料，不查询薪资。首次使用：

```bash
python3 -m reverse_check channels
python3 -m reverse_check init cases/target --company 字节跳动 --department "国际化广告 CRM 与交易" --company-alias ByteDance --company-alias TikTok
python3 -m reverse_check scan cases/target --limit 5 --timeout 20
python3 -m reverse_check report cases/target
```

有扫描记录的报告只展示工作强度和团队氛围两个维度。旧案例没有扫描记录时仍使用原有六维报告。扫描不会自动导入证据；正文、体验日期、摘录和部门归属需要审阅。

## 三个核心来源

默认扫描仅小红书、牛客、脉脉。`channels --all` 可查看保留的其他渠道；V2EX、知乎、OfferShow 不参与默认扫描。

## 渠道范围

| 渠道 | 实际接入 | 限制 |
|---|---|---|
| V2EX | 原生公开 JSON：最近主题、指定主题及首批回复 | 最近主题不是全站历史搜索；不需要配置 API 2.0 token；旧公开接口可能不可用 |
| 牛客 | search → detail → 页面可见评论 | 当前最多40条可见评论，含页面已加载的子回复；不保证所有楼中楼 |
| 知乎 | OpenCLI search → answer-detail | 当前只读取搜索返回的回答；文章、问题不作为已读正文 |
| 小红书 | search/正常搜索页回退 → note → comments --with-replies | 每篇最多20条顶层评论及上游可读取子回复，需要连接和登录 |
| 脉脉 | 浏览器职言交流搜索（type=gossip）→ 打开原帖 → 公开正文 | 需要登录；按真实卡片点击打开原帖；无法识别的正文记为受限，评论暂未接通；人才搜索不参与 |
| OfferShow | 人工提供氛围、强度讨论原文 | 未核实公开讨论 API，不查询薪资 |
| 看准 | 人工提供员工工作体验原文 | 未实现自动读取 |

仅查指定渠道或指定 V2EX 帖子：

```bash
python3 -m reverse_check scan cases/target --source nowcoder --source xiaohongshu --source maimai --query "字节跳动 国际化 CRM 加班"
python3 -m reverse_check scan cases/target --source v2ex --topic-id 123456
```

示例主题 ID 需要替换为真实目标。每个核心渠道默认三组搜索词（部门线索、加班、氛围），部门含英文缩写时优先使用该缩写避免过长查询；每组最多读取 limit 条候选详情，最多保存 limit 篇相关原文。timeout 是单次调用预算，不是整轮扫描的总时限。V2EX 最多检查100条列表记录；回复只读第一页、最多100条，不能声称已读完所有评论。

## OpenCLI 准备

根据 [OpenCLI 官方说明](https://github.com/jackwener/OpenCLI)安装命令与浏览器扩展。当前开发环境已安装 CLI 2.0.3；2026-11-11 doctor 确认扩展连接，牛客搜索与正文读取已经实测成功。知乎返回 AUTH_REQUIRED，小红书站内跳转超时；连接扩展不表示每个平台都已登录。

```bash
npm install -g @jackwener/opencli
opencli doctor
```

channels 的 installed_unchecked 只说明找到可执行文件，不说明浏览器已连接或平台已登录。软件不复制登录会话，不输出 Cookie，不运行评论、发帖或点赞命令。

## 线索与评论

求助帖正文没写具体体验时也会保留在 run.json 的 leads 中，供追查评论和原作者；leads_only 表示找到了待追查线索，没有已读到的体验描述。线索不进入证据账本。帖子和评论的 author/parent_id/time 只按实际读取字段保存，未知为 null，不从目标信息补齐。

牛客只从真正的 .comment-box 提取评论，不把页面快捷评论按钮当作已发评论；静态“全部评论”标题不表示评论已经加载。小红书回退读取正常搜索页，优先选择带完整签名参数的笔记链接，避免误用卡片前面的无签名链接；只使用页面实际提供的链接。

## 记录与证据

`cases/target/scans/<ID>/run.json` 保存渠道状态、范围、匹配记录和对应 collection 位置；raw 保存 API 响应或 OpenCLI 的结构化输出。原生响应另外保留请求 URL、最终 URL、状态码及内容类型。读取失败后已经拿到的材料仍可保留，并标为 partial。

正文与已读取评论合并后要求同时命中公司/别名与工作体验词；这是线索筛选，不是身份认证、部门匹配或语义判定。帖子和回复构成同一来源上下文，不自动按回复数量增加独立证人。纯薪资帖不作为目标，混合帖只用于后续提取工作体验段落。

读取到的原文通过现有采集流程生成 collections/<ID>/evidence-drafts.json，仍需逐条补充元数据并审阅后 import。接口返回异常、超时、未配置、登录限制和成功查询但未命中分别保留。HTML、Markdown、JSON 报告均展示扫描状态；零材料时两个维度仍为待核实。

人工材料使用原有 import 证据格式，见 [证据格式](evidence-format.md)。OfferShow 若没有可分享 URL，可使用 user-provided: 前缀定位用户提供的材料；保留原文出处、体验时间，并只摘录氛围或强度信息。

## 本轮核查

V2EX 两个域名的真实请求均超时；此环境不能据此确认实际服务可用性。测试使用固定论坛响应验证了主题/回复关联、纯薪资过滤、详情读取、域名限制、失败与未命中区分，以及证据隔离。固定响应测试不代表所有真实平台已接通。2026-11-11 新增真实核查：牛客找到并读取正文，知乎明确返回登录要求，小红书两次跳转超时，部分牛客候选被上游内容归属校验拒绝。工具现在解析 stdout 中的结构化错误代码，登录要求不再被归为通用错误；失败和零结果分别记录。

2026-11-11 三核心来源真实核查：牛客两篇正文读取13条可见评论；小红书正常搜索页回退成功，两篇笔记读取37条顶层/子回复记录；脉脉职言搜索打开两条原帖，一篇正文可读，一篇未识别到文字正文，记为部分成功。上述数据为功能实测的特定样本，没有据此判断目标团队的风评。
