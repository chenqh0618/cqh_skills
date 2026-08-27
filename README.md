# project-init-loose

一个 Claude Code skill：给科研/数据分析项目铺一套**松耦合三侧**骨架——`mgmt/`（管理）+ `analysis/`（分析，主线）+ `explore/`（探索，旁支），外加四个项目内 subagent。

设计取向是**少仪式、强边界**：没有 `方案 → 执行 → 审核` 的流水线，没有强制闸门；侧与侧之间只有极窄的几条通道，其余靠各侧自己的 `CLAUDE.md` 自足约束。

## 铺出来的样子

```
<project>/
├── CLAUDE.md              # ≤15 行指路（只说去哪读，不定细则）；AGENTS.md 是它的软链
├── .gitignore             # data/ + 大二进制 + 编辑器垃圾
├── bin/abstracts.sh       # 扫两侧所有单元的 abstract + upstream（三侧共用，实现只此一份）
├── .claude/agents/        # mgr · analyst · explorer · reviewer
├── mgmt/                  # 管理侧（轻，只放文档，要能整体读进上下文）
│   ├── CLAUDE.md          #   本侧规则唯一源
│   ├── PROJECT.md         #   研究背景 / 科学问题 / 目标 / 实验设计（含推断单位）
│   ├── RESOURCES.md       #   已有数据：绝对路径 / 规模 / 内容 / 命名键 / 已知坑
│   ├── PLAN.md            #   任务链 + 三态进度（只挂 A，不挂 E）
│   ├── FINDINGS.md        #   结论账本，只增不改
│   └── plans/             #   按需写的方案，无强制模板
├── analysis/              # 分析侧（重，主线）
│   ├── CLAUDE.md          #   本侧规则唯一源
│   ├── _templates/        #   SUMMARY.md（含 abstract frontmatter）· PIPELINE.md
│   └── A<idx>_<内容>_<MMDD>/   scripts· logs· results· SUMMARY.md· PIPELINE.md
└── explore/               # 探索侧（重，不进主线）
    ├── CLAUDE.md          #   本侧规则唯一源
    ├── _templates/        #   SUMMARY.md · PIPELINE.md
    └── E<idx>_<内容>_<MMDD>/   同 analysis 规格
```

## 三侧之间只有这几条通道

| 方向 | 载体 | 规则 |
|---|---|---|
| 方案 → 执行 | **用户的嘴** | 分析/探索侧默认不读 `mgmt/`；用户点名「按 `mgmt/plans/xxx.md` 跑」时才读那一个文件 |
| 分析结果 → 决策 | **`SUMMARY.md`** | 管理侧只读 `analysis/A*/SUMMARY.md`（五节固定标题），不读脚本与日志 |
| 探索结果 → 决策 | **默认没有** | `explore/` 不挂任务表、结论不自动进账本；用户点名「把 E0x 记进账本」时才收 |

`analysis/` 与 `explore/` **规格完全一样**（自包含单元、强制 `SUMMARY.md` + `PIPELINE.md`、审核落点同构），差别只在进不进主线。放 `explore/` 的是旁支议题与一次性试探；要让探索结论真正立住，正路是在 `analysis/` 开一个 A 重做。

唯一保留的授权门：**新建一个 `A<idx>` / `E<idx>` 必须有用户对它的明确指令**。已开单元内改参数、重跑、补图不需重新授权；只读探查不受限。

## 单元之间怎么互相检索

单元多起来之后，最大的浪费是「agent 一开工先把十个 SUMMARY 读一遍补背景」。这套骨架的处理是**摘要先行**：

每个 `SUMMARY.md` 顶部有一段 YAML frontmatter，与正文五节同为强制产物——

```yaml
---
abstract: 对 6 组 snATAC 做 MACS2 peak calling 与 QC，得 12.4 万共识 peak。
upstream: [A01]
---
```

