#!/usr/bin/env bash
# Downloads the static brand fonts once into a per-user cache (fill_template.py copies them into each draft).
# Usage: fetch_fonts.sh [DEST]
# Satoshi: Indian Type Foundry Free Font License (Fontshare). Not bundled; fetched from the official source.
# Inter: SIL Open Font License 1.1 (rsms/inter). Fetched from the official GitHub release.
# Static weights only. Variable fonts print as Type 3 in Chrome and break text extraction.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# Default: a per-user cache outside the skill folder, so the fonts are never committed or shared with the skill.
DEST="${1:-${VP_FONT_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/vp-whitepaper-fonts}}"
mkdir -p "$DEST"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
need() { [ -s "$DEST/$1" ]; }
if ! need Satoshi-Bold.ttf || ! need Satoshi-Black.ttf; then
  curl -fsSL --retry 2 --max-time 180 -o "$TMP/satoshi.zip" "https://api.fontshare.com/v2/fonts/download/satoshi"
  unzip -q -o -j "$TMP/satoshi.zip" "*/WEB/fonts/Satoshi-Bold.ttf" "*/WEB/fonts/Satoshi-Black.ttf" "*/License/FFL.txt" -d "$TMP/s"
  cp "$TMP/s/Satoshi-Bold.ttf" "$TMP/s/Satoshi-Black.ttf" "$DEST/"
  cp "$TMP/s/FFL.txt" "$DEST/Satoshi-LICENSE-FFL.txt"
fi
if ! need Inter-Regular.ttf || ! need Inter-Medium.ttf; then
  curl -fsSL --retry 2 --max-time 180 -o "$TMP/inter.zip" "https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip"
  unzip -q -o -j "$TMP/inter.zip" "extras/ttf/Inter-Regular.ttf" "extras/ttf/Inter-Medium.ttf" "LICENSE.txt" -d "$TMP/i"
  cp "$TMP/i/Inter-Regular.ttf" "$TMP/i/Inter-Medium.ttf" "$DEST/"
  cp "$TMP/i/LICENSE.txt" "$DEST/Inter-LICENSE-OFL.txt"
fi
for f in Satoshi-Bold.ttf Satoshi-Black.ttf Inter-Regular.ttf Inter-Medium.ttf; do [ -s "$DEST/$f" ] || { echo "missing $f after download: stop; never substitute the variable font"; exit 1; }; done
ls -1 "$DEST"
