#!/usr/bin/env bash
# 用法: scaffold.sh <project_dir>
#
# 确定性铺「松耦合三侧」骨架：根 CLAUDE.md（指路）+ mgmt/（管理侧）+ analysis/（分析侧，主线）
# + explore/（探索侧，不进主线）+ .claude/agents/{mgr,analyst,explorer,reviewer}。
# 背景/数据检索与 PROJECT/RESOURCES/根CLAUDE 回填由 skill 负责（见 SKILL.md 步骤 2/3/5）。
# 无 --upgrade 模式：已存在任一侧即拒绝，不覆盖。
set -euo pipefail

PROJ_DIR="${1:?用法: scaffold.sh <project_dir>}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TPL_DIR="$SCRIPT_DIR/../templates"

[ -d "$PROJ_DIR" ] || { echo "ERROR: 项目目录不存在: $PROJ_DIR" >&2; exit 1; }
[ -w "$PROJ_DIR" ] || { echo "ERROR: 项目目录不可写: $PROJ_DIR" >&2; exit 1; }
PROJ_DIR="$(cd "$PROJ_DIR" && pwd)"   # 绝对化 = 规范根，写进 CLAUDE.md 与 agent prompt

SIDES=(mgmt analysis explore)
AGENTS=(mgr analyst explorer reviewer)

# --- 守卫：不覆盖 --------------------------------------------------------------
for d in "${SIDES[@]}"; do
  [ -e "$PROJ_DIR/$d" ] && { echo "ERROR: 已存在，拒绝覆盖: $PROJ_DIR/$d" >&2; exit 2; }
done
[ -s "$PROJ_DIR/CLAUDE.md" ] && { echo "ERROR: 根 CLAUDE.md 已存在且非空，拒绝覆盖: $PROJ_DIR/CLAUDE.md" >&2; exit 2; }
for a in "${AGENTS[@]}"; do
  [ -s "$PROJ_DIR/.claude/agents/$a.md" ] && { echo "ERROR: 已存在 agent，拒绝覆盖: .claude/agents/$a.md" >&2; exit 2; }
done

# --- 铺 -----------------------------------------------------------------------
# 根：指路契约 + AGENTS 软链 + .gitignore（不覆盖已有）
cp "$TPL_DIR/root_CLAUDE.md" "$PROJ_DIR/CLAUDE.md"
[ -e "$PROJ_DIR/AGENTS.md" ] || ln -s CLAUDE.md "$PROJ_DIR/AGENTS.md"
[ -e "$PROJ_DIR/.gitignore" ] || cp "$TPL_DIR/root_gitignore" "$PROJ_DIR/.gitignore"

# 三侧整目录铺过去
for side in "${SIDES[@]}"; do
  cp -r "$TPL_DIR/$side" "$PROJ_DIR/$side"
done

# agents
mkdir -p "$PROJ_DIR/.claude/agents"
for a in "${AGENTS[@]}"; do
  cp "$TPL_DIR/agents/$a.md" "$PROJ_DIR/.claude/agents/$a.md"
done

# 规范根占位一次性填掉（根契约 / 三侧契约 / 四个 agent）
while IFS= read -r f; do
  sed -i "s#<CANONICAL_ROOT>#$PROJ_DIR#g" "$f"
done < <(grep -rl '<CANONICAL_ROOT>' "$PROJ_DIR/CLAUDE.md" "${SIDES[@]/#/$PROJ_DIR/}" "$PROJ_DIR/.claude/agents" || true)

# git：没有 repo 就 init；不 commit（首个 commit 留给回填之后，见 SKILL.md 步骤 7）
GIT_NOTE="已有 git repo，未动"
if [ ! -d "$PROJ_DIR/.git" ]; then
  git -C "$PROJ_DIR" init -q && GIT_NOTE="已 git init（尚未 commit）"
fi

# --- 汇报 ---------------------------------------------------------------------
echo "已生成三侧骨架于: $PROJ_DIR"
{
  echo "CLAUDE.md"; echo "AGENTS.md -> CLAUDE.md"; echo ".gitignore"
  find "$PROJ_DIR/.claude" "${SIDES[@]/#/$PROJ_DIR/}" \( -type f -o -type l \) | sed "s#^$PROJ_DIR/##"
} | sort | sed 's/^/  /'
echo "git: $GIT_NOTE"
echo "已装 subagent: ${AGENTS[*]}（在本项目内 /agents 可见）"
echo "下一步（由 skill 完成）: 回填 mgmt/PROJECT.md（背景）、mgmt/RESOURCES.md（数据）、根 CLAUDE.md（项目名/一句话背景），然后首个 commit。"
