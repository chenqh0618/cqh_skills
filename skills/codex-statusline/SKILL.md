---
name: codex-statusline
description: Configure and install the native Codex CLI TUI footer status line through config.toml, with presets and selectable fields for model, reasoning, context, rate limits, tokens, Git, directory, session, task progress, and Fast mode. Use when the user asks to create, customize, simplify, hide, reset, or troubleshoot a Codex status line/status bar/footer, including requests containing “状态栏”, “statusline”, or “status bar”.
---

# Codex Status Line

Configure Codex's native TUI footer by editing `[tui].status_line`. Do not reuse Claude Code's external-command `statusLine` mechanism: Codex renders a fixed set of native items itself.

## Locate the bundled files

1. Resolve the directory containing this `SKILL.md` as `SKILL_DIR`.
2. Use `${SKILL_DIR}/scripts/configure.py` for previews and writes.
3. Read `${SKILL_DIR}/references/items.md` only when field-level descriptions, aliases, or compatibility notes are needed.

## Choose a layout

Use an explicit user selection when provided. Otherwise use `balanced` and state the choice without blocking on a question.

| Preset | Purpose |
|---|---|
| `balanced` | Model/reasoning, remaining context, limits, project folder name, and Git branch |
| `essentials` | Model/reasoning, remaining context, project folder name, and Git branch |
| `everything` | Every useful native field except the absolute-path `current-dir` field |
| `usage` | Context, rate limits, and token consumption |
| `session` | Project folder name, thread, run state, task progress, and Git branch |

Map natural-language requests to canonical IDs or aliases before invoking the script. Examples: `model,context,git,dir`, `reasoning,limits,tokens`, or canonical IDs such as `thread-title`. Map `dir`, `cwd`, `path`, and `folder` to `project-name`, which renders only the project folder name. Use canonical `current-dir` only when the user explicitly requests an absolute/current path. Use `--elements none` to hide the footer and `--reset` to restore Codex's default layout.

## Preview and install

Always preview first:

```bash
python3 "${SKILL_DIR}/scripts/configure.py" --preset balanced
python3 "${SKILL_DIR}/scripts/configure.py" --elements model,context,git,dir
```

If the user asked to configure, install, or change the status line, install the previewed layout:

```bash
python3 "${SKILL_DIR}/scripts/configure.py" --preset balanced --install
```

The script preserves unrelated TOML, validates the result, writes atomically, and saves the previous file as `config.toml.codex-statusline.bak`. Respect `CODEX_HOME`; use `--config PATH` only when the user names a different config.

For advice, inspection, or preview-only requests, do not pass `--install`.

## Validate

After installation:

1. Run `codex --strict-config doctor --summary --ascii --no-color` when the installed Codex supports it.
2. Require the Configuration/config check to pass; report unrelated auth or network diagnostics separately rather than treating them as a status-line failure.
3. Tell the user to start a new Codex TUI session. An already-running TUI may retain its loaded configuration.

If the installed Codex rejects a documented field, use `/statusline` in that Codex version to discover its available items and update the selection. Do not invent field IDs. `/theme` changes syntax highlighting and is not a separate status-line color theme.

## Utilities

List presets, aliases, and canonical fields:

```bash
python3 "${SKILL_DIR}/scripts/configure.py" --list
```
