# cqh_skills

用于生物信息学分析结果汇报的个人 skills，默认使用中文，并要求关键结论可追溯到实际分析输出。

| Skill | 用途 | 入口 |
| --- | --- | --- |
| `clarify-report` | 生成通俗易读的 Markdown 报告，包含图表解读、证据链接和术语表。 | [SKILL.md](skills/clarify-report/SKILL.md) |
| `report-ppt` | 生成正式 PPTX，包含图表解读、逐页讲稿、证据来源和成品检查。 | [SKILL.md](skills/report-ppt/SKILL.md) |

## 目录与调用

两个 skill 分别位于 `skills/clarify-report/` 和 `skills/report-ppt/`。使用时保留完整目录，包括 `agents/`、`references/` 及适用的 `scripts/`、`tests/`。

在已加载对应 skill 的 Codex 会话中手动调用，例如：

```text
$clarify-report 根据指定分析任务的结果目录生成中文 Markdown 报告，面向非本领域读者。
$report-ppt 根据指定分析任务的结果目录制作中文 PPTX，面向初级专业人员，汇报时长 15 分钟。
```

调用时可指定任务范围、结果目录、读者或听众及详略要求。两个 skill 的配置均关闭隐式调用。

## PPT 工具依赖与测试

`report-ppt/scripts/pptx_support.py` 使用 Python、`python-pptx` 和 Pillow。渲染页面预览还需要 LibreOffice（或 `soffice`）与 `pdftoppm`。制作中文幻灯片时需检查目标环境的中文字体；辅助模块默认使用 `Noto Sans CJK SC`。

在可导入 `pptx` 和 `PIL` 的环境中，从仓库根目录运行现有测试：

```bash
python -B -m unittest discover -s skills/report-ppt/tests -v
```

测试使用合成图片与幻灯片，验证辅助工具行为；实际报告仍需按各 skill 的工作流核实科学证据与成品可读性。
