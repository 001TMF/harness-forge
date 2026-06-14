#!/usr/bin/env bash
# Install the meta-harness skill into Claude Code.
#
#   curl -fsSL https://raw.githubusercontent.com/001TMF/harness-forge/main/install.sh | bash
#
# Flags:
#   --project   install into ./.claude/skills (this repo only) instead of ~/.claude/skills
# Env:
#   CLAUDE_SKILLS_DIR   override the destination skills directory
set -euo pipefail

SKILL="meta-harness"               # installed skill folder name
SRC_PATH="skills/meta-harness"     # location within the harness-forge repo
REPO="https://github.com/001TMF/harness-forge.git"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
[ "${1:-}" = "--project" ] && DEST=".claude/skills"

mkdir -p "$DEST"

if [ -f "$SRC_PATH/SKILL.md" ]; then
  # running from a local clone — copy directly
  SRC="$SRC_PATH"
else
  # piped via curl — fetch the repo into a temp dir
  command -v git >/dev/null 2>&1 || { echo "error: git is required" >&2; exit 1; }
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  echo "Fetching harness-forge..."
  git clone --depth 1 --quiet "$REPO" "$TMP"
  SRC="$TMP/$SRC_PATH"
fi

rm -rf "${DEST:?}/$SKILL"
cp -r "$SRC" "$DEST/$SKILL"

echo "✓ Installed '$SKILL' → $DEST/$SKILL"
echo "  Open Claude Code — the meta-harness skill is now available (it triggers"
echo "  automatically on harness/scaffold optimization tasks, or invoke it by name)."
