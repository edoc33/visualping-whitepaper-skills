#!/usr/bin/env python3
"""Automated QA for a rendered account white paper. Called by render_and_qa.sh.

Usage: qa_checks.py FILLED_HTML DOM_DUMP PDF QA_CONTEXT_JSON TEMPLATE_HTML
Text is checked twice: the filled HTML's visible text (reading order, unaffected by column layout) and
the PDF's extracted text (reading order, hyphen breaks rejoined).
Blocking (FAIL): page count and spill pages, Letter size, fonts (exact static Satoshi/Inter, embedded, no
Type 3), CSS changed from the template, labels that do not extract intact, overflow into the footer,
clipped boxes, right-margin overruns, broken images, label tracking over 0.05em, mockups without their own
"illustrative" caption, leftover placeholders, em dashes, a regex subset of the never-say table,
#1 without the exact footnote, plan gating missing on a page, wrong flag colours, privacy leaks
(emails other than the rep's, phone numbers when the phone block is off, internal tool hosts or meeting
passcodes, domains other than visualping.io, .example or the account's own, any term in
WORK_DIR/private-terms.txt).
Warnings (WARN): en dashes, numbers that need a claims-log source, large empty areas.
This is a subset. The full never-say table and the claims log are the agent's checks (SKILL.md steps 4, 6).
"""
import datetime, html as H, json, re, subprocess, sys
from pathlib import Path

src = Path(sys.argv[1]).read_text(encoding="utf-8")
dom = Path(sys.argv[2]).read_text(encoding="utf-8") if Path(sys.argv[2]).exists() else ""
pdf = Path(sys.argv[3])
ctx = json.loads(Path(sys.argv[4]).read_text(encoding="utf-8"))
tpl = Path(sys.argv[5]).read_text(encoding="utf-8")
work = Path(sys.argv[1]).resolve().parent
fails, warns, oks = [], [], []
run = lambda *a: subprocess.run(a, capture_output=True, text=True, check=True).stdout
ws = lambda s: re.sub(r"\s+", " ", s).strip()
def visible(s):
    s = re.sub(r"<!--.*?-->|<(script|style)\b.*?</\1>", " ", s, flags=re.S)
    return ws(H.unescape(re.sub(r"<[^>]+>", " ", s)))
dehyph = lambda s: re.sub(r"(\w)- (\w)", r"\1-\2", s)

body = src.split("<body", 1)[1]
sections = re.split(r'<section class="page', body)[1:]
sec_txt = [visible("<x" + s) for s in sections]
vis = " ".join(sec_txt)

# 1. pages and size
info = run("pdfinfo", str(pdf))
pages = int(re.search(r"Pages:\s+(\d+)", info).group(1))
(oks if 4 <= pages <= 6 else fails).append(f"pages={pages} (want 4 to 6)")
if len(sections) != pages:
    fails.append(f"PDF has {pages} pages but HTML has {len(sections)} page sections: content spilled or a page broke")
if not re.search(r"Page size:\s+612 x 792 pts", info):
    fails.append("page size is not US Letter (612 x 792 pts)")
page_txt = [dehyph(ws(run("pdftotext", "-f", str(i), "-l", str(i), str(pdf), "-"))) for i in range(1, pages + 1)]
flat = " ".join(page_txt)

# 2. fonts and CSS
ALLOWED = {"Satoshi-Bold", "Satoshi-Black", "Inter-Regular", "Inter-Medium"}
bad, fams = set(), set()
for r in run("pdffonts", str(pdf)).splitlines()[2:]:
    parts = r.split(); base = parts[0].split("+")[-1]; fams.add(base)
    if "Type 3" in r: bad.add(f"{base} is Type 3 (variable font or synthetic style)")
    if parts[-5] != "yes": bad.add(f"{base} not embedded")
    if base not in ALLOWED: bad.add(f"unexpected font {base} (allowed: {', '.join(sorted(ALLOWED))})")
if bad: fails.extend(sorted(bad))
else: oks.append("fonts: " + ", ".join(sorted(fams)))
if not any(f.startswith("Satoshi") for f in fams): fails.append("Satoshi missing (headings)")
if not any(f.startswith("Inter") for f in fams): fails.append("Inter missing (body)")
first_style = lambda s: (re.search(r"<style>(.*?)</style>", s, re.S) or [None, ""])[1]
if first_style(src) != first_style(tpl):
    fails.append("the filled page's CSS differs from template/whitepaper.html: never edit CSS, change values.json and refill")
