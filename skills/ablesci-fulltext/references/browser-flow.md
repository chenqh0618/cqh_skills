# 已验证的网页流程

2026-10-13 用正常 Playwright Chromium 实测；网站改版时以当前可见表单为准。选择器失效时查看页面再调整，不连续重复提交。授权与预算见 SKILL.md。

## 启动与登录

先检查 Python `playwright` 和 Chromium 是否可用。用一个持续存在的 Python 进程保留会话。交互式 Python 应关闭终端回显并设置 `PYTHON_HISTORY=/dev/null`，退出前清除临时进程的 readline 历史。也可用临时脚本；凭据始终从配置读取。

```python
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

# 用户有明确指定路径时替换 None；否则使用环境变量或默认配置。
explicit_config_path = None
selected_config = explicit_config_path or os.environ.get('ABLESCI_CONFIG')
if selected_config:
    cfg_path = Path(selected_config).expanduser().resolve(strict=True)
else:
    candidates = [Path.cwd() / '.config/ablesci.json',
                  Path.home() / '.config/ablesci/config.json']
    cfg_path = next((p.resolve() for p in candidates if p.is_file()), None)
    if cfg_path is None:
        raise FileNotFoundError('Create a private local configuration from the template')
cfg = json.loads(cfg_path.read_text(encoding='utf-8'))  # 不打印
output_dir = Path(cfg.get('output_dir', str(Path.cwd() / 'R0_ablesciCollect'))).expanduser()
if not output_dir.is_absolute():
    output_dir = cfg_path.parent / output_dir
output_dir = output_dir.resolve()
pw = sync_playwright().start()
browser = pw.chromium.launch(headless=True)
ctx = browser.new_context(accept_downloads=True,
                          viewport={'width': 1280, 'height': 1000})
page = ctx.new_page()
page.goto('https://www.ablesci.com/site/login',
          wait_until='domcontentloaded', timeout=45000)
# 检查确为本站登录表单后填写。
assert page.url.startswith('https://www.ablesci.com/site/login')
page.locator('#LAY-user-login2-email').fill(cfg['email'])
page.locator('#LAY-user-login2-password').fill(cfg['password'])
page.locator('#able-login-submit').click()
```

登录成功后 URL 可能仍为 `/site/login`，页面显示“已登录”“登录成功”；不能仅靠 URL 判断。源码含隐藏的成功模板，要看可见 `inner_text()` 或账号导航，不能在完整 HTML 中搜“登录成功”。不要打印 input value、Cookie、请求头或配置对象。随后检查 `https://www.ablesci.com/my/assist-my`。

## DOI 表单

```python
page.goto('https://www.ablesci.com/assist/create',
          wait_until='domcontentloaded')
page.locator('#onekey').fill(doi)
page.get_by_role('button', name='智能提取文献信息').click()
```

弹窗提供：“信息正确，直接发布”（直接提交，仅在全文模式且已核对类型/预算并写 submitting 后使用）；“信息正确，还需修改”；“信息有误，手动填写”。主表单仍为空不代表提取失败，元数据可能只在弹窗内。

字段：`#Assist-doi`、`#Assist-title`、`#Assist-url`、`#Assist-point`、`#Assist-note`、`#Assist-remark`；提交：`#form-submit-btn`。

## 选择全文或支持材料

输入类型映射见 SKILL.md。支持材料从智能提取弹窗点击“信息正确，还需修改”，返回表单设置类型，不能直接发布：

```python
page.get_by_text('信息正确，还需修改', exact=True).click()
```

2026-10-13 已检查真实表单：

| 请求类型 | 页面可见选项 | 实际字段 |
| --- | --- | --- |
| 全文 `fulltext` | 只需要正文 | `input[name="Assist[suppl]"][value="0"]` |
| 支持材料 `supplementary` | 仅需补充材料 | `input[name="Assist[suppl]"][value="1"]` |

原生 radio 被 layui 隐藏，用户点击的是后面的 `.layui-form-radio`。点击可见控件，不强制点击隐藏 input，也不通过 JavaScript 改值跳过表单事件。

```python
label = '仅需补充材料' if material_type == 'supplementary' else '只需要正文'
option = page.locator('.layui-form-radio').filter(has_text=label)
if not option.is_visible():
    page.get_by_text('高级选项', exact=True).click()
option.click()
expected = '1' if material_type == 'supplementary' else '0'
selected = page.locator('input[name="Assist[suppl]"]:checked').input_value()
assert selected == expected, 'Material selection was not applied; do not submit'
```

