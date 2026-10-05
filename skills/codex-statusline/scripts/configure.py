#!/usr/bin/env python3
"""Preview or install Codex CLI's native TUI status-line configuration."""

from __future__ import annotations

import argparse
import difflib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
import tomllib


FIELD_INFO = {
    "project-name": "项目文件夹名（不显示绝对路径）",
    "current-dir": "当前工作目录（可能显示绝对路径，须显式选择）",
    "run-state": "当前运行状态",
    "thread-title": "当前会话标题",
    "git-branch": "Git 分支",
    "context-remaining": "剩余上下文比例",
    "context-used": "已用上下文比例",
    "five-hour-limit": "5 小时用量限制",
    "weekly-limit": "每周用量限制",
    "codex-version": "Codex CLI 版本",
    "used-tokens": "当前会话已用 token",
    "total-input-tokens": "累计输入 token",
    "total-output-tokens": "累计输出 token",
    "thread-id": "会话 ID",
    "fast-mode": "Fast 模式状态",
    "model-with-reasoning": "模型和推理强度",
    "reasoning": "推理强度",
    "task-progress": "任务进度",
}

PRESETS = {
    "balanced": (
        "model-with-reasoning",
        "context-remaining",
        "five-hour-limit",
        "weekly-limit",
        "project-name",
        "git-branch",
    ),
    "essentials": (
        "model-with-reasoning",
        "context-remaining",
        "project-name",
        "git-branch",
    ),
    "everything": tuple(field for field in FIELD_INFO if field != "current-dir"),
    "usage": (
        "model-with-reasoning",
        "context-remaining",
        "context-used",
        "five-hour-limit",
        "weekly-limit",
        "used-tokens",
        "total-input-tokens",
        "total-output-tokens",
    ),
    "session": (
        "project-name",
        "thread-title",
        "run-state",
        "task-progress",
        "git-branch",
    ),
}

ALIASES = {
    "model": ("model-with-reasoning",),
    "effort": ("reasoning",),
    "reasoning-effort": ("reasoning",),
    "context": ("context-remaining",),
    "remaining": ("context-remaining",),
    "used-context": ("context-used",),
    "limits": ("five-hour-limit", "weekly-limit"),
    "limit": ("five-hour-limit", "weekly-limit"),
    "tokens": ("used-tokens",),
    "input-tokens": ("total-input-tokens",),
    "output-tokens": ("total-output-tokens",),
    "git": ("git-branch",),
    "branch": ("git-branch",),
    "dir": ("project-name",),
    "cwd": ("project-name",),
    "path": ("project-name",),
    "folder": ("project-name",),
    "project": ("project-name",),
    "thread": ("thread-title",),
    "session": ("thread-title",),
    "session-id": ("thread-id",),
    "task": ("task-progress",),
    "progress": ("task-progress",),
    "fast": ("fast-mode",),
    "version": ("codex-version",),
}

TUI_SECTION_RE = re.compile(r"^\s*\[(?!\[)\s*tui\s*\]\s*(?:#.*)?$")
ANY_TABLE_RE = re.compile(r"^\s*\[\[?.*?\]\]?\s*(?:#.*)?$")
STATUS_RE = re.compile(r"^(\s*)status_line\s*=")
DOTTED_STATUS_RE = re.compile(r"^(\s*)tui\.status_line\s*=")
ROOT_TUI_DOTTED_RE = re.compile(r"^\s*tui\.[A-Za-z0-9_-]+\s*=")
ROOT_TUI_INLINE_RE = re.compile(r"^\s*tui\s*=")


class ConfigError(RuntimeError):
    """Raised when config.toml cannot be edited without risking other settings."""


def default_config_path() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    base = Path(codex_home).expanduser() if codex_home else Path.home() / ".codex"
    return base / "config.toml"


