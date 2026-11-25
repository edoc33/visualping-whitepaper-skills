#!/usr/bin/env python3
"""Fill template/whitepaper.html from values.json and sources.json into a fresh draft folder.

Usage: fill_template.py /abs/values.json /abs/sources.json /abs/NEW_DRAFT_DIR

The folder holding values.json must also hold fact-sheet.md and private-terms.txt (may be empty).

values.json
- Text placeholders: "KEY": "text". Every value is inserted as escaped text (no raw HTML).
- Optional blocks: every IF:KEY in the template needs "KEY": true or false. False removes the block,
  and its placeholders are then not required.
- Context keys (not printed, used by QA): "ACCOUNT_DOMAIN" (the account's own domain) and
  "REP_EMAIL" (also printed in the CTA).
sources.json
- "KEY": ["F12", "G-4"] for every text key that is printed. Every F# must be a row in fact-sheet.md and
  every G-# a row in references/claims-guardrails.md. "FIXTURE" is accepted only when VP_WP_TEST=1.
SHOW_DRAFT_BANNER false is refused while fact-sheet.md still has a "Needs rep confirmation" row.

Fails (exit 1, nothing written) on: relative paths, missing/empty values, non-boolean flags, unknown
keys, printed keys without valid sources, example domains that are not reserved (.example), an existing
OUT_DIR (always use a new draft folder).
Writes OUT_DIR/whitepaper.html, assets/ (fonts copied from the cache if present), qa-context.json and
claims-skeleton.md (one row per printed key, to complete in the fact sheet's claims log).
"""
import html, json, os, re, shutil, sys
from pathlib import Path

here = Path(__file__).resolve().parent
tpl_dir = here.parent / "template"
FONT_CACHE = Path(os.environ.get("VP_FONT_CACHE", Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "vp-whitepaper-fonts"))
TEST = os.environ.get("VP_WP_TEST") == "1"  # tests only: also requires a fictional .example ACCOUNT_DOMAIN
if len(sys.argv) != 4 or not all(os.path.isabs(a) for a in sys.argv[1:]):
    print("FAIL usage: fill_template.py /abs/values.json /abs/sources.json /abs/NEW_DRAFT_DIR"); sys.exit(1)
vpath = Path(sys.argv[1]); wdir = vpath.parent
values = json.loads(vpath.read_text(encoding="utf-8"))
sources = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
out = Path(sys.argv[3])
fs_path, pt_path = wdir / "fact-sheet.md", wdir / "private-terms.txt"
# A fact row can source printed text only if it is filled in, has a status other than "Do not use",
# and is not in the internal section (F40 to F49).
fact_rows = set()
if fs_path.exists():
    for l in fs_path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*(F(\d+))\s*\|(.*)\|\s*$", l)
        if not m or 40 <= int(m.group(2)) <= 49: continue
        cells = [c.strip() for c in m.group(3).split("|")]
        status = cells[-1] if cells else ""
        if status and not re.search(r"do not use", status, re.I) and all(cells[:1]): fact_rows.add(m.group(1))
g_rows = set(re.findall(r"^\|\s*(G-\d+)\s*\|", (here.parent / "references" / "claims-guardrails.md").read_text(encoding="utf-8"), re.M))
raw = (tpl_dir / "whitepaper.html").read_text(encoding="utf-8")
src = raw
errors = []
PH = re.compile(r"\{\{([A-Z0-9_]+)\}\}")

flags = sorted(set(re.findall(r"<!--IF:([A-Z0-9_]+)-->", src)))
for k in flags:
    v = values.get(k)
    if not isinstance(v, bool):
        errors.append(f"{k} must be true or false"); continue
    src = re.sub(r"<!--IF:%s-->(.*?)<!--ENDIF:%s-->" % (k, k), (lambda m: m.group(1)) if v else "", src, flags=re.S)

