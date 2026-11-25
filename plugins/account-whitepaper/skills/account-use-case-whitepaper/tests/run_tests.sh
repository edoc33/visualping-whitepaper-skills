#!/usr/bin/env bash
# Regression tests for the fill, render and QA scripts. Uses only a fictional account.
# Usage: tests/run_tests.sh   (needs Chrome/Chromium, poppler, python3, network once for fonts)
set -u   # no pipefail: the QA exit code is checked on purpose, output is grepped separately
HERE="$(cd "$(dirname "$0")" && pwd)"; S="$HERE/../scripts"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
export VP_FONT_CACHE="${VP_FONT_CACHE:-$HOME/.cache/vp-whitepaper-fonts}"   # reuse the cache if present
export VP_WP_TEST=1
pass=0; failn=0
ok()  { echo "PASS $1"; pass=$((pass+1)); }
bad() { echo "FAIL $1"; failn=$((failn+1)); }
ls "$VP_FONT_CACHE"/Satoshi-Bold.ttf "$VP_FONT_CACHE"/Satoshi-Black.ttf "$VP_FONT_CACHE"/Inter-Regular.ttf "$VP_FONT_CACHE"/Inter-Medium.ttf >/dev/null 2>&1 || "$S/fetch_fonts.sh" >/dev/null || { echo "font fetch failed"; exit 2; }
FX="$HERE/fixture-example-values.json"; SRC="$HERE/fixture-example-sources.json"
prep() { cp "$2" "$T/$1-values.json"; if ! python3 "$S/fill_template.py" "$T/$1-values.json" "$SRC" "$T/$1" >"$T/$1.fill.log"; then echo "  (fill failed for $1)"; cat "$T/$1.fill.log"; return 1; fi; }
variant() { python3 - "$FX" "$T/$1.json" "$2" <<'P'
import json,sys; v=json.load(open(sys.argv[1])); v.update(json.loads(sys.argv[3])); json.dump(v,open(sys.argv[2],"w"))
P
}
render() { "$S/render_and_qa.sh" "$T/$1" "Example.pdf" 2>&1; }
# 1. good fixture, 6 pages, AUTO_QA_PASS marker and final name
prep good "$FX" && render good >/dev/null && ok "6-page fixture passes" || bad "6-page fixture should pass"
d="$(ls -d "$T"/good/render-* | head -1)"
[ -e "$d/AUTO_QA_PASS" ] && [ -s "$d/Example.pdf" ] && [ ! -e "$d/UNVERIFIED.pdf" ] && ok "pass leaves QA_PASS and final name" || bad "pass marker or name wrong"
grep -q "Owner\|Success test" "$T/good/claims-skeleton.md" 2>/dev/null; [ -s "$T/good/claims-skeleton.md" ] && ok "claims skeleton written" || bad "no claims skeleton"
[ ! -e "$T/good/assets/fonts/.." ] || [ -s "$T/good/assets/fonts/Satoshi-Bold.ttf" ] && ok "fonts copied from cache, not from the skill folder" || bad "fonts not copied"
[ -z "$(ls "$HERE/../template/assets" | grep -i fonts)" ] && ok "no fonts inside the skill folder" || bad "fonts found inside template/assets"
# 2. four-page variant (capability pages off)
variant v4 '{"SHOW_CAP1_PAGE":false,"SHOW_CAP2_PAGE":false}'; prep four "$T/v4.json" && render four >/dev/null && ok "4-page variant passes" || bad "4-page variant should pass"
# 3. all optional blocks on, draft banner on: passes and is named INTERNAL DRAFT
variant vall '{"SHOW_BADGE":true,"SHOW_PRICING":true,"SHOW_REP_PHONE":true,"SHOW_PRICE2":true,"SHOW_PRICE3":true,"SHOW_DRAFT_BANNER":true}'
prep all "$T/vall.json" && out="$(render all)" && ok "all flags on passes" || { bad "all flags on should pass"; echo "$out" | grep FAIL; }
ls "$T"/all/render-*/"INTERNAL DRAFT - Example.pdf" >/dev/null 2>&1 && ok "draft banner names the file INTERNAL DRAFT" || bad "draft file name missing"
# 4. fill refuses missing values, unknown keys, missing sources, real example domains
variant vbad '{"NOT_A_KEY":"x","MOCK_DOMAIN":"realcompany.com"}'; python3 - "$T/vbad.json" <<'P'
import json,sys; v=json.load(open(sys.argv[1])); v.pop("COVER_HEADLINE"); json.dump(v,open(sys.argv[1],"w"))
P
o="$(python3 "$S/fill_template.py" "$T/vbad.json" "$SRC" "$T/badfill")" && bad "fill should fail" || ok "fill rejects bad values"
for p in "missing value for COVER_HEADLINE" "unknown keys: NOT_A_KEY" "MOCK_DOMAIN must use a reserved"; do echo "$o" | grep -q "$p" && ok "fill detects: $p" || bad "fill missed: $p"; done
[ ! -e "$T/badfill/whitepaper.html" ] && ok "failed fill writes nothing" || bad "failed fill wrote output"
python3 -c 'import json,sys; s=json.load(open(sys.argv[1])); s.pop("CTA_HEADLINE"); json.dump(s,open(sys.argv[2],"w"))' "$SRC" "$T/src-missing.json"
o="$(python3 "$S/fill_template.py" "$FX" "$T/src-missing.json" "$T/nosrc")"; echo "$o" | grep -q "no valid source ids for CTA_HEADLINE" && ok "fill requires a source per printed key" || bad "fill missed missing source"
# 5. overclaims, em dash, wrong flags, tracking, missing caption, CSS edit
variant vclaims '{"COVER_DEK":"We take down leaks in real time \u2014 guaranteed, with a pen test summary and SOC 2 Type I certified.","STEP3_TEXT":"Dashboard 2.0 alerts on every new page as it appears."}'
prep claims "$T/vclaims.json"
sed -i.bak 's/letter-spacing:.05em;text-transform:uppercase;color:var(--deep)/letter-spacing:.3em;text-transform:uppercase;color:var(--deep)/; s/background:#2fa36b/background:#20b093/; s/<div class="illus">Illustrative alert<\/div>//; s/(illustrative)<\/div>/<\/div>/g' "$T/claims/whitepaper.html"
out="$(render claims)"; rc=$?
[ $rc -ne 0 ] && ok "overclaim fixture fails" || bad "overclaim fixture should fail"
ls "$T"/claims/render-*/FAILED-QA.pdf >/dev/null 2>&1 && [ ! -e "$(ls -d "$T"/claims/render-* | head -1)/AUTO_QA_PASS" ] && ok "failed QA renames to FAILED-QA.pdf, no marker" || bad "failed QA naming wrong"
for pat in "never-say 'take down'" "never-say 'real time'" "em dash" "pen test" "SOC 2 Type I certified" "Dashboard 2.0" "as it appears" "flag swatches" "letter-spacing .3em" "illustrative" "CSS differs"; do
  echo "$out" | grep -q -i -- "$pat" && ok "detects: $pat" || bad "missed: $pat"
