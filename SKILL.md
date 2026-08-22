---
name: project-init-loose
description: >-
  Scaffold a LOOSE three-side project skeleton inside a given project directory: root CLAUDE.md
  (≤15-line signpost) + mgmt/ (管理侧: PROJECT / RESOURCES / PLAN+进度 / FINDINGS 账本 / plans/)
  + analysis/ (分析侧/主线: 自包含单元 A<idx>_<内容>_<MMDD>, 强制产物 SUMMARY.md + PIPELINE.md)
  + explore/ (探索侧/旁支: 自包含单元 E<idx>_<内容>_<MMDD>, 与 analysis 同规格但不进主线, 结论默认
  不回流管理侧) + four project-scoped subagents (mgr / analyst / explorer / reviewer) under
  .claude/agents/. The sides are deliberately DECOUPLED — no plan→execute pipeline, no mandatory
  review gate: plans reach the analysis side only when the user names one, results reach the
  management side only through each unit's SUMMARY.md, and explore/ results reach it only when the
  user names one. Use when the user asks for a 宽松/松耦合 project init, 两套/三套系统 (一侧项目管理
  + 一侧专注分析 + 一侧自由探索), project-init-loose, 初始化项目(松), 创建 mgmt/analysis/explore
  三侧骨架, 加一个探索侧. Prefer the stricter four-tier `project-init` skill instead when the user
  wants 00–03 四层结构, 强制审核闸门, or 每 task 详细方案. This skill searches the target folder for
  research background and existing data, ASKS the user for whatever is still missing (it does not
  abort), then lays down the skeleton, fills mgmt/PROJECT.md (background) + mgmt/RESOURCES.md (data
  with absolute paths/specs/gotchas) + the root CLAUDE.md project name, migrates any pre-existing
  PLAN-like doc into mgmt/PLAN.md (stripping references to files that do not exist in this layout),
  and makes the first git commit. It does not write detailed plans or review content. No --upgrade
  mode.
---

# Project Init（松耦合三侧版）

针对给定项目文件夹，铺一套**三侧并行、彼此解耦**的骨架：根 `CLAUDE.md`（≤15 行指路）+ `mgmt/`（管理侧，轻）
+ `analysis/`（分析侧，重，**主线**）+ `explore/`（探索侧，重，**不进主线**）+ `.claude/agents/{mgr,analyst,explorer,reviewer}.md`。

**与四层版 `project-init` 的根本差别：没有流水线。** 四层版是 `00 定方向 → 01 定方案 → 02 跑 → 03 审 → 回填 00`；
本版**管理与分析之间只有两条通道**：

| 方向 | 载体 | 规则 |
|---|---|---|
| 方案 → 执行 | **用户的嘴** | 分析侧默认不读 `mgmt/`；用户点名「按 `mgmt/plans/xxx.md` 跑」时才读那一个文件 |
| 结果 → 决策 | **`SUMMARY.md`** | 管理侧只读 `analysis/A*/SUMMARY.md`（五节固定标题），不读脚本与日志 |

**第三侧 `explore/` 只接上面第一条通道，不接第二条。** `E<idx>` 单元与 `A<idx>` 规格完全一样（自包含、强制 `SUMMARY.md` + `PIPELINE.md`、审核同构），
差别只在**不进主线**——不挂 `mgmt/PLAN.md` 任务表，结论不自动进 `FINDINGS.md`，用户点名才由 `mgr` 去读那一个 SUMMARY。
放这里的是旁支议题、一次性试探；要让探索结论真正立住，正路是在 `analysis/` 开一个 A 重做。

配套取舍：分析侧与探索侧都**不写方案文件**（`scripts/` 即施工图，偏差写进 SUMMARY 的 `as-run` 节）；
审核**只在用户点名时**发生（无强制闸门），产物落被审单元内的 `review/`；预注册是管理侧 `plans/` 里的**可选**动作。
唯一保留的授权门是「**新建一个 `A<idx>` / `E<idx>` 须有用户对它的明确指令**」——已开的单元内迭代自由。

## 输入

- `project_dir`（必填）：目标项目文件夹**绝对路径**。用户没给就先问清楚，别猜。
- 产物：`<project_dir>/` 下根 `CLAUDE.md` + `AGENTS.md` 软链 + `.gitignore` + `.claude/agents/`（四个）+ `mgmt/` + `analysis/` + `explore/`。

## 总流程

1. 解析 `project_dir`（绝对化；若有软链别名，取 `readlink -f` 的真实路径作**规范根**）。
2. 检索**研究背景**与**已有数据**（启发式见下）。
3. **缺哪样当场问用户**——不中止、不铺半成品、也不按常理编。
4. 跑 `scripts/scaffold.sh`（确定性铺骨架 + `git init`）。
5. 回填 `mgmt/PROJECT.md`、`mgmt/RESOURCES.md`、根 `CLAUDE.md` 的项目名与一句话背景。
6. 搬迁项目里既有的规划类文档进 `mgmt/PLAN.md`（若有）。
7. 首个 `git commit`。
8. 汇报。

## 步骤 2：检索背景与数据

读到能写出「背景」和「数据清单」为止（不求全，但求可信）。