def resolve_elements(raw: str | None, preset: str | None) -> list[str]:
    if raw is None:
        return list(PRESETS[preset or "balanced"])

    normalized = raw.strip().lower()
    if normalized in {"", "none", "off", "hide", "hidden", "关闭", "隐藏"}:
        return []

    result: list[str] = []
    unknown: list[str] = []
    for token in re.split(r"[,，\s]+", normalized):
        if not token:
            continue
        token = token.replace("_", "-")
        expanded = ALIASES.get(token)
        if expanded is None:
            expanded = (token,) if token in FIELD_INFO else ()
        if not expanded:
            unknown.append(token)
            continue
        for field in expanded:
            if field not in result:
                result.append(field)

    if unknown:
        raise ConfigError(
            "未知状态栏字段: "
            + ", ".join(unknown)
            + "。运行 --list 查看可用字段。"
        )
    return result


def _line_ending(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def _assignment_end(lines: list[str], start: int) -> int:
    """Return the exclusive end of a scalar or bracketed TOML assignment."""
    rhs = lines[start].split("=", 1)[1]
    depth = 0
    saw_array = False
    quote: str | None = None
    escaped = False

    for index in range(start, len(lines)):
        fragment = rhs if index == start else lines[index]
        for char in fragment:
            if quote == '"':
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    quote = None
                continue
            if quote == "'":
                if char == "'":
                    quote = None
                continue
            if char == "#":
                break
            if char in {'"', "'"}:
                quote = char
            elif char == "[":
                saw_array = True
                depth += 1
            elif char == "]" and saw_array:
                depth -= 1
        if not saw_array or depth <= 0:
            return index + 1
    raise ConfigError("status_line 数组没有闭合的 ]。")


def _insert(lines: list[str], index: int, line: str, newline: str) -> None:
    if index > 0 and not lines[index - 1].endswith(("\n", "\r")):
        lines[index - 1] += newline
    lines[index:index] = [line + newline]


def _parse_toml(text: str, path: Path) -> dict:
    try:
        return tomllib.loads(text) if text.strip() else {}
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path} 不是有效 TOML，未修改: {exc}") from exc


def update_config(text: str, fields: list[str] | None, path: Path) -> str:
    """Return config text with status_line set, or removed when fields is None."""
    _parse_toml(text, path)
    newline = _line_ending(text)
    lines = text.splitlines(keepends=True)
    assignment = None if fields is None else f"status_line = {json.dumps(fields)}"

    first_table = next((i for i, line in enumerate(lines) if ANY_TABLE_RE.match(line)), len(lines))
    dotted_matches = [
        i for i, line in enumerate(lines[:first_table]) if DOTTED_STATUS_RE.match(line)
    ]
    if len(dotted_matches) > 1:
        raise ConfigError("检测到多个 tui.status_line 定义，未修改。")
    if dotted_matches:
        start = dotted_matches[0]
        end = _assignment_end(lines, start)
        if fields is None:
            del lines[start:end]
        else:
            indent = DOTTED_STATUS_RE.match(lines[start]).group(1)  # type: ignore[union-attr]
            lines[start:end] = [f"{indent}tui.{assignment}{newline}"]
        result = "".join(lines)
        _validate_result(result, fields, path)
        return result

    section_starts = [i for i, line in enumerate(lines) if TUI_SECTION_RE.match(line)]
    if len(section_starts) > 1:
        raise ConfigError("检测到多个 [tui] 表，未修改。")
    if section_starts:
        section_start = section_starts[0]
        section_end = next(
            (
                i
                for i in range(section_start + 1, len(lines))
                if ANY_TABLE_RE.match(lines[i])
            ),
            len(lines),
        )
        matches = [
            i
            for i in range(section_start + 1, section_end)
            if STATUS_RE.match(lines[i])
        ]
        if len(matches) > 1:
            raise ConfigError("检测到多个 [tui].status_line 定义，未修改。")
        if matches:
            start = matches[0]
            end = _assignment_end(lines, start)
            if fields is None:
                del lines[start:end]
            else:
                indent = STATUS_RE.match(lines[start]).group(1)  # type: ignore[union-attr]
                lines[start:end] = [f"{indent}{assignment}{newline}"]
        elif fields is not None:
            _insert(lines, section_end, assignment, newline)
        result = "".join(lines)
        _validate_result(result, fields, path)
        return result

    root_lines = lines[:first_table]
    if any(ROOT_TUI_INLINE_RE.match(line) for line in root_lines):
        raise ConfigError(
            "检测到内联 tui = {...}；为避免破坏其他设置，请先改为 [tui] 表或使用 /statusline。"
        )
    if fields is None:
        return text
    if any(ROOT_TUI_DOTTED_RE.match(line) for line in root_lines):
        dotted_assignment = f"tui.{assignment}"
        _insert(lines, first_table, dotted_assignment, newline)
        result = "".join(lines)
    else:
        result = text
        if result and not result.endswith(("\n", "\r")):
            result += newline
        if result and not result.endswith(newline * 2):
            result += newline
        result += f"[tui]{newline}{assignment}{newline}"
    _validate_result(result, fields, path)
    return result


