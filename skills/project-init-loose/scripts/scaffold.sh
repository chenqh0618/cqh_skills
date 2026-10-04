#!/usr/bin/env bash
# Usage: scaffold.sh <existing-project-directory>
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
exec python3 - "$SCRIPT_DIR" "$@" <<'PY'
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

def require(ok, message):
    if not ok:
        raise ValueError(message)

def exists(path):
    return path.exists() or path.is_symlink()

try:
    require(sys.version_info >= (3, 11), "Python 3.11+ is required")
    parser = argparse.ArgumentParser(description="Initialize a project; optional decisions are recorded, not executed.")
    parser.add_argument("project")
    parser.add_argument("--domain")
    parser.add_argument("--project-class", choices=["lightweight", "complex"])
    parser.add_argument("--env-mode", choices=["shared", "project"])
    parser.add_argument("--reason")
    parser.add_argument("--reference-root")
    options = parser.parse_args(sys.argv[2:])
    decisions = [options.domain, options.project_class, options.env_mode, options.reason]
    require(not any(decisions) or all(decisions),
            "Provide --domain, --project-class, --env-mode and --reason together, or omit all for an unclassified skeleton.")
    is_scrna = bool(options.domain and options.domain.lower() in {"scrna", "scrna-seq", "snrna", "snrna-seq"})
    reference_root = options.reference_root
    if is_scrna and not reference_root:
        reference_root = "/public/data/cqh_data/proj_sync/tools_db/scRNA_v2"
    if reference_root:
        require(bool(options.domain), "--reference-root requires explicit project decisions")
        require(Path(reference_root).is_absolute(), "Reference root must be absolute")
    def md_value(value):
        return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")
    scripts = Path(sys.argv[1]).resolve()
    templates = scripts.parent / "templates"
    project = Path(options.project).resolve()
    require(project.is_dir() and os.access(project, os.W_OK), f"Not a writable project directory: {project}")
    require("\n" not in str(project) and "\r" not in str(project) and "`" not in str(project),
            "Project path cannot contain newlines or Markdown backticks")
    require(shutil.which("git"), "git is required")
    roots = ["CLAUDE.md", "AGENTS.md", "mgmt", "analysis", "explore", "_archived", ".project", "TASKS.md"]
    roles = ["mgr", "analyst", "explorer", "reviewer"]
    owned = roots + [f".claude/agents/{name}.md" for name in roles] + [f".codex/agents/{name}.toml" for name in roles]
    conflicts = [name for name in owned if exists(project / name)]
    require(not conflicts, f"Managed paths already exist; use MIGRATION.md: {', '.join(conflicts)}")
    for name in [".claude", ".claude/agents", ".codex", ".codex/agents"]:
        path = project / name
        require(not exists(path) or path.is_dir() and not path.is_symlink(), f"Invalid or linked parent: {path}")
        require(not path.exists() or os.access(path, os.W_OK), f"Parent is not writable: {path}")
    gitignore = project / ".gitignore"
    require(not gitignore.is_symlink() and (not gitignore.exists() or gitignore.is_file()),
            "Refusing invalid or linked .gitignore")
    repo = subprocess.run(["git", "-C", str(project), "rev-parse", "--show-toplevel"],
                          capture_output=True, text=True)
    require(repo.returncode == 0 or not exists(project / ".git"), "Existing Git metadata could not be read")

    # Build and validate a complete skeleton before publishing any managed path.
    with tempfile.TemporaryDirectory(prefix=".loose-init-", dir=project) as temporary:
        stage = Path(temporary)
        (stage / ".project").mkdir()
        for side in ["mgmt", "analysis", "explore"]:
            (stage / side).mkdir()
            source = templates / side
            for item in source.iterdir():
                if item.name == "_templates":  # old installed versions may leave empty directories
                    continue
                target = stage / side / item.name
                if item.is_dir():
                    shutil.copytree(item, target)
                else:
                    shutil.copy2(item, target)
            (stage / side / "AGENTS.md").symlink_to("CLAUDE.md")
        for name in ["analysis", "explore"]:
            (stage / "_archived" / name).mkdir(parents=True)
        shutil.copy2(templates / "archived/CLAUDE.md", stage / "_archived/CLAUDE.md")
        (stage / "_archived/AGENTS.md").symlink_to("CLAUDE.md")
        shutil.copy2(templates / "root_CLAUDE.md", stage / "CLAUDE.md")
        (stage / "AGENTS.md").symlink_to("CLAUDE.md")
        shutil.copytree(templates / "project", stage / ".project", dirs_exist_ok=True)
        shutil.copytree(templates / "unit", stage / ".project/templates")
        shutil.copy2(scripts / "task_tools.py", stage / ".project/tasks.py")
        shutil.copy2(scripts.parent / "MIGRATION.md", stage / ".project/MIGRATION.md")
        for name in roles:
            source = templates / "agents" / f"{name}.md"
            text = source.read_text()
            front, body = text.split("---", 2)[1:]
            fields = dict(line.split(": ", 1) for line in front.strip().splitlines())
            require(fields["name"] == name, f"Role name mismatch: {source}")
            claude = stage / ".claude/agents" / f"{name}.md"
            claude.parent.mkdir(parents=True, exist_ok=True)
            claude.write_text(text)
            codex = stage / ".codex/agents" / f"{name}.toml"
            codex.parent.mkdir(parents=True, exist_ok=True)
            role = {"name": name, "description": fields["description"], "developer_instructions": body.strip()}
            codex.write_text("\n".join(f"{key} = {json.dumps(value, ensure_ascii=False)}" for key, value in role.items()) + "\n")
        for path in stage.rglob("*"):
            if path.is_file() and not path.is_symlink() and path.suffix in {".md", ".toml"}:
                path.write_text(path.read_text().replace("<CANONICAL_ROOT>", str(project)))
        if options.domain:
            background = stage / "mgmt/PROJECT.md"
            with background.open("a") as stream:
                stream.write("\n## 初始化选择\n\n| 项目 | 选择 |\n|---|---|\n")
                for key, value in [("分析领域", options.domain), ("项目类别", options.project_class),
                                   ("选择依据", options.reason)]:
                    stream.write(f"| {key} | {md_value(value)} |\n")
            usage = stage / ".project/environments/USAGE.md"
            with usage.open("a") as stream:
                stream.write("\n## 初始化选择\n\n")
                stream.write(f"- 默认环境方式：`{options.env_mode}`\n")
                stream.write("- 部署状态：planned（仅记录选择；初始化未安装或验证分析环境）。\n")
                stream.write("- 实际 profile、解释器/prefix、软件版本与验证日期：使用前核对并填写。\n")
                if reference_root:
                    ref = Path(reference_root)
                    version_file = ref / "VERSION"
                    version = version_file.read_text().strip() if version_file.is_file() else "unknown"
                    stream.write(f"- 参考代码库：`{md_value(reference_root)}`；版本：`{md_value(version)}`。\n")
                    if is_scrna:
                        stream.write(f"- scRNA 初始化与调用接口：`{md_value(str(ref / 'docs/PROJECT_USAGE.md'))}`。\n")
                        stream.write("- 采用该库的 R 模板时使用 SCRNA_PARAMS 指定本单元配置；ORG 按实际物种填写，OUTPUT_ROOT 指向本单元 results，跨单元输入显式指定。\n")
                        stream.write("- 共享环境缺失或不满足依赖时先准备所选环境；不回退到旧 scRNA 环境。\n")
        subprocess.run([sys.executable, str(stage / ".project/tasks.py"), "index"], check=True, capture_output=True, text=True)
        (stage / ".project/tasks.lock").unlink()
        ignore = gitignore.read_text() if gitignore.exists() else (templates / "root_gitignore").read_text()
        rules = ["/.project/tasks.lock", "/.loose-init-*/", "/analysis/.new-task-*/", "/explore/.new-task-*/", ".loose-*"]
        missing = [rule for rule in rules if rule not in ignore.splitlines()]
        if missing:
            ignore = ignore.rstrip() + "\n\n# project-init-loose runtime files\n" + "\n".join(missing) + "\n"
        (stage / ".gitignore").write_text(ignore)
        if gitignore.exists():
            (stage / ".gitignore").chmod(gitignore.stat().st_mode & 0o777)
        if repo.returncode != 0:
            subprocess.run(["git", "-C", str(stage), "init", "-q"], check=True)
            owned.append(".git")
        # All destinations were checked before any write; never merge scientific task trees.
        published, parents = [], []
        try:
            for name in owned:
                target = project / name
                require(not exists(target), f"Destination appeared during initialization: {target}")
                missing_parents = []
                parent = target.parent
                while not parent.exists():
                    missing_parents.append(parent)
                    parent = parent.parent
                for parent in reversed(missing_parents):
                    parent.mkdir()
                    parents.append(parent)
                os.rename(stage / name, target)
                published.append(name)
            os.replace(stage / ".gitignore", gitignore)
        except Exception:
            for name in reversed(published):
                (stage / name).parent.mkdir(parents=True, exist_ok=True)
                os.rename(project / name, stage / name)
            for parent in reversed(parents):
                parent.rmdir()
            raise
    print(f"Initialized project-init-loose: {project}")
    print("Created mgmt/, analysis/, explore/, _archived/, .project/, TASKS.md and both agent adapters.")
    print("Next: fill project background and data facts. No scientific tasks or conclusions were created.")
    print("Git: existing repository preserved." if repo.returncode == 0 else "Git: initialized; no commit created.")
except (ValueError, OSError, subprocess.CalledProcessError) as error:
    print(f"ERROR: {error}", file=sys.stderr)
    sys.exit(2)
PY
