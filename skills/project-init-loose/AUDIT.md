# 本地 skill 审核与修改记录

日期：2026-09-11。审查基线：本仓原 HEAD `452bae2`。本轮按用户确认的 Q1–Q11 实施，只更新 skill、模板、工具与发现入口，不迁移实际科研项目。

## 实际问题与处理

| 观察 | 修改 |
|---|---|
| SUMMARY 混合结论、方法、运行故障和改图历史 | ABSTRACT 用于相关性筛选，SUMMARY 维护当前结论，AS_RUN 提供最终复现信息；样式微调只维护最终状态 |
| analysis/explore 各维护一份几乎相同的规则与模板 | 共用 .project/WORKFLOW.md 和一套任务模板，PIPELINE 按需创建 |
| 禁止读 mgmt 与要求读数据清单矛盾 | 允许读取背景、数据和实验设计；计划不自动成为执行指令 |
| 新建目录逐一授权、旧目录内自由追加 | 授权跟随科学目标；目标内拆分 A/E 和委派不再要求转录用户原话 |
| 探索进入主线要求另开 A 重做 | 可按用户请求直接引用 E，保留探索证据性质，按证据缺口决定验证 |
| 缺少任务生命周期；编号来自活跃目录最大号 | 项目根 _archived/analysis、_archived/explore；编号计入归档；明确预览、迁移和恢复流程 |
| FINDINGS 永远追加 | 维护当前有效结论，替代或撤回内容进入 mgmt/history 并保留依据 |
| reviewer 强制拼接全文、绑定 Codex 和历史 sandbox 故障 | 根据实际可用工具按需取证，零 findings 可有效；访问限制作为明确的核验限制 |
| 只有 Claude 原生角色文件 | 同一角色正文生成 Claude Markdown 与 Codex TOML，模型继承 |
| 初始化使用 sed 插入绝对路径，提交指令包含 git add -A | 以 Python 处理路径和预先检查冲突，先构建完整候选再发布；提交只选择生成及回填文件 |

此前只读抽样覆盖 proj_cellAging 38 个、proj_COPD_mito 12 个、proj_temp/proj_mito_v3 1 个任务：51 份 SUMMARY 合计 791,112 bytes，任务根没有 ABSTRACT。该统计是当时的文件快照，不代表这些项目现在均保持原状。

直接证据：
- [A04 SUMMARY](/public/data/cqh_data/proj_processing/proj_cellAging/analysis/A04_epiHvgPcSweep_0813/SUMMARY.md:229)：275 行、53,388 bytes，含两轮字号调整细节；as-run 约占全文 38%。
- [E08 SUMMARY](/public/data/cqh_data/proj_processing/proj_cellAging/explore/E08_AT2DATPProportion_0825/SUMMARY.md:61)：多轮字号/点大小修改和统计方法变化混在同一记录区，说明不能把所有“改图”都当成纯样式修改。
- [A04 入口脚本](/public/data/cqh_data/proj_processing/proj_cellAging/analysis/A04_epiHvgPcSweep_0813/scripts/run_grid.sh:23) 与 [E08 脚本](/public/data/cqh_data/proj_processing/proj_cellAging/explore/E08_AT2DATPProportion_0825/scripts/01_analyze.R:10)：存在固定原目录路径，支持采用恢复原位后重跑。

## 模型与 agent 能力依据

评估使用可核实的公开能力与宿主加载机制，没有推测未公开的模型内部架构，也没有以厂商基准替代本项目实测。

