#!/usr/bin/env bash
# Render a filled white paper to PDF with headless Chrome, then run the QA checks. Fails closed.
# Usage: render_and_qa.sh WORK_DIR "Output File Name.pdf"
#   WORK_DIR holds whitepaper.html and assets/ (from fill_template.py) and assets/fonts/ (from fetch_fonts.sh).
# Renders into a fresh WORK_DIR/render-<timestamp>/ folder: PDF, page-N.png (110 dpi), qa-report.txt.
# Exit 0 only when the render succeeded and every blocking QA check passed. Then the folder holds a
# AUTO_QA_PASS marker and the PDF under its final name ("INTERNAL DRAFT - " prefix while the draft banner
# is on). On a QA failure the PDF is FAILED-QA.pdf. AUTO_QA_PASS covers automated checks only; the agent
# still does the visual, fact and buyer checks (SKILL.md step 6) before handing over.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="$(cd "${1:?WORK_DIR required}" && pwd)"
NAME="${2:-whitepaper.pdf}"
case "$NAME" in */*|.*|"") echo "bad output name: $NAME"; exit 2;; esac
case "$NAME" in *.pdf) ;; *) NAME="$NAME.pdf";; esac
if [ -z "${CHROME:-}" ]; then
  for c in google-chrome google-chrome-stable chromium chromium-browser \
           "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
           "/Applications/Chromium.app/Contents/MacOS/Chromium"; do
    if command -v "$c" >/dev/null 2>&1 || [ -x "$c" ]; then CHROME="$c"; break; fi
  done
fi
[ -n "${CHROME:-}" ] || { echo "Chrome or Chromium not found; set CHROME=/path/to/chrome"; exit 2; }
for t in pdffonts pdftotext pdftoppm pdfinfo python3; do
  command -v "$t" >/dev/null || { echo "missing $t (Linux: apt install poppler-utils; macOS: brew install poppler)"; exit 2; }
done
for f in Satoshi-Bold.ttf Satoshi-Black.ttf Inter-Regular.ttf Inter-Medium.ttf; do
  [ -s "$WORK/assets/fonts/$f" ] || { echo "missing font $f: run scripts/fetch_fonts.sh \"$WORK/assets/fonts\""; exit 2; }
done
[ -s "$WORK/whitepaper.html" ] || { echo "missing $WORK/whitepaper.html"; exit 2; }
[ -s "$WORK/qa-context.json" ] || { echo "missing qa-context.json: fill with scripts/fill_template.py"; exit 2; }
OUT="$WORK/render-$(date +%Y%m%d-%H%M%S)"
mkdir "$OUT"
PDF="$OUT/UNVERIFIED.pdf"
URL="$(python3 -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve().as_uri())' "$WORK/whitepaper.html")"
# New headless mode uses its own throwaway profile by default. Do not pass --user-data-dir: a fresh
# explicit profile hangs on some Linux containers, and the user's own profile must never be used.
# Chrome's temporary profile goes in a private short-path temp folder (socket paths are length-limited),
# deleted when the script exits, even after a timeout kill.
CTMP="$(mktemp -d "${TMPDIR:-/tmp}/vpwp.XXXXXX")"; chmod 700 "$CTMP"
trap 'rm -rf "$CTMP" "$OUT/dom.html"' EXIT
export TMPDIR="$CTMP"
FLAGS=(--headless=new --disable-gpu --hide-scrollbars --allow-file-access-from-files
       --run-all-compositor-stages-before-draw --virtual-time-budget=8000 --disable-extensions --no-first-run)
# Portable timeout (macOS has no `timeout`): run_limited SECONDS cmd...
run_limited() { local s="$1"; shift; "$@" & local pid=$!
  ( i=0; while [ $i -lt "$s" ]; do sleep 1; kill -0 "$pid" 2>/dev/null || exit 0; i=$((i+1)); done
    kill "$pid" 2>/dev/null; sleep 5; kill -9 "$pid" 2>/dev/null ) & local w=$!
  local rc=0; wait "$pid" || rc=$?; kill "$w" 2>/dev/null; wait "$w" 2>/dev/null || true; return $rc; }
# Chrome's sandbox cannot start as root (containers); only then drop it.
[ "$(id -u)" = "0" ] && FLAGS+=(--no-sandbox)
run_limited 90 "$CHROME" "${FLAGS[@]}" --no-pdf-header-footer --print-to-pdf="$PDF" "$URL" >"$OUT/chrome.log" 2>&1 || { echo "Chrome print failed (see $OUT/chrome.log)"; exit 2; }
[ -s "$PDF" ] || { echo "render failed: no PDF"; exit 2; }
run_limited 90 "$CHROME" "${FLAGS[@]}" --window-size=816,1056 --dump-dom "$URL" > "$OUT/dom.html" 2>>"$OUT/chrome.log" || { echo "DOM dump failed"; exit 2; }
pdftoppm -r 110 -png "$PDF" "$OUT/page"
PAGES="$(pdfinfo "$PDF" | awk '/^Pages:/{print $2}')"
PNGS="$(ls "$OUT"/page-*.png 2>/dev/null | wc -l | tr -d ' ')"
[ "$PAGES" = "$PNGS" ] || { echo "preview count $PNGS != pages $PAGES"; exit 2; }
set +e
python3 "$HERE/qa_checks.py" "$WORK/whitepaper.html" "$OUT/dom.html" "$PDF" "$WORK/qa-context.json" "$HERE/../template/whitepaper.html" > "$OUT/qa-report.txt" 2>&1
RC=$?
set -e
cat "$OUT/qa-report.txt"
rm -f "$OUT/dom.html"
if [ "$RC" = "0" ]; then
  if python3 -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1])).get("draft", True) else 1)' "$WORK/qa-context.json"; then
    NAME="INTERNAL DRAFT - $NAME"
  fi
  mv "$PDF" "$OUT/$NAME"; touch "$OUT/AUTO_QA_PASS"
  echo "PASS: $OUT/$NAME"
else
  mv "$PDF" "$OUT/FAILED-QA.pdf"
  [ "$RC" = "1" ] || echo "QA script error (exit $RC): see qa-report.txt"
fi
echo "artifacts: $OUT"
exit "$RC"