def _validate_result(text: str, fields: list[str] | None, path: Path) -> None:
    parsed = _parse_toml(text, path)
    tui = parsed.get("tui", {})
    if not isinstance(tui, dict):
        raise ConfigError("tui 配置不是 TOML 表。")
    if fields is None:
        if "status_line" in tui:
            raise ConfigError("重置失败：status_line 仍存在。")
    elif tui.get("status_line") != fields:
        raise ConfigError("写入后的 status_line 与请求字段不一致。")


def _effective_write_path(path: Path) -> Path:
    path = path.expanduser()
    return path.resolve() if path.is_symlink() else path


def write_atomic(path: Path, text: str) -> Path | None:
    path = _effective_write_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    backup: Path | None = None
    mode = 0o600
    if path.exists():
        mode = stat.S_IMODE(path.stat().st_mode)
        backup = path.with_name(path.name + ".codex-statusline.bak")
        shutil.copy2(path, backup)

    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, mode)
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise
    return backup


def print_catalog() -> None:
    print("预设:")
    for name, fields in PRESETS.items():
        print(f"  {name:10} {','.join(fields)}")
    print("\n字段:")
    for field, description in FIELD_INFO.items():
        print(f"  {field:22} {description}")
    print("\n别名:")
    for alias, fields in ALIASES.items():
        print(f"  {alias:22} {','.join(fields)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="预览或安装 Codex CLI 原生 TUI 状态栏配置。"
    )
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--preset", choices=PRESETS, help="使用内置布局预设")
    choice.add_argument("--elements", help="逗号分隔的字段或别名；none 表示隐藏")
    choice.add_argument("--reset", action="store_true", help="删除自定义值，恢复 Codex 默认状态栏")
    parser.add_argument(
        "--config",
        type=Path,
        default=default_config_path(),
        help="config.toml 路径（默认遵循 CODEX_HOME）",
    )
    parser.add_argument("--install", action="store_true", help="写入配置；默认仅显示 diff")
    parser.add_argument("--list", action="store_true", help="列出预设、字段与别名")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.list:
        print_catalog()
        return 0

    try:
        fields = None if args.reset else resolve_elements(args.elements, args.preset)
        requested_path = args.config.expanduser()
        read_path = _effective_write_path(requested_path)
        original = read_path.read_text(encoding="utf-8") if read_path.exists() else ""
        updated = update_config(original, fields, read_path)
        if updated == original:
            print(f"无需修改: {requested_path}")
            return 0

        if not args.install:
            diff = difflib.unified_diff(
                original.splitlines(),
                updated.splitlines(),
                fromfile=str(requested_path),
                tofile=str(requested_path) + " (preview)",
                lineterm="",
            )
            print("\n".join(diff))
            print("\n仅预览；确认后加 --install 写入。")
            return 0

        backup = write_atomic(requested_path, updated)
        print(f"已写入: {requested_path}")
        if backup:
            print(f"备份: {backup}")
        if fields is None:
            print("状态栏: Codex 默认布局")
        elif fields:
            print("状态栏: " + ", ".join(fields))
        else:
            print("状态栏: 已隐藏")
        return 0
    except (ConfigError, OSError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
