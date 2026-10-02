# cqh_skills

个人 skills 的统一维护仓库，覆盖生物信息学项目组织与结果汇报。默认使用中文，科学结论以实际分析输出为依据。

| Skill | 用途 | 入口 |
| --- | --- | --- |
| `project-init-loose` | 初始化松耦合项目工作区，提供任务记录、索引与可恢复归档工具。 | [SKILL.md](skills/project-init-loose/SKILL.md) |
| `clarify-report` | 生成通俗易读的 Markdown 报告，包含图表解读、证据链接和术语表。 | [SKILL.md](skills/clarify-report/SKILL.md) |
| `report-ppt` | 生成正式 PPTX，包含图表解读、逐页讲稿、证据来源和成品检查。 | [SKILL.md](skills/report-ppt/SKILL.md) |
| `detail_biomed_research_explore` | 生物医学原始研究逐图精读，梳理研究框架、证据链和结论边界，交付独立 HTML。 | [SKILL.md](skills/detail_biomed_research_explore/SKILL.md) |

## 维护与本地入口

源码、工作流、模板和测试统一维护在 `skills/<名称>/`。`adapters/claude/` 保留两个报告 skill 已有的 Claude 手动调用配置，并通过仓库内相对软链共享资源。

本地宿主的 skills 目录链接到此仓库，修改后在此仓库提交与推送。以下命令中的仓库路径需替换为实际克隆位置；已有同名入口时先核对并移至 skills 目录之外备份，再建立链接。

```bash
skill_repo="/absolute/path/to/cqh_skills"
mkdir -p "$HOME/.agents/skills" "$HOME/.claude/skills"
for name in project-init-loose clarify-report report-ppt; do
    ln -sT "$skill_repo/skills/$name" "$HOME/.agents/skills/$name"
done
ln -sT "$skill_repo/skills/project-init-loose" "$HOME/.claude/skills/project-init-loose"
for name in clarify-report report-ppt; do
    ln -sT "$skill_repo/adapters/claude/$name" "$HOME/.claude/skills/$name"
done
```

使用时保留仓库完整目录及软链；本地入口依赖该克隆目录的位置。

## 调用

在已加载对应 skill 的 Codex 会话中手动调用，例如：

```text
$project-init-loose 为指定项目初始化 mgmt/analysis/explore 工作区。
$clarify-report 根据指定分析任务的结果目录生成中文 Markdown 报告，面向非本领域读者。
$report-ppt 根据指定分析任务的结果目录制作中文 PPTX，面向初级专业人员，汇报时长 15 分钟。
```

Claude Code 使用对应的 `/project-init-loose`、`/clarify-report`、`/report-ppt`。调用报告 skill 时可指定任务范围、结果目录、读者或听众及详略要求；两个报告 skill 保留手动调用设置，`project-init-loose` 保留原有调用行为。

## 依赖与测试

`project-init-loose` 需要 Python 3.11+ 和 Git，Python 代码仅依赖标准库。现有项目的更新方式见 [MIGRATION.md](skills/project-init-loose/MIGRATION.md)。

`report-ppt/scripts/pptx_support.py` 使用 Python、`python-pptx` 和 Pillow。渲染页面预览还需要 LibreOffice（或 `soffice`）与 `pdftoppm`。制作中文幻灯片时需检查目标环境的中文字体；辅助模块默认使用 `Noto Sans CJK SC`。

从仓库根目录运行对应测试；PPT 测试使用可导入 `pptx` 和 `PIL` 的环境：

```bash
python3 -B -m unittest discover -s skills/project-init-loose/tests -v
python -B -m unittest discover -s skills/report-ppt/tests -v
```

测试使用临时小项目、合成图片与幻灯片，验证工具行为；实际报告仍需按各 skill 的工作流核实科学证据与成品可读性。

## project-init-loose 历史

2026-09-12 从 [原独立仓库](https://github.com/chenqh0618/project-init-loose) 迁入 `skills/project-init-loose/`，保留截至 `37196849d0587def9d2b7e77ab6887df4aed2418` 的全部 7 次提交及原提交哈希。旧仓库归档用于回溯，后续开发在本仓库进行。

此次迁移调整 skill 的维护位置和本地入口。已有科研项目中的生成文件按各项目需要，通过迁移说明选择性更新。
