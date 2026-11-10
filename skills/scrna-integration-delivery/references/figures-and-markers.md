# 降维图与 marker

用于所请求的降维图、DotPlot 及其派生计算。完整图形交付覆盖以下适用类别；指定单类补图时只执行对应部分。

## 降维图

默认以已有 UMAP 为主要展示空间，标明实际 reduction。保留已计算的其他空间坐标；t-SNE／PHATE 等是否展开同套图按项目配置，不仅为填补清单增加计算。整合前后图使用相同细胞范围，注明校正前／后表示。

| 类别 | 内容 |
| --- | --- |
| `identity` | 各已计算 resolution 的 cluster、主分辨率 cluster 与 celltype、注释状态／置信度和未定项；有 state/subtype、来源标签或 reference/projected 区分时展示对应信息 |
| `focus_genes` | 指定关注基因的 RNA 表达分布，标明基因映射、数值层及归一化；零表达和 feature 不可用分别显示 |
| `states` | 指定的 UCell scores，关联基因集版本、覆盖及可用状态；分数继承与重算分别记录 |
| `metadata` | 实际存在的 sample、donor、library、condition、时间、batch、group，类别顺序依据实验设计固定 |
| `technical_metrics` | nCount、nFeature、线粒体／核糖体比例、doublet score、去污染指标等逐细胞技术指标，注明原始／校正来源及单位 |

HVG 数、PC 数、resolution 和整合参数属于分支级信息，写入参数表或图注，不伪造为逐细胞变化。复用 UCell 前核对细胞、输入 RNA 层、签名及参数；缺少评分时只有在任务要求且具备基因集／参数的情况下补算。不能仅因重新聚类就声称重新评分，也不能根据最高分自动赋予确定身份。

同一对象、同一可比指标跨流程使用共同色阶，默认覆盖其全部有效值；变换／截断须标注并记录。不同 RNA 层或评分规则不强行共用色阶；不同 UCell 签名的分数不能直接用于排列生物程序强弱。相同身份／样本使用固定颜色；cluster 颜色只在对应分支与 resolution 内解释。

PDF 与 300 dpi PNG 配套输出。按最终展示尺寸排版，正文／坐标文字以约 11–12 pt 为起点，长标签换行、面板过多分页；图例、分面条和标题清晰，避免重叠和裁切。各嵌入可有不同几何范围，不据此直接比较二维距离。

## DotPlot 分组与分面

完整 marker 交付提供 `by_cluster`、`by_celltype` 两种聚合，分别展示 `known_markers`、`cluster_top3`、`celltype_top3` 三类基因面板；不适用项说明原因。已知 marker 按身份、功能或文献主题配置，不限定每类只能三个基因。

人和小鼠肺上皮可从[内置字典](lung-epithelium.md)选择有物种与背景依据的已知 marker/theme。该字典不替代当前数据的 top3，也不自动改写注释；短 marker 面板与完整 UCell 签名按字典说明分别使用。

| 元素 | 要求 |
| --- | --- |
| x 轴 | 基因，按 `theme` 分面。已知 marker 使用声明的身份／功能／文献主题；数据驱动 top3 的主题为来源群，如 `Top3: cluster C1`，不凭排名杜撰功能解释 |
| cluster 图 y 轴 | 主分辨率 cluster，按该分辨率正式 `cluster_celltype` 映射分面；所有面板都按 celltype 分面，不能把 top3 来源 cluster 或 state 代替此分面 |
| celltype 图 y 轴 | 逐细胞 celltype 标签聚合后的类别；默认直接显示，有明确父层级时可附加父层级分面 |
| 不确定身份 | 混合、ambiguous、unresolved 等保留独立分面；缺少正式 cluster 身份映射时标记未评估，不默默改用多数标签 |
| 点矩阵 | 展示全部行群体 × 面板基因，x 按来源分面只影响布局，不能只显示各群自己的 marker |
| 点面积 | `100 × mean(counts > 0)`，范围 0–100%；显式存储的稀疏零不计阳性 |
| 点颜色 | 约定未整合 RNA 的 `mean(log1p(normalized_counts))`，默认不逐基因做 z-score |
| 缺失与零 | 已测得的零表达为 0；feature 不可用为 NA，使用独立符号，不把缺失补成零 |

