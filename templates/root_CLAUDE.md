# <项目名> — 三侧组织约定（指路，不定细则）

> 项目：<一句话项目背景>。背景与数据见 `mgmt/PROJECT.md` / `mgmt/RESOURCES.md`。**规范根**：`<CANONICAL_ROOT>`——绝对路径统一用此前缀，有软链别名时只认规范根。

| 侧 | 放什么 | 开工先读 |
|---|---|---|
| `mgmt/` | 科学问题 / 数据清单 / 任务链与进度 / 结论账本 / 方案（轻） | `mgmt/CLAUDE.md` |
| `analysis/` | 分析单元 `A<idx>_<内容>_<MMDD>`：脚本·日志·结果·SUMMARY（重，主线） | `analysis/CLAUDE.md` |
| `explore/` | 探索单元 `E<idx>_<内容>_<MMDD>`：同 `analysis/` 规格，但**不进主线** | `explore/CLAUDE.md` |

**各侧规则彼此独立且各自完整——进哪侧就先读那侧的 `CLAUDE.md`。** 管理与分析两侧只有两条通道：方案靠用户点名进分析侧（不自动流转）；结果靠 `analysis/A*/SUMMARY.md` 回到管理侧。
`explore/` 默认不回流：E 不进任务表、结论不自动进账本，用户点名才收。
`data/` 只读，勿用 `find`/`ls -R`/`tree` 递归枚举；要数据清单读 `mgmt/RESOURCES.md`。
**默认不翻别的分析/探索单元**；每个 `SUMMARY.md` 顶部有 `abstract` + `upstream`，要总览跑 `bin/abstracts.sh`，据此再决定展开谁。
派活：`mgr`（管理侧）· `analyst`（分析侧，派单须带用户原话）· `explorer`（探索侧，派单须带用户原话）· `reviewer`（仅用户点名审核时）。