for m in re.finditer(r"letter-spacing:\s*([0-9.]+)(em|px)", src):
    v = float(m.group(1)) if m.group(2) == "em" else None
    if v is not None and v > 0.05: fails.append(f"letter-spacing {m.group(1)}em > 0.05em")

# 3. labels extract intact, per page
missing, split, n_labels = [], [], 0
for i, sec in enumerate(sections):
    for lab in re.findall(r'class="(?:eyebrow|pill|lab|lab red|tag|small-h)"[^>]*>(.*?)</(?:div|span)>', sec, re.S):
        t = visible(lab)
        if not t or i >= len(page_txt): continue
        n_labels += 1
        P = page_txt[i].upper(); T = t.upper()
        if T in P: continue
        if re.sub(r"\s", "", T) in re.sub(r"\s", "", P): split.append(f"p{i+1} '{t}'")
        else: missing.append(f"p{i+1} '{t}'")
pg = lambda xs: ", ".join(sorted(set(x.split(" ")[0] for x in xs)))
if split: fails.append(f"{len(split)} letter-split labels (tracking or font problem) on {pg(split)}")
if missing: fails.append(f"{len(missing)} labels missing from the PDF text on {pg(missing)}")
if not split and not missing: oks.append(f"{n_labels} labels extract intact on their pages")

# 4. geometry and DOM checks from the template's load-time script
m = re.search(r'data-check="([^"]*)"', dom)
if not m:
    fails.append("layout measurement missing (template check script did not run)")
else:
    parts = H.unescape(m.group(1)).split(" | ")
    gaps = [p for p in parts if re.match(r"p\d+ gap_to_footer=", p)]
    if len(gaps) != len(sections): fails.append(f"expected {len(sections)} page measurements, got {len(gaps)}")
    for part in parts:
        g = re.match(r"p(\d+) gap_to_footer=(-?\d+)", part)
        if g and int(g.group(2)) < 6: fails.append(f"page {g.group(1)} content runs into the footer (gap {g.group(2)}px)")
        elif g and int(g.group(2)) > 260: warns.append(f"page {g.group(1)} has {g.group(2)}px of empty space above the footer")
        for tok, why in (("hscroll", "horizontal overflow"), (" clip ", "text clipped inside its box"),
                         (" margin ", "element runs into the right margin"), (" img ", "image failed to load"),
                         (" nocaption ", "mockup without its own 'illustrative' caption"), (" tracking ", "label tracking over 0.05em")):
            if tok in part: fails.append(f"{why}: {part}")
        if part.startswith("fonts:"): oks.append("browser loaded " + part[6:])

# 5. copy rules (HTML visible text and PDF text)
if re.search(r"\{\{[A-Z0-9_]+\}\}", src) or re.search(r"\{\{[A-Z0-9_]+\}\}", flat): fails.append("unfilled {{placeholders}} remain")
# Diagnostics name the rule and page, never the surrounding text, so the report does not leak.
for name, txt in (("html", vis), ("pdf", flat)):
    if "\u2014" in txt: fails.append(f"em dash ({name}) on " + ", ".join(f"p{i+1}" for i, t in enumerate(sec_txt) if "\u2014" in t))
