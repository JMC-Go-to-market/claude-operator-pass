#!/usr/bin/env bash
# install.sh — Install claude-operator-pass skill ecosystem
# Usage: curl -fsSL https://raw.githubusercontent.com/JMC-Go-to-market/claude-operator-pass/main/install.sh | bash

set -euo pipefail

REPO_URL="https://github.com/JMC-Go-to-market/claude-operator-pass"
SKILLS_DIR="${HOME}/.claude/skills"

if ! command -v git >/dev/null 2>&1; then
    echo "ERROR: git is required but not installed." >&2
    exit 1
fi

mkdir -p "$SKILLS_DIR"
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

echo "Installing claude-operator-pass..."
git clone --depth 1 "$REPO_URL" "$TEMP_DIR" >/dev/null 2>&1

safe_skill_name() {
  # C locale: in UTF-8, a-z can include A-Z, and this check would then accept BadName.
  (
    LC_ALL=C
    case "$1" in
      ""|-*|*-|*--*|*[!a-z0-9-]*) exit 1 ;;
    esac
  )
}

# Skip .git. Any other symlink is refused before a destination is deleted.
if find "$TEMP_DIR" -path "$TEMP_DIR/.git" -prune -o -type l -print | grep -q .; then
  echo "ERROR: the pack contains a symlink. Not installing." >&2
  exit 1
fi

install_one() {
  local from="$1" name="$2"
  local root target parent
  root="$(cd "$SKILLS_DIR" && pwd -P)"
  target="$root/$name"
  case "$target" in
    "$root"/*) ;;
    *)
      echo "ERROR: refusing to install outside $root" >&2
      exit 1
      ;;
  esac
  parent="$(dirname "$target")"
  if [[ "$parent" != "$root" ]]; then
    echo "ERROR: refusing to install outside $root" >&2
    exit 1
  fi
  rm -rf -- "$target"
  cp -R "$from" "$target"
  echo "  + $name"
}

name_list=""
if [[ -d "$TEMP_DIR/operator-pass" ]]; then
  name_list="operator-pass"
fi
for skill_dir in "$TEMP_DIR/skills"/operator-pass-*; do
  if [[ -d "$skill_dir" ]]; then
    name_list="${name_list}"$'\n'"$(basename "$skill_dir")"
  fi
done
while IFS= read -r name; do
  [[ -n "$name" ]] || continue
  if ! safe_skill_name "$name"; then
    echo "ERROR: skill name is not lowercase letters, digits, and hyphens: $name" >&2
    exit 1
  fi
done <<< "$name_list"
if [[ -d "$TEMP_DIR/operator-pass" ]]; then
  install_one "$TEMP_DIR/operator-pass" "operator-pass"
fi
for skill_dir in "$TEMP_DIR/skills"/operator-pass-*; do
  if [[ -d "$skill_dir" ]]; then
    install_one "$skill_dir" "$(basename "$skill_dir")"
  fi
done

echo ""
echo "Done. Restart Claude Code to pick up the new skill."
echo ""
echo "Setup:"
echo "  export OPERATOR_PASS_API_KEY=\"jmc_live_...\""
echo "  Get a key at https://jaymountconsulting.com/operator-pass"
echo ""
echo "Try it:"
echo "  > Lint this cold email: <paste>"
echo "  > What tools are available?"
echo ""
echo "Source:  $REPO_URL"