`abstract` 的配方是**对象 + 方法 → 结论**（≤4 行，必须点出动过的数据对象，坑留在正文的「坑」节）；`upstream` 是上游单元 ID，直读原始数据则写 `[data/]`。

检索规则对三侧统一：

| | analyst / explorer | mgr | reviewer |
|---|---|---|---|
| 派单点名的依赖单元 | 全开 | 全开 | 全开 |
| 扫两侧 abstract（`bin/abstracts.sh`） | 自主 | 自主（默认入口） | 自主 |
| 展开 `A*/SUMMARY.md` | 自主 | 自主 | 限被审折引用过的 |
| 展开 `E*/SUMMARY.md` | 自主 | **须用户点名** | 限被审折引用过的 |
| 下潜别人的 `scripts/` `results/` | 自主 | 需说明理由 | 限被审折引用过的 |

- **默认不翻别的折**：手上的指令 + 点名的依赖就是全部输入。真卡住了才走「扫摘要 → 展开 SUMMARY → 下潜 scripts/results」这三步。
- 三步都是只读，**不需要额外授权**，但**必须留痕**——写进自己 `SUMMARY.md` 的 `as-run` 节，返回时也说一句。
- **读 ≠ 调用**：别人的脚本可以读、可以抄进自己的 `scripts/` 再改，但不得跨折 `bash` 它。
- **引用 `explore/` 必须标注**「来自 E0x，探索侧，未进主线」，且只能当线索或参数来源，不得写进「结论」节当已立住的事实。
- `explore/` 的不回流原则靠「mgr 展开 E 须点名」守住——**abstract 层可见 ≠ 结论回流**。

`bin/abstracts.sh` 无参扫两侧，可传 `analysis` / `explore` 只扫一侧；漏写 frontmatter 的单元会被点名，兼作 lint。

## 四个 subagent

| agent | 干什么 |
|---|---|
| `mgr` | 管理侧执行者：科学问题 / 数据清单 / PLAN 进度 / FINDINGS 账本 / 写方案。不跑重计算，没有开 A 的权力 |
| `analyst` | 分析侧执行者：建 A 折、跑计算、落产物、写 SUMMARY 与 PIPELINE。派单须带用户原话 |
| `explorer` | 探索侧执行者：同上，但只建 E 折、只写 `explore/` |
| `reviewer` | 独立审核者，**只在用户点名时派**：编排 codex 异模型（沙箱只读）判「结论是否被数据支持」，逐条核对其引用的路径与数字 |

每个 agent 的 prompt 只写职责与指路，规则一律指向对应侧的 `CLAUDE.md`——**规则只有一个源**，避免两处说两套话。

## 与四层版 `project-init` 的区别

| | `project-init`（严） | `project-init-loose`（本仓） |
|---|---|---|
| 结构 | `00_project_control` / `01_task_control` / `02_analysis_results` / `03_analysisResults_review` | `mgmt/` + `analysis/` + `explore/` |
| 流程 | `00 定方向 → 01 定方案 → 02 跑 → 03 审 → 回填 00` | 无流水线 |
| 方案 | 每个 task 一份详细方案，必写 | 分析/探索侧不写方案文件，`scripts/` 即施工图 |
| 审核 | 强制闸门（结论进 00 前须审） | 只在用户点名时发生 |
| 根 `CLAUDE.md` | 规则源（~90 行） | 指路牌（≤15 行），规则在各侧 |

要 00–03 四层、强制闸门、每 task 详细方案，用 `project-init`；要两三套彼此不打扰的系统，用本仓。

## 安装

```bash
git clone https://github.com/chenqh0618/project-init-loose.git ~/.claude/skills/project-init-loose
```

之后在 Claude Code 里说「初始化项目（松）/ 创建 mgmt analysis explore 三侧骨架」，或直接 `/project-init-loose`。

## 用法

skill 需要一个参数：`project_dir`（目标项目文件夹**绝对路径**）。它会

