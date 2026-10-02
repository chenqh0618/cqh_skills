# 生物医学论文主线精读 · 精简版

技能名：`biomedical-paper-mainline-reader` · 版本：1.0.0

这是详细版 `biomedical-paper-evidence-reader` 的独立精简变体，不覆盖原包。生成本文件包不代表已经安装或更新到账户。

## 这版怎样读论文

先交代背景、问题和总体思路，然后用3–5个关键研究节点串联证据；不按所有主图/子图完整概括。固定提炼对“肺损伤修复的细胞动态和分子机制”的2–4条高价值启发，数量不够时不凑数。默认正文约2,000–3,500个中文字，交付单文件HTML。

保留的不是全部细节，而是影响结论的关键实验/分析、直接结果、转折和边界。论文结论与面向用户课题的推演必须区分。

## 调用文字

> 使用“生物医学论文主线精读”解读这篇论文。先说明背景和目的，再沿研究主线选择关键证据展开，不做逐图完整概括。针对我的肺损伤修复细胞动态与分子机制研究，提炼最值得参考的问题、设计、方法或其他启发，区分现有数据可尝试与新增验证，最终输出HTML。

具体队列或当前重点变更时，在请求中直接说明；`references/research-context.md` 是可更新的默认背景。

## 文件

- `SKILL.md`：核心流程与边界。
- `references/research-context.md`：用户课题背景及使用条件。
- `assets/report-template.html`：内嵌样式的离线HTML外壳。
- `scripts/build_report.py`：Python标准库渲染器，无网络依赖。
- `examples/preview.json` / `examples/preview.html`：结构演示，不含真实论文发现。
- `tests/`：渲染功能测试与语义检查场景。

## 生成与验证

```bash
python scripts/build_report.py examples/preview.json preview.html
python -m unittest discover -s tests -p 'test_*.py' -v
```

生成器输入已经撰写的分析JSON，不会自动下载或理解论文。正文字段按纯文本转义；不支持把HTML、Markdown、LaTeX或Mermaid直接塞入字段作为已渲染内容。需要复杂图示时，可在人工核验后扩展模板，用离线静态形式呈现。不是每篇论文都需要图示。

本版本取消全部主图/子图覆盖校验，改为检查来源、主线节点、课题启发与材料状态；它不检查科学结论真伪。报告状态使用“主线精读”“材料有限”“模板演示”，不使用“完整逐图审计”。视觉和功能验证结果见 `tests/validation-results.txt`；没有对真实论文完成端到端学术质量验证。