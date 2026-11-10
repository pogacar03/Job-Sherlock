# 证据格式与判定规则

CLI 接受 UTF-8 JSON **数组**，每一项是一段可定位原文对应的一项观察。示例见 [虚构演示材料](../reverse_check/data/demo-evidence.json)，完整命令见 [README](../README.md)。

```json
[
  {
    "id": "e-001",
    "source_ref": "user-provided:匿名访谈笔记第2段（此例虚构）",
    "title": "关于近期下班时间的自述（此例虚构）",
    "source_type": "user_interview",
    "access": "user_provided",
    "source_text": "最近四周我们组大约七点下班，上线日会更晚。",
    "quote": "最近四周我们组大约七点下班",
    "observation": "受访者自述所在组近四周大约七点下班。",
    "dimension": "workload",
    "direction": "neutral",
    "scope": {
      "company": "示例科技",
      "business_unit": null,
      "department": "搜索平台部",
      "city": "上海",
      "role": "后端研发"
    },
    "observed_at": "2026-10-15",
    "published_at": null,
    "retrieved_at": "2026-11-10",
    "origin_id": "interview-a"
  }
]
```

此示例的日期和范围已作为虚构场景给定。真实材料只写实际知道的信息，不据此例补齐缺失值。

| 字段 | 含义与约束 |
| --- | --- |
| `id` | 可省略，由内容生成。手动ID最多80字符，仅字母、数字、下划线与连字符。同ID不同内容拒绝导入。 |
| `source_ref` | 原始HTTP(S)链接，不接受URL用户名密码。没有公开URL的用户材料用 `user-provided:可定位名称`，不会生成可点击链接。 |
| `title` | 原文标题或用户材料名称。 |
| `source_type` | `employee_account` 员工自述；`user_interview` 用户访谈；`official` 官方资料；`secondary` 二手资料。自述不代表身份已认证。 |
| `access` | `full_text` 已读取原文；`user_provided` 用户提供文本；`snippet` 仅摘要。 |
| `source_text` / `quote` | 保存读取的原文段落与逐字摘录；摘录必须是段落中的子串。程序不联网校验也不判断语义是否足以支撑观察。 |
| `observation` | 对摘录的克制转述，明确是谁描述、描述什么，不把一次经历推成部门常态。 |
| `dimension` | `workload` 工作强度、`atmosphere` 团队氛围、`management` 管理沟通、`stability` 岗位稳定性、`compensation` 薪酬兑现、`growth` 成长空间。 |
| `direction` | `risk` 风险观察、`positive` 正向观察、`neutral` 中性观察；由采集者提取，不是程序从原文推断。 |
| `scope` | 对象包含 company、business_unit、department、city、role。company必须填写明确主体；其他未知填null。不可用调查目标填补原文空缺。 |
| `observed_at` | 体验/事件发生日；未知为null。只知道月份/年份或“以前”时保留原文，首版日期填null；不能编造具体日。 |
| `published_at` | 发布日期，未知为null。不能代替观察日期。 |
| `retrieved_at` | 获取日期，必填。以上日期均为YYYY-MM-DD，观察/发布日期不得晚于获取日。 |
| `origin_id` | 同一原始作者、访谈或转载血缘的本案例标记；未知填null。不使用个人身份信息作为标记。 |

## 如何进入判断

公司主体须与案例公司或显式 `company_aliases` 匹配。用户填写的业务线、部门、城市、岗位逐项匹配；未填写不限制该项。**部门本身未明确时，首版不生成部门现状判断。** 字符串只做大小写、全半角和空白归一化，不猜测组织别称或子公司关系。

直接分析材料还必须满足：员工自述或用户访谈、可见原文、观察日期明确且位于基准日前默认365天内、发布时间不晚于基准日。窗口可用 `--lookback-days` 调整（1–3650天，边界包含）。其他材料保留在“背景与待核线索”，并逐条显示原因。

同一原始血缘、去掉UTM/点击跟踪参数后的同一URL或相同摘录，经传递关系合成来源簇。同一作者多次发言会保守合并；不同作者碰巧相同摘录也可能合并。不同簇不保证独立，数量不是概率，不用于估计加班/离职发生率。

每个维度有三种状态：无符合条件材料为 `unknown`；存在材料为 `observed`；风险与正向观察同时出现为 `conflicting`。即使同一个来源自身矛盾也保留分歧。正式/非正式、不同排班、时间点和子组差异要靠后续核实，不采用多数票。

## 文件与修改

案例目录包含 `case.json`、`evidence.json`、检索计划 `queries.md`，Skill另存 `search-log.md`。导入任一条无效时整批不写入；同内容同ID再次导入返回新增0条。并行搜集可以，导入需串行；导入锁异常遗留时确认没有进程在写入再移除 `.import-lock`。

更正旧证据时保留原始来源，使用新ID并在观察里说明更正关系，或由用户明确编辑账本；读取时仍会重新校验格式。CLI当前不提供更新/删除命令。首版报告和账本含保存的原文，默认保存在Git忽略的 `cases/`、`reports/`，分享前审阅材料。