1. 检索项目里的**研究背景**与**已有数据**；缺哪样**当场问用户**（不中止、不编）；
2. 跑 `scripts/scaffold.sh <project_dir>` 确定性铺骨架 + `git init`；
3. 回填 `mgmt/PROJECT.md`（背景）、`mgmt/RESOURCES.md`（数据）、根 `CLAUDE.md` 的项目名；
4. 把项目里既有的 PLAN 类文档搬进 `mgmt/PLAN.md`（剥掉指向本布局不存在的文件的引用）；
5. 首个 `git commit`。

**不会**写 `plans/` 方案、不写 `FINDINGS` 条目、不建任何 `A<idx>` / `E<idx>`。

### 守卫

`scaffold.sh` 在 `mgmt/` `analysis/` `explore/` 任一已存在、根 `CLAUDE.md` 非空、或已有同名 agent 时 **`exit 2` 拒绝，不覆盖**。

## 已铺的项目怎么补上 abstract 检索机制

本 skill **没有 `--upgrade`**（不想在这里长分支）。已经铺好三侧的老项目，手工两步：

```bash
SKILL=~/.claude/skills/project-init-loose ; PROJ=<项目绝对路径>

# 1) 铺检索工具 + 覆盖三侧契约、四个 agent、根 CLAUDE.md 与两个 SUMMARY 模板
#    （手工改过这些文件的话，先 diff 再决定要不要覆盖）
mkdir -p "$PROJ/bin" && cp "$SKILL/templates/bin/abstracts.sh" "$PROJ/bin/" && chmod +x "$PROJ/bin/abstracts.sh"
cp "$SKILL/templates/root_CLAUDE.md" "$PROJ/CLAUDE.md"
for s in mgmt analysis explore; do cp "$SKILL/templates/$s/CLAUDE.md" "$PROJ/$s/CLAUDE.md"; done
for s in analysis explore; do cp "$SKILL/templates/$s/_templates/SUMMARY.md" "$PROJ/$s/_templates/SUMMARY.md"; done
for a in mgr analyst explorer reviewer; do cp "$SKILL/templates/agents/$a.md" "$PROJ/.claude/agents/$a.md"; done
grep -rl '<CANONICAL_ROOT>' "$PROJ/CLAUDE.md" "$PROJ"/{mgmt,analysis,explore} "$PROJ/.claude/agents" \
  | xargs sed -i "s#<CANONICAL_ROOT>#$PROJ#g"
# 根 CLAUDE.md 的项目名与一句话背景会被覆盖掉，记得填回去

# 2) 给存量单元补 frontmatter——先看谁漏了
bash "$PROJ/bin/abstracts.sh"     # 输出里带 ⚠ 的就是要补的
```

存量单元的 `abstract` 照它自己 `SUMMARY.md` 的「结论」节改写（对象 + 方法 → 结论），`upstream` 照正文的「上游输入」行填单元 ID。

## 老项目怎么手工补 `explore/`

已经在用两侧布局的项目，三步补上第三侧：

```bash
SKILL=~/.claude/skills/project-init-loose ; PROJ=<项目绝对路径>
cp -r "$SKILL/templates/explore" "$PROJ/explore"          # 若已有 explore/，改成只补 CLAUDE.md 与 _templates/
cp "$SKILL/templates/agents/explorer.md" "$PROJ/.claude/agents/explorer.md"
grep -rl '<CANONICAL_ROOT>' "$PROJ/explore" "$PROJ/.claude/agents/explorer.md" \
  | xargs sed -i "s#<CANONICAL_ROOT>#$PROJ#g"
```

然后手工同步这三处（模板已改好，照抄即可）：根 `CLAUDE.md` 加 `explore/` 行 + 派活行加 `explorer`；`mgmt/CLAUDE.md` 加「`explore/` 默认不回流」一段；`analyst.md` / `mgr.md` / `reviewer.md` 各补一句边界。

## 许可

个人使用，无附加许可声明。
