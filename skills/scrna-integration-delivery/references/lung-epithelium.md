# 人与小鼠肺上皮 marker 字典

仅在本 skill 已由用户指名、且当前任务需要肺上皮 marker／状态参考时读取。面向成年肺及常见损伤修复背景；包含近端气道、远端气道和肺泡，解剖位置须匹配实际取样。胎肺发育、肿瘤和特殊模型应另外选择参考，不能把此表当作完整细胞图谱。

- [面板 TSV](../assets/lung-epithelium/panels.tsv)：每行是一个物种的身份、候选 subtype 或 state；基因列以分号分隔，可直接读入 R/Python。
- [来源 TSV](../assets/lung-epithelium/sources.tsv)：按 `source_ids` 关联论文／官方基因集、物种、背景、核对范围和日期。

本表是人工提炼的关键 marker 面板，不是原论文完整签名或已在当前项目验证的分类器。来源支持的模型／人群、跨物种资源映射与本项目观察分别解释；以实际表达、多基因共表达和跨样本支持决定是否采用标签。

## 读取与选择

1. 按 `species` 选择 `mmu` 或 `hsa`，再依据取样位置、已有身份与目标 theme 过滤。两物种分别列基因；不能通过修改大小写实现同源映射，也不把一物种特有的面板强补到另一物种。
2. `identity` 建立 AT1、AT2、Club、Goblet、Ciliated、Basal、PNEC、Tuft/Tuft-like、Ionocyte 等背景；`subtype_candidate` 是研究定义的亚群候选；`state` 可叠加于身份，不能替代身份。先看 `parent_identity`，再看候选面板。
3. 将选中行复制到项目配置，保存字典版本／摘要、来源和修改。映射实际 feature ID，记录缺失、别名及多重映射；项目明确排除的基因继续排除。保持数据驱动 top3 独立计算。
4. 正向 marker 用于共同支持；`context_genes` 是父身份或解释背景，`negative_genes` 是文献中相对降低／缺少的对照。后两者不默认加入正向 UCell；单细胞 dropout 不能证明阴性。

| 主题 | 重点候选与使用边界 |
| --- | --- |
| 肺泡身份与 AT2 异质性 | AT1／AT2；鼠 Axin2/Tm4sf1、人 TM4SF1 相关 AEP 候选；人 WIF1/HHIP/CA2 与 AT2-signaling 面板。表达相似不等于干性、自我更新或跨物种亚群同一性 |
| 气道与稀有细胞 | 基底、Club、黏液分泌、成熟纤毛及 PNEC／Tuft／Ionocyte；鼠 hillock、人 suprabasal／squamous 候选需要解剖与背景支持。CFTR、FOXI1 或 KRT8 单独阳性均不足以定型 |
| 远端分泌与双谱系表达 | 人 RAS-associated，鼠 BASC 共表达及 H2-K1-high Club-like。RAS 不直接等同小鼠 Club；Scgb1a1/Sftpc 双阳性须排除 ambient RNA／doublet，BASC 还需位置及谱系证据 |
| 损伤与分化 | 鼠 activated／primed AT2、DATP／PATS／ADI，人 transitional-like、aberrant-basaloid-like，及两物种 deuterosomal。几个文献标签存在重叠，不强排必经阶段或宣称轨迹方向 |
| 可叠加程序与技术背景 | E2F／G2M、IFN、TNF–NFκB、UPR、ROS、hypoxia、MHC-II、即时早期及热休克程序。程序高分不证明刺激来源、通路因果、真实增殖率或细胞衰老 |

## 物种和背景差异

- 人 basal 使用 `TP63`，小鼠为 `Trp63`；人 Club 的 `CYP2F1` 与鼠 `Cyp2f2` 分开列出。人 `SFTPA1/SFTPA2` 不能机械变成两个小鼠同名基因。
- 人气道 tuft-like 面板使用 `POU2F3;ASCL2;LRMP`；原研究中未检出一些经典鼠 tuft marker，故人面板不强求 `TRPM5/GNAT3`。同时注意部分人 tuft-like 细胞可表达 FOXI1，联合 CFTR 和 tuft 证据区分 ionocyte。[Goldfarbmuren 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7237663/)
- 人 RAS 面板的 `SCGB3A2/CEACAM6` 来自远端气道研究；孤立的 SCGB3A2 不足以区分 Club、RAS 或 AT2 相关状态。[Basil 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC9297319/)
- 人 basaloid-like 候选需联合 `KRT17/TP63/LAMB3/LAMC2/MMP7` 与 KRT5/KRT15 相对缺少的证据，仍需确认上皮身份与疾病背景；KRT17 单独表达不能诊断该状态。[Adams 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7439502/)
- DATP、PATS、ADI 的鼠面板与人类 transitional-like 面板分开保存；KRT8/CLDN4 与损伤有关，但不是所有组织／细胞中的特异过渡标志。原文的谱系或功能结论不能由面板分数迁移到新数据。[Choi 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7487779/) · [Kobayashi 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7461628/) · [Strunz 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7366678/)
- Deuterosomal 的中心粒扩增程序可含细胞周期相关基因，不能直接标成分裂细胞；MHC-II 也可来自上皮本身，不凭 CD74/HLA/H2 单独判为免疫污染。按完整身份、同细胞证据和样本层面模式复核。

## 与 DotPlot、UCell 的衔接

`theme` 可直接用于已知 marker DotPlot 的 x 分面；cluster 图 y 分面仍采用本项目正式 celltype 映射。`positive_genes`、背景和负向基因显示时注明角色；面板是先验，不按其最高分强制命名。

`score_policy` 的含义：

| 值 | 使用方式 |
| --- | --- |
| `marker_panel_only` | 默认用于表达图和联合证据；如需据此评分，需在项目中声明为自定义短面板，记录有效基因数、覆盖与判定规则，不称为原文完整签名 |
| `coexpression_only` | 关注同细胞共表达及来源／解剖证据，不用两个基因的单一 UCell 分数建立 BASC 或 AEP 标签 |
| `full_signature_preferred` | 表内只含官方基因集中的少量展示 marker。需要状态评分时优先读取项目固定版本的完整 `signature_id`；短面板评分须另命名并明确它不是完整 Hallmark/Reactome 分数 |

核对基因集物种、实际 feature 覆盖、评分输入和参数；不沿用 E20 的固定分数门槛。某一 marker 缺失不自动否定身份，但覆盖不足时不得给出可靠分数或确定标签。不同程序可重叠，不能把 state 分数直接归一化为互斥细胞组成。

## 核验与维护

面板键为 `species + panel_id`，来源 ID 必须存在；正向、背景、负向基因角色不得意外重叠。新增项要保留其原始证据物种与背景，不能将官方同源映射资源表述为该物种肺上皮的实验验证。本次核对的是文献／资源与字典结构，未在实际 scRNA 队列上验证灵敏度、特异度或 UCell 阈值。