已知 marker 表保存 `gene_key`、symbol、theme、来源、正向／负向／背景角色和显示顺序。同一基因可在多个 theme 出现，使用不同面板列键，统计时不重复加权。稳定 ID 与 symbol 映射保留；重复 symbol 默认按 ID 区分。确认多条 feature 属于同一基因而需聚合时，先按明确规则合并 counts，并统一用于排名和展示，不能两处静默使用不同映射。

cluster 先按 celltype 再按 cluster 排列，分页尽量保持主题和行组边界；所有页合起来覆盖完整行列组合。底表保存分组层级、cluster/celltype、theme、基因键、均值、检出率、feature 状态、细胞数和页码。主展示使用全部保留细胞；有 projected 时另导出 reference-only 底表，并明确两种范围。

## 数据驱动 top3

cluster 和 celltype 各自在同一对象、流程及注释版本内执行 one-vs-rest：当前群为 in，其他保留群为 out。celltype top3 直接按逐细胞 celltype 重算，不能拼接 cluster top3 代替。候选不限于已知 marker 或 HVG；按项目规则显式排除人工插入等禁止分析的真实 feature，保留排除与映射记录。

项目已有明确的 RNA 层及计算口径优先；没有约定时可采用以下 E20 经验作为描述性起点，并记录实际选择。这些是本技能的可调整起点，不是软件默认值或所有数据集的固定阈值。

```text
L_i = 第 i 个细胞在完整约定 RNA 层的总 counts
normalized_counts_gi = 10000 × counts_gi / L_i
mean_in/out = 各组 normalized_counts 的算术平均
log2FC = log2(mean_in + 1) - log2(mean_out + 1)
pct_in/out = 各组 counts_gi > 0 的细胞比例，范围 0–1
pct_difference = pct_in - pct_out
```

文库分母使用完整约定 RNA 层，不在筛选 marker、HVG 或分析基因后重算。零文库细胞在输入检查中处理并记录。排名的 log2FC 是先求均值再取对数；DotPlot 颜色是先逐细胞 log1p 再求均值，两者不可混用。

- 起点为有限的 `log2FC ≥ 0.25` 且 `pct_in ≥ 0.10`；按 log2FC 降序、检出率差降序、稳定基因键升序排序，每群至多取三个不同基因。已有项目阈值或用户指定优先。
- 有 reference/projected 区分时默认在 reference 选择 marker；没有时使用全部保留细胞。发现和展示范围分别记录，projected 不是独立验证队列。
- rest 包含其他保留标签，包括未定类别；未定群的富集基因仅为描述性 marker，不据此直接改写身份。
- 仅一个群、in/out 无有效细胞时标记不可计算及原因；不从其他对象借隐含对照。合格 marker 不足三个时保留实际数量，不降低门槛凑数。
- 导出完整候选排名和 top3 选择、可用性表，包含群内外均值、log2FC、检出率、`n_in/n_out`、资格状态及筛选参数。

marker 排名用于描述群体差异，可能受样本构成、测序深度及质量影响。结合跨样本表达支持解释；本流程不自动产生处理条件的统计推断，p value/FDR 也不是本起点的筛选条件。

## 核验

核对细胞 ID、标签版本和表达层，抽查均值／真实检出率与底表一致；核对两层级 top3 分别计算、正确排序和不足原因。检查 x theme 与 cluster y celltype 分面、分页完整矩阵及图例；缺失 feature、单一 celltype、没有 reference 对照时不产生虚假的零值或排名。按实际图幅查看代表图，验证文字、符号、色阶、PDF/PNG 和 DPI。