needed = set(PH.findall(src))
for k in sorted(needed):
    v = values.get(k)
    if not isinstance(v, str) or not v.strip():
        errors.append(f"missing value for {k}")
    s = sources.get(k)
    ok = lambda x: isinstance(x, str) and (x in fact_rows or x in g_rows or (TEST and x == "FIXTURE"))
    if not (isinstance(s, list) and s and all(ok(x) for x in s)):
        errors.append(f"no valid source ids for {k} in sources.json (F# must exist in fact-sheet.md, G-# in the guardrails)")
context = {"ACCOUNT_DOMAIN"}
allowed = needed | set(flags) | set(PH.findall(raw)) | context
unknown = sorted(set(values) - allowed)
if unknown: errors.append("unknown keys: " + ", ".join(unknown))
dom = values.get("ACCOUNT_DOMAIN", "")
if not re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", dom or ""):
    errors.append("ACCOUNT_DOMAIN must be a lowercase domain")
for k in ("EXAMPLE_URL", "MOCK_DOMAIN"):
    if k in needed and not re.match(r"^[a-z0-9.-]+\.example(/|$)", values.get(k, "")):
        errors.append(f"{k} must use a reserved .example domain")
SYNCED = re.compile(r"Mobile Documents|CloudStorage|Google ?Drive|Dropbox|OneDrive|iCloud", re.I)
if TEST and not str(values.get("ACCOUNT_DOMAIN", "")).endswith(".example"):
    errors.append("VP_WP_TEST=1 is only for the fictional fixture (.example ACCOUNT_DOMAIN)")
if out.resolve().parent != wdir.resolve():
    errors.append("the draft folder must be directly inside the folder that holds values.json")
if SYNCED.search(str(wdir.resolve())):
    errors.append("the working folder is inside a synced folder; use a private local folder")
if out.exists():
    errors.append(f"{out} exists: use a new draft folder per attempt")
if not TEST:
    if not fs_path.exists(): errors.append(f"missing {fs_path}")
    if not pt_path.exists(): errors.append(f"missing {pt_path} (list contact names, workspace and label names, hosts; may be empty)")
if values.get("SHOW_DRAFT_BANNER") is False and fs_path.exists():
    open_rows = [l for l in fs_path.read_text(encoding="utf-8").splitlines()
                 if l.startswith("|") and "Verdict (" not in l and re.search(r"needs rep confirmation", l, re.I)]
    if open_rows: errors.append(f"SHOW_DRAFT_BANNER is false but fact-sheet.md has {len(open_rows)} 'Needs rep confirmation' rows")
if errors:
    print("FAIL\n  " + "\n  ".join(errors)); sys.exit(1)

res = PH.sub(lambda m: html.escape(values[m.group(1)], quote=False), src)
if re.search(r"<!--(?:END)?IF:", res):
    print("FAIL IF markers left"); sys.exit(1)
out.mkdir(parents=True, exist_ok=True)
shutil.copytree(tpl_dir / "assets", out / "assets", dirs_exist_ok=True, ignore=shutil.ignore_patterns("fonts"))
if FONT_CACHE.is_dir():
    shutil.copytree(FONT_CACHE, out / "assets" / "fonts", dirs_exist_ok=True)
(out / "whitepaper.html").write_text(res, encoding="utf-8")
(out / "private-terms.txt").write_text(pt_path.read_text(encoding="utf-8") if pt_path.exists() else "", encoding="utf-8")
(out / "qa-context.json").write_text(json.dumps({
    "account_domain": dom, "rep_email": values.get("REP_EMAIL", ""),
    "show_rep_phone": values.get("SHOW_REP_PHONE", False), "rep_phone": values.get("REP_PHONE", "") if values.get("SHOW_REP_PHONE") else "",
    "draft": values.get("SHOW_DRAFT_BANNER", True), "account_name": values.get("ACCOUNT_NAME", "")}, indent=1), encoding="utf-8")
rows = ["| Key | Printed text | Source ids | Verified (who, when) |", "|---|---|---|---|"]
for k in sorted(needed):
    rows.append(f"| {k} | {values[k].replace('|', '/')} | {', '.join(sources[k])} | |")
(out / "claims-skeleton.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
n_pages = res.count('<section class="page')
print("OK filled ->", out / "whitepaper.html", "(%d pages)" % n_pages)
