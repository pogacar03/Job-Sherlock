# Sherlock README：参考对象与呈现观察

2026-11-10，用户确认所指“福尔摩斯项目”为 **[sherlock-project/sherlock](https://github.com/sherlock-project/sherlock)**。此前对 `tywinlu1988/Baker-Street` 的调研属于同名候选误识别，其笔记保留，但不再视作用户指定的参考项目。

## 可核实的事实

- GitHub仓库介绍：按用户名跨社交网站寻找账号。它是一个明确用途的查询工具，本次不能把它描述为多Agent推理框架。[仓库](https://github.com/sherlock-project/sherlock)
- 本次GitHub API返回107,754个Star、12,460个Fork；仅是当日快照，不代表增长速度或流量来源，也不能据此推断走红原因。[仓库API](https://api.github.com/repos/sherlock-project/sherlock)
- 当前读取的固定提交为 `c588d7c8b476df9f9c84912a05d1430fb8cdcdae`，默认分支master。README实际位于 `docs/README.md`，而不是仓库根目录。[固定版本README](https://github.com/sherlock-project/sherlock/blob/c588d7c8b476df9f9c84912a05d1430fb8cdcdae/docs/README.md)

## README里实际看到了什么

1. 居中Logo后紧接一句话用途，读者不用先理解架构。
2. 安装、使用、贡献三个入口直接可见。
3. 终端真实截图放在安装前，先展示工具运行的结果。
4. 常规使用示例从一个用户名的单条命令开始，随后才展开完整帮助。
5. 有贡献者、许可证与Star历史等可检查的社区信息，也说明社区包和已知安装问题。

以上是内容观察；“这些因素有助于理解、试用和传播”是设计推断。没有传播渠道、下载、媒体曝光与用户增长数据，本次不将README表述为其高Star数的已证明原因。

## 在照见中的应用

- 首屏使用项目自己的视觉封面与一句话用途。
- 在技术原理之前展示真实生成的报告截图，明确演示虚构。
- 首条命令生成完整离线报告，再按需阅读Skill、真实材料导入和高级选项。
- 将用户关心的六个问题放在前面，把字段与底层规则保留在专门文档。
- 仅展示当前真实版本、运行条件和支持方式；没有伪造Star、用户数、推荐语、CI结果或许可证。

视觉资产为本项目新作，报告截图来自本地实际输出；没有复制Sherlock的Logo、截图、文案或代码。证据引擎与Skill也是独立实现，README呈现参考不等于系统架构移植。