done
# 6. banned phrases inside multi-column cards, wrapped mid-sentence
variant vwrap '{"NEED1_TEXT":"Your list of forty competitor domains is checked and we promise that nothing slips, because we never miss a single pricing edit on any of them.","POC2_TEXT":"Refine the rule so the team can see alerts in real time as the work goes on."}'
prep wrap "$T/vwrap.json"; out="$(render wrap)"
echo "$out" | grep -q "never-say 'never miss'" && echo "$out" | grep -qi "never-say 'real time'" && ok "detects banned phrases in narrow columns" || bad "missed banned phrases in columns"
# 7. long text overflows, #1 without footnote, plan gating, privacy
variant vlong "{\"STEP1_TEXT\":\"$(python3 -c 'print(("We create a monitor for each pricing page on your list. " * 30).strip())')\"}"
prep long "$T/vlong.json"; out="$(render long)"; echo "$out" | grep -q "clip\|footer\|spilled" && ok "long text fails layout QA" || bad "long text should fail"
variant vfoot '{"SHOW_BADGE":true}'; prep foot "$T/vfoot.json"; sed -i.bak 's/\*#1 based on the most users publicly shared/*Based on users/' "$T/foot/whitepaper.html"
out="$(render foot)"; echo "$out" | grep -q "#1 claim without the exact footnote" && ok "#1 without footnote fails" || bad "#1 without footnote should fail"
variant vplan '{"STEP2_TEXT":"Site scan finds pricing pages on each site.","STEP4_TEXT":"Alerts arrive in Slack. The team flags each change."}'
prep plan "$T/vplan.json"; out="$(render plan)"; echo "$out" | grep -q "names Site scan without the Business plan" && ok "plan gating per page" || bad "missed plan gating"
variant vpriv '{"NEED2_TEXT":"Jane said on the zoom.us call with jane.doe@customer.com, phone 416 555 0199, that vendor-portal.net leaks."}'
mkdir -p "$T/acct"; cp "$T/vpriv.json" "$T/acct/values.json"; printf 'Jane\n' > "$T/acct/private-terms.txt"
python3 "$S/fill_template.py" "$T/acct/values.json" "$SRC" "$T/acct/draft-1" >/dev/null || echo "  (fill failed for acct)"; out="$(render acct/draft-1)"
for p in "an email other than REP_EMAIL on p2" "phone-like number" "internal tool or meeting detail" "domain other than" "a private term appears on p2"; do echo "$out" | grep -q -- "$p" && ok "privacy detects: $p" || bad "privacy missed: $p"; done
echo "$out" | grep -q "jane.doe\|vendor-portal\|416 555" && bad "QA report echoes private values" || ok "QA report masks private values"
ls "$T"/acct/draft-1/render-*/AUTO_QA_PASS >/dev/null 2>&1 && bad "private term should block AUTO_QA_PASS" || ok "private term in the account folder blocks AUTO_QA_PASS"
# 7b. production mode: FIXTURE sources refused, fact-sheet rows required, banner-off refused with open confirmations
mkdir -p "$T/prod"; cp "$FX" "$T/prod/values.json"; : > "$T/prod/private-terms.txt"
printf '| F10 | Use case | CUST | form | Needs rep confirmation |\n' > "$T/prod/fact-sheet.md"
o="$(VP_WP_TEST=0 python3 "$S/fill_template.py" "$T/prod/values.json" "$SRC" "$T/prod/draft-1")"
echo "$o" | grep -q "no valid source ids" && ok "production fill refuses FIXTURE sources" || bad "production fill accepted FIXTURE"
echo "$o" | grep -q "SHOW_DRAFT_BANNER is false but" && ok "banner-off refused while confirmations are open" || bad "banner-off not refused"
o="$(python3 "$S/fill_template.py" values.json "$SRC" "$T/rel")"; echo "$o" | grep -q "usage" && ok "fill refuses relative paths" || bad "fill accepted relative path"
# 7c. round-2 adversarial cases
variant vreal '{"ACCOUNT_DOMAIN":"realcompany.com"}'; mkdir -p "$T/real"; cp "$T/vreal.json" "$T/real/values.json"
python3 "$S/fill_template.py" "$T/real/values.json" "$SRC" "$T/real/d1" | grep -q "only for the fictional fixture" && ok "test mode refused for a real domain" || bad "test mode accepted a real domain"
variant vno1 '{"SHOW_BADGE":true,"NEED3_TEXT":"We are #1 for accuracy. See https://examplecorp.example/doc?token=abc and 10.0.0.12."}'
prep no1 "$T/vno1.json"; out="$(render no1)"
for p in "#1 used outside" "query string, token" "IP address"; do echo "$out" | grep -q -- "$p" && ok "detects: $p" || bad "missed: $p"; done
# 8. missing font fails closed, no empty render folder
n0="$(ls -d "$T"/good/render-* | wc -l)"; rm -f "$T/good/assets/fonts/Inter-Regular.ttf"
"$S/render_and_qa.sh" "$T/good" "Example.pdf" >/dev/null 2>&1 && bad "render without fonts should fail" || ok "missing font fails closed"
[ "$(ls -d "$T"/good/render-* | wc -l)" = "$n0" ] && ok "no empty render folder on precondition failure" || bad "empty render folder created"
echo "passed $pass, failed $failn"; [ $failn -eq 0 ]
