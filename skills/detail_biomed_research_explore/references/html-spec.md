# HTML 交付规范

## 结构

单文件 UTF-8，默认中文。顺序固定为：标题与论文身份/版本 → 材料覆盖 → 背景/目的/设计 → 主图路线 → 逐图证据链 → 综合回答/工作模型/贡献/缺口/后续验证 → 参考来源 → 质量与限制说明。

默认以清晰段落为主，表格只负责比较和证据定位。逐图分析占主要篇幅；不要将整篇论文压缩成卡片标题。桌面侧栏目录与窄屏可换行目录；表格局部滚动而不是整页横向溢出；打印模式移除固定导航与按钮。

## 可追溯来源

JSON `sources` 中每条来源有唯一 `id`、完整 `citation`、可选的 `url`、`kind`、`locator` 与 `accessed`。正文段落/子图通过 `refs` 列表引用来源 ID；`locator` 给出 Figure、子图、PDF 页或方法节。

示意：正文“【有范围的结论】[1]（Fig. 2c–e；PDF p. 7；Methods: ...）”。引用写在相应结论附近。用户提供的本地 PDF 可以没有公开 URL，但保留文件名、论文身份和页码。不要伪造 DOI、页码或子图；HTML 中不保留 `turn...` 或平台私有引用 token。

## 原图与资源

仅嵌入实际读取并能核对来源的图。原图嵌入与全文阅读是两个不同要求；无法合法嵌入时，用图号/来源与文字解读替代转载，不能伪造原图。用户提供论文时可在分析需要范围内使用相关图像。公开获取材料尊重许可，避免无必要地重发全部原图。

`images` 支持本地 PNG、JPEG、WebP、GIF 或经过安全检查的 SVG，脚本转换为 data URI。`path` 须在 `--assets-root` 内，不能指向网络或系统私密文件；保留 `alt`、`caption`、`source`。

公式可用 `math` 区块的安全 MathML 和 `source`（原始 LaTeX）离线显示；或以已渲染 SVG/PNG 图块展示。复杂公式优先核对原文符号和上下标，数学源码仅作为可展开备份，不能代替渲染。

Mermaid 可预渲染为经检查的 SVG 图像，再通过 `image` 区块嵌入，同时在 `code` 区块保留源。环境没有 Mermaid 渲染器时，改用 `flow` 原生 HTML 节点并保留同等关系，不需要为了装饰强制加图。不自动联网下载依赖；不能默默改成 CDN 后声称离线可用。

## 生成器输入

使用 `examples/template-report.json` 作可编辑起点，**不得把演示措辞留在真实完整报告里**。

- `metadata.status`：`template`（结构演示）、`partial`（部分解读）或 `complete`（完整材料范围的解读）。`complete` 要求全部主图已记录且原图已核验，Methods/正文材料覆盖未缺失。补充材料是否齐全单独说明；有影响核心主张的缺失不能声称完整。
- `expected_main_figures`：源文确认的主图标签列表，须与 `figures[].label` 对应。
- 每幅图必须填写 `context/question/design/results/inference/limitations/bridge` 和 `panels`；这些对应八项分析（`panels` 是第四项）。
- `expected_panels` 为源文所有子图标签，`panels[].labels` 分组覆盖这些标签且不得遗漏/重复。
- 区块可用普通字符串，或 `p`、`callout`、`table`、`flow`、`math`、`image`、`code` 类型。字符串只显示为纯文本，不隐式解释 Markdown/HTML。
- `figure_map` 为主图导航；`synthesis` 为综合回答分节。
- `quality` 展示已完成检查和未解决事项，不能自动等同科学质量已通过。

构建：
```bash
python scripts/build_report.py report.json output.html --assets-root /path/to/assets
```

生成器使用 Python 标准库，无联网、无账号依赖。遇到材料不全，填写清楚“未获取/未核验”，并使用 `partial`，不要绕过校验将其改为 `complete`。

## 检查

静态校验唯一 ID、引用 ID、内部锚点、图片文件路径、图标签覆盖、元数据和必填章节。浏览器分别检查桌面/手机布局、表格滚动、中文、目录、公式、图片和打印样式。断网模式验证无外部资源依赖；外部参考文献链接需要网络属于正常情形，不代表正文不能离线阅读。

没有浏览器测试时，不写“已验证所有浏览器兼容”。HTML 内容有模板/占位符时标题和页面显著标识为模板，不能交付成完成的论文报告。
