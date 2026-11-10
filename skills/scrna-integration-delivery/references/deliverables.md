# 目录与结果文件

用于整理交付入口、导出表和对象、编写分支说明。目录是新交付的优先布局；已有等价文件可通过索引关联，不要求为布局重跑分析。

## 分支与路径

- 一个单元对应明确的数据集及版本。`analysis_object` 表示全数据集、谱系、celltype 或明确的细胞组合；保存成员与父对象来源。
- `workflow_id` 表示归一化、整合算法、整合分组及必要参数变体，例如 `SCT_harmony_sample`。归一化分组、整合分组、拟合范围分别记录，不能靠文件名推断。
- 分支键为数据集、对象和流程；cluster 还须带 resolution。不同分支的同号 cluster 不表示同一群体。

```text
<unit>/
├── SUMMARY.md
├── AS_RUN.md
├── config/                              # 实际参数、基因集、theme、颜色和顺序
├── scripts/
├── logs/
├── results/
│   ├── figures/<analysis_object>/<workflow_id>/
│   │   ├── identity/
│   │   ├── focus_genes/
│   │   ├── states/
│   │   ├── metadata/
│   │   ├── technical_metrics/
│   │   ├── markers/
│   │   └── composition/{celltype,cluster_r<resolution>}/
│   ├── tables/
│   │   ├── index/
│   │   └── <workflow_id>/<analysis_object>/
│   │       ├── 01_input/
│   │       ├── 02_integration_clustering/
│   │       ├── 03_annotation/
│   │       ├── 04_scores/
│   │       ├── 05_markers/
│   │       ├── 06_composition/
│   │       └── 99_validation/
│   └── data/<workflow_id>/<analysis_object>/
│       └── annotated.rds                 # 或 h5ad，及实际必需的矩阵／模型
└── work/<workflow_id>/<analysis_object>/<step>/
```

仅建立有实际产物的目录。图形底表放入对应的 `tables/` 步骤，`figures/` 只放图。正式对象、必要矩阵／模型放 `results/data/`；可再生中间结果放 `work/`。后者不是正式结果的唯一入口。单元的 `results/data/` 与项目原始数据目录含义不同。

沿用已有项目的摘要和执行记录文件名。已有 `<scope>/{rds,figures,tables}` 等输出时，保留实际计算接口，由项目导出或索引关联到交付结构；对象索引指向唯一权威文件，不重复复制大型表达矩阵。跨单元输入使用明确文件及版本，不依赖“最新文件”或含义未定义的当前工作目录。

文件名包含内容、层级、必要的 resolution 和页码，如 `dotplot.by_cluster.cluster_top3.r0p6.page01.pdf`；`r0p6` 只是示例。PDF/PNG 使用相同 stem。重绘可再生图按项目约定更新，正式科学对象更新保留可追溯版本。

## 文件内容

以下为完整交付的适用清单。局部任务只处理被请求部分；已有等价内容可直接登记。大表采用压缩 TSV，参数和环境记录沿用项目格式。

| 位置 | 内容与示例 |
| --- | --- |
| `tables/index/` | 分支汇总、对象索引、图形索引、其他产物索引；登记完成／缺失／不适用状态及原因 |
| `01_input/` | 样本元数据、保留细胞清单、过滤前后数量、feature 映射与排除、输入来源及摘要；记录 sample/donor/library、原 barcode、reference/projected，以及流程间或对象间的成员交集 |
| `02_integration_clustering/` | 实际表示、归一化／整合参数、HVG、维度、邻居图设置、seed、坐标、全部已计算分辨率的 cluster 和群数、主分辨率选择 |
| `03_annotation/` | 逐细胞 metadata、cluster→celltype 映射、marker／参考证据、置信度及不确定原因；身份、state、QC、旧／新标签分列 |
| `04_scores/` | 逐细胞 UCell、基因集成员及来源／版本、有效覆盖、RNA 层、评分参数、样本／群体摘要、继承或重算记录 |
| `05_markers/` | 已知 marker/theme、cluster 与 celltype 各自候选排名、top3 选择和可用性、DotPlot 数值底表及行列／分页映射 |
| `06_composition/` | 样本×类别数量、分母与比例，样本有效性，组平均比例与有效样本数，层级和 resolution |
| `99_validation/` | 本次及复用检查的证据入口，实际通过／失败／未执行范围，图形可读性核验 |
| `data/` | 最终 Seurat/AnnData 对象及必要外置矩阵／模型；保留约定 RNA 层、metadata、聚类、已有坐标和评分，明确外置数据的细胞／feature 映射 |

对象索引至少记录分支、实际路径、细胞／样本数量、输入与对象版本及必要哈希。图形索引记录分支、类别、特征、层级／resolution、reduction、细胞范围、文件及底表路径、页码、图幅和 DPI。相对路径统一以单元根为基准，或使用项目规定的规范绝对路径；底表可据索引定位，无需在目录中重复保存。

## 每条流程的结果说明

每个对象×流程在摘要中有独立段落，较长时链接分支报告，按以下内容解释实际结果：

1. **对象与输入**：来源、过滤规则、细胞／样本／供体数、拟合与投影范围；其他方法是否使用相同成员。
2. **整合与聚类**：实际表示和分组、主要参数、主分辨率与群数、必要的校正前后诊断；完整细节链接参数表。
3. **注释与状态**：cluster 的身份及证据、混合和未定项、关注基因、UCell 模式；既有标签与新标签的变化有依据。
4. **marker 与组成**：已知及数据驱动 marker、逐样本出现情况、数量／比例及分母，是否由少数样本或技术指标驱动。
5. **解释与入口**：重要的混杂、可比性限制、缺失／失败项，以及对象、图形、底表和实际运行记录。

UMAP 混匀不能单独证明整合有效；时间与 batch 的混杂也不会通过整合自动分离。摘要中按证据强度陈述观察、关联和候选解释，不从交付完整性推断科学结论成立。

## 核验

核对本次目录及索引可解析、完成的产物非空、对象／表格／坐标按细胞 ID 对应、标签属于正确分支和 resolution、图与底表可追溯。确认关键版本及必要哈希、实际参数和执行范围有记录。缺图、未定注释或不适用的统计项保留原因，不用空目录或预期文件名代替交付。
