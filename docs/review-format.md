# 逐段审阅建议

扫描的 v2 `run.json` 包含候选与正文、评论的独立段落。模型或人工制作 `{"schema_version":1,"proposals":[...]}`，字段示例见 [虚构建议](examples/review-proposals.json) 和对应[虚构扫描](examples/review-scan.json)。这个示例全部虚构，需将扫描放入案例的 `scans/scan1/run.json` 才能演练。

每项必须指向 scan_id、candidate_id 和 segment_id；quote 必须逐字出现在该段。basis 的每项包含 field、segment_id、part（text 或发布时允许 time_raw）和 quote。非空来源类型、范围及日期均要有对应原文依据；未知填 null。范围、体验时间及作者身份不能用调查目标补齐。原文没有可定位的公司时不能作为当前账本记录。

来源类型的依据必须来自被引用的同一段，不能把主帖作者的身份声明移用给评论作者。其他范围与日期依据也需要人工核对是否适用于该作者。

kind 为 experience/question/hearsay/official/unknown；只有员工亲历建议可经此流程接收，其他内容作为线索。程序检查快照、引用和格式，不认证匿名身份、原文真假、依据语义或团队归属，需由审阅者判断。

旧版手工 `import` 仍可按[证据格式](evidence-format.md)登记已审阅材料与背景。

使用 `python3 -m reverse_check candidates cases/target --out reports/cards` 生成只读卡片；使用 `python3 -m reverse_check review cases/target --file proposals.json` 在终端逐条接收或跳过。审阅中 `q` 提交此前已选择的项，Ctrl-C 在提交前取消本轮选择。审阅完成后重新运行 `report`。非交互输入不会自动接收。
