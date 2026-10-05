# Codex 原生状态栏字段

以下 ID 经 Codex CLI 0.144.4 的本机二进制与官方配置说明核对。Codex 会自己渲染字段、颜色和可用性；配置只决定字段及其顺序。

## 配置语义

```toml
[tui]
status_line = ["model-with-reasoning", "context-remaining", "project-name"]
```

- 未设置 `status_line`：使用 Codex 默认值 `model-with-reasoning, context-remaining, current-dir`。
- 设置 `status_line = []`：隐藏状态栏。
- 在 TUI 输入 `/statusline`：用当前 Codex 版本的交互选择器配置字段。

## 字段

| ID | 内容 |
|---|---|
| `project-name` | 项目文件夹名；默认用于路径位置，不显示绝对路径 |
| `current-dir` | 当前工作目录；可能显示绝对路径，只在用户明确要求时选用 |
| `run-state` | 当前运行状态 |
| `thread-title` | 当前会话标题 |
| `git-branch` | Git 分支 |
| `context-remaining` | 剩余上下文比例 |
| `context-used` | 已用上下文比例 |
| `five-hour-limit` | 5 小时用量限制 |
| `weekly-limit` | 每周用量限制 |
| `codex-version` | Codex CLI 版本 |
| `used-tokens` | 当前会话已用 token |
| `total-input-tokens` | 累计输入 token |
| `total-output-tokens` | 累计输出 token |
| `thread-id` | 会话 ID |
| `fast-mode` | Fast 模式状态 |
| `model-with-reasoning` | 模型和推理强度 |
| `reasoning` | 推理强度 |
| `task-progress` | 任务进度 |

某些字段在数据不可用时可能不显示，例如非 Git 目录中的 `git-branch`，或账户不提供对应周期时的用量限制。

## 脚本别名

常用别名：`model`、`context`、`git`、`branch`、`dir`、`cwd`、`path`、`folder`、`effort`、`reasoning-effort`、`limits`、`tokens`、`project`、`thread`、`session-id`、`task`、`progress`、`fast`、`version`。

`dir`、`cwd`、`path` 和 `folder` 都展开为 `project-name`，从而只显示文件夹名。若确实需要当前目录绝对路径，须显式使用规范字段 `current-dir`。`limits` 展开为 `five-hour-limit,weekly-limit`。脚本去重并保留首次出现的顺序。

## 兼容性

状态栏字段可能随 Codex 版本变化。遇到“不支持的 ID”时，以该版本的 `/statusline` 选择器为准。不要改用 Claude Code 的 `~/.claude/settings.json`、`statusLine.command` 或 stdin JSON 脚本；这些不是 Codex CLI 的状态栏接口。
