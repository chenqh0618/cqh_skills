# cqh_skills

个人 skills 的统一维护仓库，覆盖生物医学论文解读、生物信息学项目组织、结果汇报与 CLI 状态栏配置。默认使用中文，科学结论以实际分析输出为依据。

| Skill | 用途 | 入口 |
| --- | --- | --- |
| `project-init-loose` | 初始化松耦合项目工作区，提供任务记录、索引与可恢复归档工具。 | [SKILL.md](skills/project-init-loose/SKILL.md) |
| `clarify-report` | 生成通俗易读的 Markdown 报告，包含图表解读、证据链接和术语表。 | [SKILL.md](skills/clarify-report/SKILL.md) |
| `report-ppt` | 生成正式 PPTX，包含图表解读、逐页讲稿、证据来源和成品检查。 | [SKILL.md](skills/report-ppt/SKILL.md) |
| `biomedical-paper-detail-reader` | 生物医学原始研究逐图精读，梳理研究框架、证据链和结论边界，交付独立 HTML。 | [SKILL.md](skills/biomedical-paper-detail-reader/SKILL.md) |
| `biomedical-paper-mainline-reader` | 生物医学论文主线精读，聚焦关键证据，并提炼对肺损伤修复细胞动态与分子机制研究的可迁移启发，交付独立 HTML。 | [SKILL.md](skills/biomedical-paper-mainline-reader/SKILL.md) |
| `biomedical-paper-story-reader` | 用故事线串联关键科学问题与主图证据，保留对照、负结果和结论边界，交付独立 HTML。 | [SKILL.md](skills/biomedical-paper-story-reader/SKILL.md) |
| `biomedical-paper-story-reader-beginner` | 面向生物医学初学者，在故事线中补足背景、术语、实验读出和对照原理，加入概念框及读图路线，交付离线单文件 HTML。 | [SKILL.md](skills/biomedical-paper-story-reader-beginner/SKILL.md) |
| `codex-statusline` | 配置 Codex CLI 原生状态栏，支持字段选择、实用预设、预览与配置备份。 | [SKILL.md](skills/codex-statusline/SKILL.md) |
| `claude-statusline` | 生成并安装 Claude Code 状态栏，支持列选择、主题及上下文和推理强度颜色提示。 | [SKILL.md](skills/claude-statusline/SKILL.md) |

## 论文解读技能的关系与选择

- `biomedical-paper-detail-reader`：逐主图及关键补图精读，适合系统核查证据链。
- `biomedical-paper-mainline-reader`：围绕核心问题精读，并固定提炼对肺损伤修复课题的迁移启发。
- `biomedical-paper-story-reader`：面向已有一定背景的读者，沿问题、证据与结论讲述研究如何推进。
- `biomedical-paper-story-reader-beginner`：独立的入门故事版，在需要时解释背景、术语、实验测什么、为什么需要对照，以及关键原图怎么看；保持对负结果和结论范围的核查。

mainline 与 story 有共同的主线叙事思路，但名称、指令和资源独立，不能把 mainline 当作原 story 的替代品。本次将现有 story 的完整源码与资源原样补入仓库，再单独维护 beginner 版本；两个版本均可单独复制使用，不依赖其他论文解读目录。原有 detail 和 mainline 内容保持不变。

初学者版包含 `assets/report_template.html`、`references/teaching-example.md` 和 `references/experiment-guide.md`。模板提供概念讲解框、读图提示、证据锚点及可折叠术语区；参考资料帮助解释测量、对照和证据边界，教学例子不得当作论文事实。每个报告仍须按实际论文重建通常 3–5 个关键节点，生成可独立离线阅读的 HTML。

## 维护与本地入口

源码、工作流、模板和测试统一维护在 `skills/<名称>/`。`adapters/claude/` 保留两个报告 skill 已有的 Claude 手动调用配置，并通过仓库内相对软链共享资源。

本地宿主的 skills 目录链接到此仓库，修改后在此仓库提交与推送。以下命令中的仓库路径需替换为实际克隆位置；已有同名入口时先核对并移至 skills 目录之外备份，再建立链接。

```bash
skill_repo="/absolute/path/to/cqh_skills"
mkdir -p "$HOME/.agents/skills" "$HOME/.claude/skills"
for name in project-init-loose clarify-report report-ppt biomedical-paper-detail-reader biomedical-paper-mainline-reader biomedical-paper-story-reader biomedical-paper-story-reader-beginner; do
    ln -sT "$skill_repo/skills/$name" "$HOME/.agents/skills/$name"
done
ln -sT "$skill_repo/skills/project-init-loose" "$HOME/.claude/skills/project-init-loose"
for name in clarify-report report-ppt; do
    ln -sT "$skill_repo/adapters/claude/$name" "$HOME/.claude/skills/$name"
done
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
ln -sT "$skill_repo/skills/codex-statusline" "${CODEX_HOME:-$HOME/.codex}/skills/codex-statusline"
ln -sT "$skill_repo/skills/claude-statusline" "$HOME/.claude/skills/claude-statusline"
```

使用时保留仓库完整目录及软链；本地入口依赖该克隆目录的位置。

## 调用

在已加载对应 skill 的 Codex 会话中手动调用，例如：

```text
$project-init-loose 为指定项目初始化 mgmt/analysis/explore 工作区。
$clarify-report 根据指定分析任务的结果目录生成中文 Markdown 报告，面向非本领域读者。
$report-ppt 根据指定分析任务的结果目录制作中文 PPTX，面向初级专业人员，汇报时长 15 分钟。
$biomedical-paper-mainline-reader 围绕关键证据解读论文，并提炼对肺损伤修复课题的启发。
$biomedical-paper-story-reader 沿科学问题与关键图的证据故事解读这篇论文，生成独立 HTML。
$biomedical-paper-story-reader-beginner 面向生物医学初学者解读这篇论文，先解释必要概念和实验原理，再带读关键图并生成离线 HTML。
$codex-statusline 为 Codex 配置显示模型、剩余上下文、用量限制、目录名和 Git 分支的状态栏。
```

Claude Code 使用对应的 `/project-init-loose`、`/clarify-report`、`/report-ppt`。调用报告 skill 时可指定任务范围、结果目录、读者或听众及详略要求；两个报告 skill 保留手动调用设置，`project-init-loose` 保留原有调用行为。

Claude Code 状态栏使用 `/claude-statusline` 交互选择列和主题，或使用 `/claude-statusline dracula` 指定主题。两个状态栏 skill 的独立预览与安装命令见各自的 `SKILL.md`。

## 依赖与测试

`project-init-loose` 需要 Python 3.11+ 和 Git，Python 代码仅依赖标准库。现有项目的更新方式见 [MIGRATION.md](skills/project-init-loose/MIGRATION.md)。

`codex-statusline` 需要 Python 3.11+ 和 Codex CLI，Python 脚本仅依赖标准库。它修改 `[tui].status_line`；可用字段以当前 Codex 版本为准。

`claude-statusline` 使用 Bun 运行生成器（未安装时可用 `npx -y bun`），生成的 Bash 脚本需要 `jq`。安装时写入 `~/.claude/scripts/statusline.sh` 并更新 `~/.claude/settings.json`。

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

