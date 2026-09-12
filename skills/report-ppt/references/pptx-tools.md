# PPT 辅助工具

共享模块为本 skill 根目录下的 `scripts/pptx_support.py`。从已加载的 skill 路径定位它，不猜测当前工作目录；Claude 的 `scripts/` 链接指向同一模块。将模块复制到任务构建目录，与 `build_slides.py` 放在一起后再使用。

依赖为 `python-pptx` 与 Pillow；渲染额外需要 LibreOffice 和 `pdftoppm`。所有函数处理展示对象，不计算统计结果或判断科学证据。

## 生成接口

- `new_presentation()`：创建空白 16:9 PPTX。使用现有模板时直接用 `pptx.Presentation(template)`。
- `set_font(text_frame, name="Noto Sans CJK SC", size=None)`：填写文字后设置段落和 run 字体，包含 East Asian 字体；`size` 单位为 pt。表格需对每个单元格调用。在目标环境先确认字体实际存在。
- `add_picture_fit(slide, path, left, top, width, height)`：在指定框内居中等比例显示图片，不裁切。位置及框尺寸均用 `pptx.util.Inches()` 等转换后的 EMU。两个输出尺寸由像素比例计算，可处理横纵 DPI 不同的图片。缺失或不可读取的图片明确报错，由 agent 回到证据处理步骤决定如何呈现。
- `set_notes(slide, narration, sources=())`：写入非空讲稿，将来源字符串列表另列在“证据来源”下。来源路径相对于成品 PPTX，具体来源语义由 agent 核实。
- 页面标题使用原生标题占位符，或将自建标题文本框的 `name` 设置为 `report-title`，供检查器准确识别。

生成脚本的最小用法（实际内容和布局按任务填写）：

```python
from pathlib import Path
from pptx.util import Inches
from pptx_support import new_presentation, set_font, set_notes, add_picture_fit

BUILD_DIR = Path(__file__).resolve().parent
REPORT_DIR = BUILD_DIR.parent.parent  # 默认 report/_build/<成品名>/ 布局
RESULT_DIR = REPORT_DIR.parent
prs = new_presentation()
slide = prs.slides.add_slide(prs.slide_layouts[6])
title = slide.shapes.add_textbox(Inches(0.6), Inches(0.35), Inches(12), Inches(0.7))
title.name = "report-title"
title.text = "本页证据支持的判断"
set_font(title.text_frame, size=30)
add_picture_fit(slide, RESULT_DIR / "figures/result.png",
                Inches(0.7), Inches(1.3), Inches(11.9), Inches(4.8))
set_notes(slide, "根据真实任务填写讲稿。", ["../tables/result.tsv：具体比较与列名"])
# 根据工作流确定未占用的成品名；保存前核实数字、图注及可见限制。
```

添加图片只负责布局。使用 PDF/SVG 等当前环境不能直接嵌入的源图时，在任务构建目录中转换为 PNG，保留源文件、转换参数和足以读清图内文字的分辨率。

## 检查与渲染

在使用当前任务副本的环境运行，路径含空格时正确引用：

```bash
python pptx_support.py check /path/to/slides.pptx
python pptx_support.py check /path/to/slides.pptx --aspect 4:3
python pptx_support.py render /path/to/slides.pptx --out-dir /path/to/new-preview
```

`check` 重新打开成品，输出 JSON；有错误退出码为 1，无错误为 0。检查比例、非空标题和备注、顶层元素边界（包含旋转）、图片比例。组合对象内部、文字溢出、元素重叠、图表可读性及科学内容仍需人工或 agent 查看，警告不会被当作已通过视觉验收。

`render` 使用隔离的 LibreOffice profile，先在临时目录转换，再向新的或空的输出目录写入 `deck.pdf` 与全部 `page-*.png`。每个外部进程默认超时 60 秒；工具缺失、渲染失败或输出目录非空会明确报错，不修改 PPTX，不接受陈旧预览。默认 110 DPI，局部文字需要细看时可提高 `--dpi`。

测试使用标准库 `unittest`：在 skill 根目录运行 `python -B -m unittest discover -s tests -v`。