- **研究背景来源**：`README*.md`、根目录 `*.md`、`docs/` `notes/` `背景/` `方案/`、立项或项目描述 `*.txt/*.pdf`。
- **已有数据来源**：`data/` 目录、样本表（`sample_info*`、`*.tsv/*.csv` 清单）、数据文件（10x 矩阵目录、`*.h5`、`*.h5ad`、`*.loom`、`fragments`、`fastq/bam`）。
  记**绝对路径 + 规模 + 内容 + 发现的坑**。扫 `data/` 时**只往下走两三层看结构**，别递归枚举到叶子。

## 步骤 3：缺失就问（不中止）

- 缺**背景** → 问一句「这个项目在研究什么、为什么做？」，用用户的话写进 `PROJECT.md §1`。
- 缺**数据** → 问「数据在哪、有哪些模态」。用户说「还没有数据」也可以铺——`RESOURCES.md` 留 `<TODO>` 并在汇报里点名。
- **科学问题 / 目标**：能从背景明确看出就写，看不出留 `<TODO>`，不要替用户编。

## 步骤 4：脚手架（确定性）

令 `SKILL_DIR` = 本 skill 目录：

    bash "$SKILL_DIR/scripts/scaffold.sh" "<project_dir>"

脚本会：校验目录存在可写；`mgmt/` `analysis/` `explore/` 任一已存在、根 `CLAUDE.md` 非空、或已有同名 agent → **拒绝**（`exit 2`，不覆盖）；
然后铺根契约（`sed` 填规范根）+ `AGENTS.md` 软链 + `.gitignore`（已有则不覆盖）+ 三侧整目录 + 四个 agent；
无 `.git` 则 `git init`（**不 commit**，留给步骤 7）；打印生成树。

> 本 skill **没有 `--upgrade`**。要把老项目搬成这个布局（含给已有两侧项目补 `explore/`），手工照 `README.md` 的三步做即可，别在这里加分支。

## 步骤 5：回填

- **`mgmt/PROJECT.md`**：`§1 研究背景` 依据步骤 2 写实（本次重点）；`§4 实验设计` 能从背景/样本表看出因素、水平、生物学重复就填表——**推断单位那一行必须写**，它决定下游统计合不合法；`§2 科学问题 / §3 目标` 看不出就留 `<TODO>`。
- **`mgmt/RESOURCES.md`**：数据根、样本表、各模态路径/规模/内容、命名键、数据坑填实。**全绝对路径，只写数据不写方法。** 没发现坑写「暂未发现」。
- **根 `CLAUDE.md`**：只回填标题 `<项目名>` 与首行 `<一句话项目背景>`。规范根已由 scaffold 填好，**勿再动**；表格与两条通道说明是通用契约，保持不动。
- **三侧 `CLAUDE.md` 与四个 agent 文件保持不动**——规则的唯一源就是它们，本步不改。
- **`PLAN.md` / `FINDINGS.md` 保持骨架**（除步骤 6 的搬迁）。

## 步骤 6：搬迁既有规划文档

项目里已有 PLAN 类文档（常见于 `docs/PLAN.md`、旧四层项目的 `00_project_control/PLAN.md`）时，搬进 `mgmt/PLAN.md`：

- **保留**：任务链与依赖语义、里程碑、以及任何真实的科学约束（如「某交付物不得按分组展开」这类防 HARKing 条款）。
- **剥掉**：指向本布局不存在的文件或机制的引用——`review/decisions.md`、`STATUS.md`、`01/T<NN>/PLAN.md 拆 A 表`、
  「审核档位」列、根 `CLAUDE.md §N 铁律` 编号引用等。指向仍存在文件的引用改写成新路径（如 `→ mgmt/FINDINGS.md`）。
- **补**：每个节点的三态标记（新项目一律 `待做`）+ 现状一句话列。
- **原文件留在原处**作历史，不删。

搬完自查一遍：`grep -nE '00_project_control|01_task_control|02_analysis_results|03_analysisResults|decisions\.md|STATUS\.md|审核档位' mgmt/PLAN.md` 应无命中。

## 步骤 7：首个 commit

    git -C "<project_dir>" add -A
    git -C "<project_dir>" commit -q -m "init: 松耦合三侧骨架（mgmt/ + analysis/ + explore/）+ 四个 subagent"

`add -A` 之前确认 `.gitignore` 已生效（`git status --short` 里不该出现 `data/` 下的东西）。

## 步骤 8：汇报

生成路径树；四个 agent 各一句职责；`PROJECT.md` 留了哪些 `<TODO>`；`RESOURCES.md` 是否发现数据坑；
`PLAN.md` 是搬迁来的还是空骨架（搬迁的话说明剥掉了什么）；下一步（科学问题与任务链由主会话与用户定；
开第一个 `A` 或 `E` 都需要用户明确指令）。

## 约束

- 不覆盖已存在的 `mgmt/`/`analysis/`/`explore/`、非空根 `CLAUDE.md`、同名 agent。
- 本次只填 `PROJECT`（背景）、`RESOURCES`、根 `CLAUDE.md` 项目名，加上 `PLAN` 的搬迁；不写 `plans/` 方案、不写 `FINDINGS` 条目、不建任何 `A<idx>` 或 `E<idx>`。
- 三侧 `CLAUDE.md` 是规则唯一源；**不要**把规则复制进根 `CLAUDE.md` 或 agent prompt（两处说两套话是这套东西最容易长的毛）。
- 全绝对路径；中文。