- GPT-6 Astra 官方说明指出，它对 skill/AGENTS 中的指令更敏感，冲突可能导致提前停下，小型任务也可能过度验证。因此删除冗余门槛、明确已授权范围、让验证成本与变更相称。[GPT-6 指南](https://developers.openai.com/api/docs/guides/latest-model)
- GPT-5.6 官方模型资料确认工具与长上下文能力。skill 使用通用文件、检索与命令约定，不根据模型名称硬编码工作流或上下文额度。[GPT-5.6 Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol)
- Opus 5 官方资料描述长任务与 agent 工作能力；这不足以证明它在本地生信项目上的正确性或领先程度。[Opus 5 发布说明](https://www.anthropic.com/news/claude-opus-5)
- Codex skills 先加载名称和说明，再按需读取正文；Claude Code 同样支持按需技能和参考材料。短入口、相关性摘要与条件读取据此设计。[Codex skills](https://learn.chatgpt.com/docs/build-skills)、[Claude Code skills](https://code.claude.com/docs/en/skills)
- Claude Code 的上下文压缩不能代替持久且准确的项目记录。保留小而稳定的规则、用文件保存最终事实，比依赖完整聊天过程更适合跨会话接续。[Claude Code memory](https://code.claude.com/docs/en/memory)
- Codex 项目角色支持 .codex/agents/*.toml，必需 name、description、developer_instructions；生成时省略模型字段以继承。项目角色配置与本会话实际暴露的协作工具不同，角色 prompt 也不等同于沙箱隔离。[Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)

本机核查版本：codex-cli 0.154.0，Claude Code 2.1.261。两端项目角色文件的生成与语法已验证；未调用两个原生 CLI 的模型会话来验证角色运行。

## Prompt 负担

SKILL.md 从 125 行 / 9,286 bytes 减到 33 行 / 3,097 bytes。reviewer 入口从 77 行缩至 8 行，具体审核约定另为按需读取的 11 行文档。根入口保持约 15 行。

新增生命周期和迁移说明增加了总文件量，不能将仓库总行数当作上下文消耗。当前设计的收益是缩短初始化入口、去除重复角色规则、将条件流程按需读取，并限制科学总结的持续膨胀。长期 token 开销和文档增长仍需实际使用验证，没有宣称固定节省比例。

## 验证与限制

- 9 项临时项目行为测试通过：两端角色格式、既有文件保留、初始化冲突与失败回滚、归档预览与恢复、文件字节保持、已登记依赖阻断、编号冲突与并发分配、元数据错误明确失败。
- 独立只读审查复现了 ENOSPC 时归档回滚不执行、初始化发布中途失败留下半成品两处问题；均已修复，并加入故障注入测试。
- 独立 agent 在生成的临时项目中执行一次标题字号 12→18 的修改：只改变绘图代码和 SVG 的相应字号；运行 start/finish 后任务保持 completed，SUMMARY、AS_RUN 和其他说明文档最终内容未增长。这个案例验证了实际小改图行为，不代表三模型全面评测。
- skill frontmatter 校验与 git diff --check 通过。
- 不运行真实组学流程，不修改已有项目，不自动清理任何科学产物。工具只能检查已登记依赖，后台进程、外部引用和未登记依赖仍须在实际归档前核查。磁盘清理遵循独立清单和已获授权。
- 迁移使用同文件系统 rename；跨文件系统、项目根变化或路径冲突均明确失败。保留历史脚本，归档成功不等于重跑已被验证。

## 交付位置

- [初始化入口](SKILL.md)
- [项目工作约定](templates/project/WORKFLOW.md)
- [归档约定](templates/project/ARCHIVE.md)
- [辅助工具](scripts/task_tools.py)
- [已有项目迁移说明](MIGRATION.md)
- [行为测试](tests/test_workflow.py)

本地 Claude 安装源保持在 ~/.claude/skills/project-init-loose；Codex 发现入口 ~/.agents/skills/project-init-loose 链接到同一目录，避免维护两份版本。本轮未发布远端仓库。

## 2026-09-12 维护位置迁移

以上安装位置和发布状态记录的是 2026-09-11 审核时的情况。当前维护源为 `cqh_skills/skills/project-init-loose/`，两个宿主的本地入口均链接到该目录；原独立仓库截至 `37196849d0587def9d2b7e77ab6887df4aed2418` 的 7 次提交完整保留。此次调整维护说明与安装入口，脚本、模板及已有科研项目保持原状。当前入口见[仓库说明](../../README.md)。