if "\u2013" in vis: warns.append("en dash found; prefer 'to' in ranges")
NEVER = {  # regex subset of references/claims-guardrails.md "Never say"; verified_on 2026-11-24
 r"\bpen(etration)?[ -]?test": "keep pen test material out of the paper; security reviews go through the Trust Center process (G-15)",
 r"dashboard 2\.0": "not a public name",
 r"take[ -]?downs?|taken down|tracks? it (through )?to removal|get it removed": "Visualping detects and alerts; it does not remove content",
 r"as (they|it) appears?|the moment (it|they)|instantly|real[- ]*time|\bimmediately\b|\bas soon as\b|\bday one\b": "checks run on a schedule; Domain Monitoring adds pages on the next rescan",
 r"\bdepth ?\d": "'depth' is not a public setting name",
 r"SOC ?2 Type ?II\b(?![^.]{0,40}planned)|SOC ?2 (Type ?I )?(certified|compliant)": "SOC 2 Type I is in progress; Type II is planned (G-16)",
 r"guarantee|never miss|\b(catch|catches|detect|detects|see|sees|capture|captures|flag|flags)( \w+)? every (change|page)\b|\bevery page\b|100% (coverage|accura)|complete coverage|no false positives": "no coverage guarantees; AI matching is not perfect",
 r"redesigned": "check the What's New date before calling anything redesigned",
 r"alerts? (you )?(on|for|when|whenever) (every|each|a|any) new pages?\b(?! that)|new pages? (is|are) (published|added|created)": "only matches to the alert criteria alert (G-4, G-5)",
 r"\bwho (looked at|viewed|has read|opened)\b|read receipts?": "flags and comments record actions, not who viewed",
 r"\b(MFA|2FA|two[- ]factor)\b(?![^.]{0,60}identity provider)": "no native MFA claim; MFA is set in the identity provider (G-17)",
 r"data residency|zero (data )?retention|\bdata (is )?stored in\b": "no residency or retention claims without a sourced row",
 r"\bnumber one\b|\bindustry[- ]leading\b|\bleading\b|\bbest[- ]in[- ]class\b": "superlatives only through the #1 footnote rule (G-1)",
 r"\buptime\b|\bSLA\b|99\.\d+ ?%|24/7": "no uptime, SLA or support-hours promises",
 r"ISO ?27001|HIPAA|FedRAMP|\bPCI\b|GDPR[- ]compliant|AES-?256": "no certifications or standards beyond G-16",
 r"\b(OpenAI|GPT-?\d+|Anthropic|Gemini|Llama|Mistral)\b|\d+ ?% accura": "no AI model vendors or accuracy figures (the MCP sentence naming Claude and ChatGPT as clients is fixed text, G-14)",
 r"any website|login[- ]protected|behind (a )?login|bypass(es)? (bot|captcha)": "no coverage claims for any site, logins or bot blocks",
 r"legal[- ]grade|court[- ]admissible|legally binding": "no legal-evidence claims",
 r"\bunlimited\b": "no unlimited claims; quote plan limits (G-21)",
 r"\bsav(e|es|ing) (you )?\d+|\d+ ?% (faster|less time)": "time or money saved only when the customer said it (F#)",
 r"\b(ChangeTower|Distill|Wachete|Hexowatch|Versionista|Fluxguard|PageCrawl|Sken\.io|Klue|Crayon)\b": "do not name competitors or the customer's current vendor",
 r"\b(robust|seamless|unlock|delve|game[- ]chang|cutting[- ]edge|leverag)": "banned word",
}
if datetime.date.today() > datetime.date(2027, 2, 7):
    NEVER[r"\bnew dashboard\b"] = "after 2027-02-07 say 'the dashboard'"
hits = set()
acct_name = (ctx.get("account_name") or "").lower()
for pat, why in NEVER.items():
    for name, txt in (("html", vis), ("pdf", flat)):
        for h in set(mm.group(0) for mm in re.finditer(pat, txt, re.I)):
            if acct_name and h.lower() in acct_name: continue  # the account's own name
            hits.add(f"never-say '{h}' ({name}): {why}")
fails.extend(sorted(hits))
BADGE = "#1 Page Monitoring Agent*"
FOOT = "*#1 based on the most users publicly shared (2M+) and the most reviews on G2 and Gartner Peer Insights among page monitoring tools. Review counts as of"
if re.search(r"#1(?!\d)", vis + " " + flat) and FOOT not in sec_txt[0]:
    fails.append("#1 claim without the exact footnote on the cover")
rest = vis.replace(BADGE, " ").replace(FOOT, " ")
if re.search(r"#1(?!\d)|number one", rest, re.I):
    fails.append("#1 used outside the fixed badge and its footnote")
# plan gating, per page
for i, t in enumerate(sec_txt):
    if "Site scan" in t and "Business" not in t: fails.append(f"p{i+1} names Site scan without the Business plan")
    if "Domain Monitoring" in t and "Solutions" not in t: fails.append(f"p{i+1} names Domain Monitoring without the Solutions plan")
    if re.search(r"Slack|Microsoft Teams|Google Sheets|scheduled reports?", t) and not re.search(r"Business|Solutions", t):
        fails.append(f"p{i+1} names Slack, Teams, Sheets or scheduled reports without the Business or Solutions plan")
    # heuristic only: the claims log is the real check of which plan each feature is on
    if re.search(r"(Site scan|Slack|Microsoft Teams|Google Sheets|scheduled reports?|labels?)[^.]{0,40}\b(Free|Starter|Personal|every plan|all plans|any plan)\b", t, re.I):
        fails.append(f"p{i+1} puts a Business feature on a lower or every plan")
