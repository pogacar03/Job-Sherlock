# 工作体验试点评测

本工具只统计人工填写并复核的标注，不进行论坛调查，也不会制造评测数据。先复制 [空模板](examples/pilot-template.json) 至忽略的 `cases/` 目录，按 [评测协议](superpowers/specs/2026-11-15-workplace-evidence-v03-design.md) 的 G 节登记案例及阅读检查。

`eligible_origins` 为已复核的原始来源簇标识数组；空数组表示完成复核且没有合格体验，`null` 表示未完成。每个工作时间字段以秒为单位，未记录为 `null`。错误计数为非负整数；尚未审阅填 `null`。不要把真实帖子或个人资料加入仓库。

```bash
python3 -m reverse_check evaluate --file cases/pilot/labels.json --out reports/pilot
```

结果包括分子、分母、未知数、分层覆盖、配对主动时间和错误数。分母为零时显示“尚未评测”。重新生成需要明确使用 `--force`。

下面是**虚构示例**中的单个案例，用于说明输入；不能当作真实测试结果：

```json
{"id":"demo-1","stratum":"rich","manual":{"eligible_origins":["post-1"],"active_seconds":100,"setup_seconds":0},"tool":{"eligible_origins":[],"active_seconds":60,"setup_seconds":20},"top10":[{"ref":"fictional-post","team_relevant":true,"experience":false}],"review_errors":{"wrong_team":0,"question_as_fact":0,"untraceable_quote":0}}
```
