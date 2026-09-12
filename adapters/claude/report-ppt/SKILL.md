---
name: report-ppt
description: 为指定生物信息学分析任务生成证据可追溯的正式 PPTX，包含图表解读、逐页讲稿和成品检查。
disable-model-invocation: true
argument-hint: "[结果目录] [任务范围、听众及汇报时长]"
---

# Report PPT

执行前读取 [PPT 工作流](references/workflow.md)，按其中的证据核验、叙事和交付要求完成任务。

本次调用参数：$ARGUMENTS

优先采用用户明确指定的内容，其余从当前任务和实际文件推断。