# flag colours, in order
for s in re.findall(r'<div class="swatch">(.*?)</div>', src, re.S):
    cols = [c.lower() for c in re.findall(r"background:(#[0-9a-fA-F]{6})", s)]
    if cols != ["#e5484d", "#2fa36b", "#f5c518", "#1882ff", "#8e4ec6"]:
        fails.append(f"flag swatches {cols} are not red, green, yellow, blue, purple")

# 6. privacy
both = vis + " " + flat
# Privacy failures name the type and page only, never the value, so the report itself does not leak.
mask = lambda v: (v[:2] + "***") if v else "***"
def page_of(v):
    for i, t in enumerate(sec_txt):
        if v.lower() in t.lower(): return f"p{i+1}"
    return "pdf"
rep = (ctx.get("rep_email") or "").lower()
for e in sorted(set(x.lower() for x in re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", both))):
    if e != rep: fails.append(f"privacy: an email other than REP_EMAIL on {page_of(e)} ({mask(e)})")
rep_digits = re.sub(r"\D", "", ctx.get("rep_phone") or "")
for ph in set(re.findall(r"\+?\(?\d[\d ().-]{8,}\d", both)):
    d = re.sub(r"\D", "", ph)
    if len(d) >= 10 and not (rep_digits and d == rep_digits):
        fails.append(f"privacy: phone-like number other than the confirmed REP_PHONE on {page_of(ph)} ({mask(ph.strip())})")
acct = (ctx.get("account_domain") or "").lower()
internal = r"(?:app\.)?hubspot\.com|hubspot|slack\.com|zoom\.us|meet\.google|tldv|passcode|pwd="
if re.search(r"/archives/|https?://\S*\?\S*|[?&](token|key|sig|auth|access_token)=", both, re.I):
    fails.append("privacy: a URL with a query string, token or internal route (print bare public URLs only)")
if re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", both):
    fails.append("privacy: an IP address appears in the paper")
for h in set(mm.group(0).lower() for mm in re.finditer(internal, both, re.I)):
    if acct and h.split(".")[0] in acct.split("."): continue  # the account itself is, for example, hubspot.com
    fails.append(f"privacy: internal tool or meeting detail on {page_of(h)} ({mask(h)})")
def own(d): return d == acct or d.endswith("." + acct)
no_mail = re.sub(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", " ", both)
for d in sorted(set(x.lower() for x in re.findall(r"\b(?:[a-z0-9-]+\.)+[a-z]{2,24}\b", no_mail, re.I))):
    if d in ("visualping.io",) or d.endswith(".visualping.io") or d.endswith(".example") or d == "example" or (acct and own(d)): continue
    if rep and rep.endswith("@" + d): continue
    fails.append(f"privacy: domain other than visualping.io, .example or the account's own on {page_of(d)} ({mask(d)})")
tpl_body = tpl.split("<body", 1)[1]
fixed_txt = visible(re.sub(r"\{\{[A-Z0-9_]+\}\}", " ", tpl_body))
pt = work / "private-terms.txt"
if not pt.exists():
    fails.append("privacy: private-terms.txt missing from the draft folder (fill_template.py copies it)")
else:
    for term in [l.strip() for l in pt.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]:
        if term.lower() in fixed_txt.lower(): continue  # also part of fixed template text; checked by the claims log
        if term.lower() in both.lower(): fails.append(f"privacy: a private term appears on {page_of(term)} ({mask(term)})")
for pat in [r"\$[\d,]+", r"\b\d[\d,]*\+? (?:vendors|domains|pages|users|sites|competitors|suppliers|monitors|alerts)"]:
    for h in sorted(set(re.findall(pat, vis))):
        warns.append(f"a number on {page_of(h)} must map to a fact-sheet row with a source (claims log)")

print("QA", pdf.name)
for o in oks: print("  OK  ", o)
for w in warns: print("  WARN", w)
for f in fails: print("  FAIL", f)
print("RESULT:", "FAIL" if fails else "PASS", f"({len(fails)} fail, {len(warns)} warn)")
sys.exit(1 if fails else 0)