仅在支持材料模式填写对应备注；具体文件范围来自用户，官方附件清单来自该论文官方页面。保持原始论文标题、DOI，不把“仅需补充材料”加到论文标题中。

```python
if material_type == 'supplementary':
    remark = '仅需该论文的支持材料（Supplementary/Supporting Information），不需要正文。'
    if requested_materials:
        remark += '指定文件：' + '；'.join(requested_materials)
    page.locator('#Assist-remark').fill(remark)
# 核对 DOI、标题、当前类型、备注、积分预算；写入对应类型的 submitting 记录。
# 确认上述条件后才执行 page.locator('#form-submit-btn').click()。
```

成功弹窗显示“求助发布成功”和“查看求助详情”。点击后立即记录 `page.url`，只用现场观察到的 ID。首次进入可能弹出“已经有人上传了文件”，先关闭该提示。

支持材料发布后还要检查求助详情的“求助补充材料”或同义标记以及备注。若与目标类型不符，停止继续下载/采纳并报告，不再创建另一个猜测正确的请求。

## 新页面与网页保存

附件通常是 `target="_blank"` 的链接，href 为 `/assist/download?id=…`。支持材料可包含多个文件，按页面观察到的文件名/链接逐个下载，不按 `.pdf` 后缀过滤。先监听原页和新页的 download 事件：

```python
downloads = []
page.on('download', lambda d: downloads.append(d))
ctx.on('page', lambda p: p.on('download', lambda d: downloads.append(d)))
# observed_filename 为页面上实际看到的附件名称。
page.get_by_role('link', name=observed_filename, exact=True).click()
```

检查 `ctx.pages` 找到下载页。页面自动下载，带进度显示；不要重复点击附件或线路。分段等待，每段短于一分钟，以处理浏览器事件并汇报。下载事件来自网页完整接收后的 blob，Playwright `save_as` 保存最终文件。多个附件逐个处理，每次记录新增的 download 事件，不能把上一个文件误记为下一个。

实测普通线路曾约 20 KB/s，当前账户积分高于当时的 500 分门槛，使用高速通道免积分。后续必须重新读取规则，不能硬编码门槛。

- 主高速按钮：`#download-highspeed-direct`；慢速提示按钮：`#download-switch-vip`。
- 点击后先核对“高速通道提示”里的规则，再点击“确认使用高速通道”。不勾选“一个月内不再提醒”，避免改长期偏好。
- 页面 100% 不代表本地保存成功；须有 download 事件且 `save_as` 成功。
- 已完成接收但没有 download 事件时，可点击网页“手动保存文件”一次。

```python
# 多个事件时选择本次目标附件；staging_path 是新的唯一临时路径，保留实际格式。
download = downloads[-1]
if download.failure() is not None:
    raise RuntimeError('Browser download failed; inspect current page')
download.save_as(str(staging_path))
```

全文通过 `verify_pdf.py` 和首页检查后归档。支持材料按 SKILL.md 的专项规则逐件核验，不要求所有文件都是 PDF 或都含 DOI；放入 `<safe-doi>__supplementary/`，在对应 JSON 的 `files[]` 记录文件清单。只拿到普通正文不能完成支持材料求助。全部所需文件已核验才更新为 `downloaded_pending_acceptance`；缺项记为 `downloaded_partial`，未确认归属/覆盖范围记为 `downloaded_unverified`。验证通过但采纳不在授权范围时记为 `downloaded`。

## 核验后的采纳

```python
page.get_by_role('button', name='采纳文件').click()
# 查看弹窗，确认是当前目标论文；留言不填。
page.locator('.layui-layer:visible').get_by_text('确定', exact=True).click()
```

第二个弹窗显示“操作成功，感谢使用科研通”，再次点击该弹窗“确定”，页面才刷新。旧 DOM 仍显示“待确认”时不能重复采纳。重新读取页面应显示“已完结”和“已采纳”；结果不明时通过详情或“我的求助”核实。

## 实测样本

全文样本：DOI `10.1126/science.ael0508`，最终 PDF 21 页、9,604,260 字节，正常求助、下载和采纳流程已完成。支持材料分支已实测点击可见控件并读取 `Assist[suppl]` 从 0 切换到 1、再切回 0，表单没有提交。新增功能未发布真实支持材料求助，不能声称该分支已完成端到端实测。维护者可用已有的合法本地全文样本进行离线核验，不要只为测试重复发布请求。此流程由 Codex 查看页面并执行，并非无人值守下载服务。
