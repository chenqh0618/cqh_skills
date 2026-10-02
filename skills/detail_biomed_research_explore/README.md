# 生物医学研究论文解读 Skill

**名称：** `detail_biomed_research_explore`  
**版本：** 1.0.0（2026-09-30）  
**目标：** 先阐述研究背景、目的和整体框架，再按主图分析证据与逻辑，最终交付独立 HTML。

## 已创建的内容与安装状态

本包包含可复用的 SKILL.md、逐图工作规范、证据审查清单、HTML 模板、可运行的离线生成脚本、结构演示和测试用例。**生成 ZIP 不等于已安装到账户；本次没有通过账户写入接口完成安装。**

## 在 ChatGPT 中使用

账户已开放 Skills 入口时，在 **Plugins → Skills → Create → Upload from your computer** 上传技能 ZIP，完成界面要求的扫描/审核/安装。解压后的顶层目录包含 SKILL.md。实际能否上传、安装及展示取决于账号/工作区开放和权限；以界面结果为准。安装后可选中此技能，或在论文解读请求中明确点名。

官方操作说明（核验日期 2026-09-30）：
- [Skills in ChatGPT](https://help.openai.com/en/articles/20001066-skills-in-chatgpt)
- [Using skills](https://openai.com/academy/skills/)
- [Skill 文件与目录组织参考](https://developers.openai.com/api/docs/guides/tools-skills)

官方说明列出的可用用户/工作区存在范围限制；不要将这里的操作说明理解为所有个人账号都必定拥有该入口。

当前界面没有 Skills 入口时，可以将 `SKILL.md`、需要的 references 文件和论文上传到普通聊天，明确要求按文件执行。此方式是当次调用指令，不是原生 Skill 注册，不保证跨会话自动加载。也可直接上传整个包并要求先读取 SKILL.md；运行脚本前应解压并审阅。

## 调用示例

> 使用“生物医学研究论文解读：证据与逻辑”解读我上传的论文。先讲研究背景、目的和整体框架，再按全部主图和关键补充证据分析：为什么做、要检验什么、实验设计、直接结果、证据如何支持结论、仍有哪些问题，以及图与图的承接。不要把推断写成已证实机制。最终生成单文件 HTML。

可以额外指定：重点关注某几幅图、临床/图谱/机制维度、某条竞争解释或与自己的研究课题关联。没有额外指定时，按全文主图系统解读，不自行缩为摘要。

## 目录

```text
detail_biomed_research_explore/
  SKILL.md
  README.md
  CHANGELOG.md
  references/
    figure-workflow.md
    evidence-review.md
    html-spec.md
    quality-checklist.md
  assets/
    report-template.html
  scripts/
    build_report.py
  examples/
    template-report.json
    report-preview.html
  tests/
    evaluation-cases.md
    test_renderer.py
    validation-results.txt
```

## 本地生成 HTML

生成器使用 Python 标准库，无第三方包、网络、账户或 API 密钥依赖。它只接受已经整理好的分析 JSON，并不自动理解论文。

```bash
python scripts/build_report.py examples/template-report.json report.html
python -m unittest discover -s tests -p 'test_*.py' -v
```

真正论文的数据结构可从演示 JSON 修改；主图和子图清单必须重新从真实论文提取。将 `metadata.status` 改为 `partial` 或 `complete` 时必须据实际材料覆盖和图像核验情况，不能仅为隐藏模板提示而修改。

## 呈现与安全

HTML 内嵌样式，原生目录与打印布局；公式支持安全 MathML，流程支持原生 HTML 或预渲染图片；图像可转换为内嵌 data URI。引用可跳转。生成脚本不调用网络，不上传文件，不访问邮件，不读取凭据。

代码做输入转义、图片路径范围限制、SVG/MathML 检查、子图覆盖和锚点校验；这些不构成对任意不可信程序的沙箱，也不替代模型对资料中指令注入的识别。

## 验证边界

代码与模板使用合成结构进行功能测试，并提供桌面/窄屏渲染检查。语义评估用例已编写；**未使用真实论文完成端到端学术质量验证**。结构检查通过不代表因果解释、样本量读取或来源判断一定正确。

## 维护

新增研究类型时优先扩展 references，不把 SKILL.md 变成巨大知识库。变更影响输出结构时，同步更新模板、演示 JSON、测试和 CHANGELOG。保留对观察/解释/结论边界的区分，不为更顺畅的故事牺牲证据准确性。
