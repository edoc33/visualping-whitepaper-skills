# Account Use Case White Paper

One skill for sales and marketing teams who want an account-specific white paper without overclaiming.
Give it an account name or domain. It reads what your team already knows about that account, builds a
sourced fact sheet, and writes a 4 to 6 page branded PDF that explains how the product solves their problem,
in their words. Every product claim is checked against a dated guardrails table, and automated QA checks
layout, fonts, banned phrases, plan gating and privacy before anything is handed over.

It never sends, shares or writes to any system. A person reviews the PDF and the claims log, then sends it.

This is a reference, adapted from a skill used in real sales work at Visualping. Internal details
(warehouse schema, channel names, account data) are replaced with generic placeholders, and the product
facts are dated: recheck them before you rely on them.

## What it expects
- **HubSpot** (read-only connector): company, deal, contacts, meetings, notes.
- **A data warehouse** (read-only SQL tool): product usage. `references/warehouse-queries.md` lists what each query needs; map it to your own schema.
- **tl;dv**: call notes and transcripts, or its HubSpot notes as a fallback.
- **Slack** (read-only search): internal context, never quoted in the paper.
- **Rendering**: headless Chrome or Chromium, poppler (`pdftotext`, `pdffonts`, `pdfinfo`, `pdftoppm`) and Python 3.

## Install

In Claude Code:

```text
/plugin marketplace add edoc33/visualping-whitepaper-skills
/plugin install account-whitepaper@account-whitepaper
```

Or copy `plugins/account-whitepaper/skills/account-use-case-whitepaper/` into your agent's skills folder.

## Layout
- `SKILL.md`: the recipe (scope, gather, fact sheet, narrative, guardrails, render, QA, hand over).
- `template/`: the HTML template with `{{PLACEHOLDERS}}` and optional blocks. The logos are placeholders.
- `references/`: claims guardrails, brand and style, fact-sheet template, generic warehouse queries.
- `scripts/`: `fetch_fonts.sh`, `fill_template.py`, `render_and_qa.sh`, `qa_checks.py`.
- `tests/`: a fictional Example Corp fixture (`.example` domains only) and the regression suite.

All paths are inside `plugins/account-whitepaper/skills/account-use-case-whitepaper/`.

## Run the tests

```sh
cd plugins/account-whitepaper/skills/account-use-case-whitepaper
tests/run_tests.sh
```

It downloads the fonts once unless they are already cached, then fills, renders and checks good and
deliberately bad variants. It should end with `failed 0`.

## License
MIT. See `LICENSE` and `THIRD_PARTY_NOTICES.md`.
