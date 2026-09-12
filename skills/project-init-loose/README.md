# project-init-loose

用于生物信息学分析项目的 Codex / Claude Code skill。保留相对独立的管理、主线分析和旁支探索，支持分层阅读、简短运行记录及迁移归档。

## 项目结构

```text
project/
├── CLAUDE.md / AGENTS.md          # 共用规则正文，按当前工作指路
├── TASKS.md                       # 自动生成的非归档任务索引
├── .project/
│   ├── WORKFLOW.md                # A/E 共用工作约定
│   ├── ARCHIVE.md                 # 归档、恢复、清理时读取
│   ├── REVIEW.md                  # 正式审核时读取
│   ├── tasks.py                   # 标准库工具，无数据库、无自动删除
│   └── templates/                # 唯一一套任务文档模板
├── .claude/agents/*.md            # mgr / analyst / explorer / reviewer
├── .codex/agents/*.toml           # 相同职责的 Codex 原生入口
├── mgmt/
│   ├── PROJECT.md / RESOURCES.md
│   ├── PLAN.md / FINDINGS.md
│   └── plans/ / history/
├── analysis/A14_cellTypeProportion_0911_codex/
│   ├── ABSTRACT.md / SUMMARY.md / AS_RUN.md
│   └── scripts/ / logs/ / results/
├── explore/E26_markerSensitivity_0911_claude/
└── _archived/
    ├── INDEX.md
    ├── analysis/
    └── explore/
```

PIPELINE 按教学、汇报或交接需要创建。ABSTRACT 帮助判断相关性；SUMMARY 保存当前有效结论；AS_RUN 给出最终实际方法与复现入口。科学方法变化记录原因和影响，纯样式微调只维护最终代码与产物。

分析与探索的单元根目录保留任务文档，代码、运行日志和有效产物分别放在 `scripts/`、`logs/`、`results/`，这三个目录由任务工具默认创建。`config/`、`work/` 和 `results/` 下的 `figures/`、`tables/`、`objects/` 等子目录按需创建；简单任务无需拆分配置或建立空目录。

任务边界、版本区分和中间文件保留规则统一见 [共同工作约定](templates/project/WORKFLOW.md)，生成后位于 `.project/WORKFLOW.md`。SUMMARY 指明当前有效交付入口；放入 `work/` 不等于允许删除，被下游引用的对象仍需明确保留并记录依赖。

## 使用

需要 Python 3.11+ 和 Git。在 Claude Code 中使用 `/project-init-loose`，在已发现该 skill 的 Codex 中使用 `$project-init-loose`，并说明目标项目。入口见 [SKILL.md](SKILL.md)。

可直接验证空目录的脚手架：

```bash
bash scripts/scaffold.sh /absolute/path/to/project
```

目录须已存在。脚本创建组织骨架并保留已有仓库，不分析原始数据、不创建科学任务、不自动提交。背景和数据清单由调用 skill 的 agent 依据实际材料回填。

本 skill 统一维护在 `cqh_skills/skills/project-init-loose/`。`~/.claude/skills/project-init-loose` 与 `~/.agents/skills/project-init-loose` 均链接到该目录；安装与维护入口见[仓库说明](../../README.md)。原独立仓库保留历史，后续修改在 `cqh_skills` 提交。项目角色分别生成各宿主原生格式，具体是否可调用取决于本机版本和会话工具，不能用根 AGENTS 软链代替角色适配。

## 日常任务

以下命令在生成项目根运行：

```bash
python3 .project/tasks.py new analysis cellTypeProportion --agent codex --question '比较各样本细胞比例'
python3 .project/tasks.py start A01 --agent claude
python3 .project/tasks.py finish A01 --status completed
python3 .project/tasks.py index
```

`new` 仅用于用户已授权目标内的任务；角色交接无需逐个转录用户原话。目录后缀记录创建者，首次实际执行者单独记录，后续接手不改名。A/E 编号各自递增，并计入归档任务。

状态命令只记录事实，不启动或监控计算；completed 不表示科学结论成立。ABSTRACT 允许未知历史字段，旧任务状态无法核实时使用 unknown；不能据此直接归档。

## 归档与恢复

```bash
# 默认预览；实际迁移前检查后台写入与未登记的计算依赖
python3 .project/tasks.py archive A01 --reason '用户已明确放弃该分析'
python3 .project/tasks.py archive A01 --reason '用户已明确放弃该分析' --apply --checked
python3 .project/tasks.py restore A01
python3 .project/tasks.py restore A01 --apply
```

迁移保持原名和内容，原路径记录在 ABSTRACT。归档后先恢复原位再继续执行；不默认保留兼容软链。工具拒绝覆盖、编号冲突、已登记的活跃下游依赖和跨文件系统 rename。

`--checked` 表示执行 agent 已核查进程及未登记依赖，不是新增用户审批。索引和声明依赖无法证明全部运行状态。磁盘清理与迁移分开，按用户授权列清单、评估重算代价和保留必要证据；工具不自动删除文件。

已有项目的选择性升级见 [MIGRATION.md](MIGRATION.md)。设计依据与验证范围见 [AUDIT.md](AUDIT.md)。

## 验证

```bash
python3 -m unittest discover -s tests -v
```

测试只使用临时小项目，覆盖初始化冲突、两端角色格式、任务身份、索引和归档恢复，不运行组学流程或调用外部模型。
