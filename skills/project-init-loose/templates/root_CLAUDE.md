# <项目名>

> <一句话项目背景>。规范根：`<CANONICAL_ROOT>`。

| 当前任务 | 先读 |
|---|---|
| 背景、研究数据、实验设计 | `mgmt/PROJECT.md`、`mgmt/RESOURCES.md` 中相关部分 |
| 项目类别与选择依据 | `mgmt/PROJECT.md` |
| 参考数据、工具代码、运行环境与启动命令 | [.project/DEPENDENCIES.md](.project/DEPENDENCIES.md) |
| 规划与结论整理 | `mgmt/CLAUDE.md` |
| 主线分析 / 旁支探索 | `analysis/CLAUDE.md` / `explore/CLAUDE.md` |
| 查找已有成果 | `TASKS.md` → 候选任务 `ABSTRACT.md` → 相关文档与产物 |
| 归档、恢复、清理 | `.project/ARCHIVE.md` |

`data/` 只读；先查 `mgmt/RESOURCES.md` 和元数据，勿用 `find`、`ls -R`、`tree` 递归枚举。`_archived/` 默认不进入日常读取和活跃索引。
四个角色 `mgr`、`analyst`、`explorer`、`reviewer` 可按需要委派；正式审核按用户请求开展。

绝对路径统一使用上述规范根，软链别名不作为记录路径。

## Scientific requirements

以下要求按任务涉及的数据处理、统计推断和生物学解释环节应用；纯配置、编码或样式调整仅检查其实际影响范围。

### Scientific analysis

- 对统计分析或生物学解释，按任务需要明确研究对象、比较关系、推断单位和预期产出。
- 涉及跨条件推断时，尊重独立生物学重复，避免 `pseudoreplication`，并考虑 sample/donor 或相应独立实验单位层面的变异。
- 区分数据观察、统计关联、候选机制和因果证据，使用与证据强度匹配的措辞；代码成功运行不代表科学结论成立。
- 优先关注 effect size、跨样本一致性、生物学相关性和稳健性，而不只关注 `p value` 或 FDR。
- 方法讨论与实验设计可依据已有知识、文献和明确标注的假设。生物学知识可用于提出假设、选择方法和解释结果，但不能替代实际数据证据。
- 对关键结论评估最可能改变判断的混杂因素和替代解释；不默认进行穷举式验证。

### Data and computation

- 对映射、标识符、坐标、维度或分组不一致，先定位并依据明确规则处理；可修复的问题核验后继续，预期缺失或多重映射报告处理方式及影响范围。仍无法解决且会破坏结果有效性的错误，停止受影响步骤，不使用 silent fallback 掩盖问题。
- 对大型组学数据优先使用 sparse、vectorized、chunked 或已有中间结果，避免不必要的 densify、复制和重复计算；复用中间结果前核对输入、关键参数及相关版本是否适配。
- 对影响结论的分析，保留足以复现的脚本、关键参数、输入来源及必要的环境信息；优先沿用项目已有记录方式。
