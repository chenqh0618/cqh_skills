#!/usr/bin/env bash
# 用法: abstracts.sh [analysis|explore]
#
# 扫各分析/探索单元 SUMMARY.md 顶部 frontmatter 的 abstract 与 upstream，一次读完全项目的
# 「有哪些单元、各自做了什么、架在谁身上」，据此决定要展开谁。无参 = 两侧都扫。
# 没写 frontmatter 的单元会被点名（兼作 lint）。纯 awk，无外部依赖。
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

case "${1:-}" in
  "")               SIDES=(analysis explore) ;;
  analysis|explore) SIDES=("$1") ;;
  -h|--help)        sed -n '2,6p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
  *) echo "用法: abstracts.sh [analysis|explore]" >&2; exit 1 ;;
esac

for side in "${SIDES[@]}"; do
  [ -d "$ROOT/$side" ] || continue
  echo "== $side/ =="
  found=0
  for d in "$ROOT/$side"/*/; do
    [ -d "$d" ] || continue
    unit="$(basename "$d")"
    case "$unit" in _*) continue ;; esac   # 跳过 _templates/ 之类
    found=1

    if [ ! -f "$d/SUMMARY.md" ]; then
      printf '%s   ⚠ 无 SUMMARY.md\n' "$unit"
      continue
    fi

    awk -v unit="$unit" '
      NR==1 {
        if ($0 !~ /^---[[:space:]]*$/) { print unit "   ⚠ 无 frontmatter"; bad=1; exit }
        state=1; next
      }
      state==1 && /^---[[:space:]]*$/ { state=2; exit }
      state==1 {
        line=$0
        if (line ~ /^abstract:/) { sub(/^abstract:[[:space:]]*/, "", line); ab=line; key="abstract"; next }
        if (line ~ /^upstream:/) { sub(/^upstream:[[:space:]]*/, "", line); up=line; key="upstream"; next }
        if (line ~ /^[A-Za-z_][A-Za-z0-9_-]*:/) { key="other"; next }
        sub(/^[[:space:]]+/, "", line)                     # 折行续写
        if      (key=="abstract") ab = ab (ab=="" ? "" : " ") line
        else if (key=="upstream") up = up (up=="" ? "" : " ") line
      }
      END {
        if (bad) exit
        if (state != 2) { print unit "   ⚠ frontmatter 未闭合"; exit }
        print unit (up=="" ? "   ⚠ 无 upstream 字段" : "   ← upstream: " up)
        print "  " (ab=="" ? "⚠ 无 abstract 字段" : ab)
      }
    ' "$d/SUMMARY.md"
  done
  [ "$found" = 1 ] || echo "（空）"
  echo
done
