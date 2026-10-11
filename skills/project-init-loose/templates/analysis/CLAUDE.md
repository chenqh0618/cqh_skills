# 分析侧

主线分析在 `analysis/` 创建 A 单元。用户指定为主线即可，计划文件不是前置条件。

本侧按项目根 `.project/WORKFLOW.md` 执行；相关规则不在上下文中或已变更时先读取。
选择参考数据、工具或环境时，查 [分析依赖](../.project/DEPENDENCIES.md) 的相关配置与启动命令。
背景、研究数据和实验设计按需读 `mgmt/PROJECT.md`、`mgmt/RESOURCES.md`；用户指定方案时读取相应方案。
任务上下文缺失时，先读其 `ABSTRACT.md`，再按需查看相关结论、运行记录或代码。
归档、恢复与空间清理见 `.project/ARCHIVE.md`。
