# Fact sheet: {Account name} ({domain})

Built {YYYY-MM-DD HH:MM, time zone} by {assistant} for {requesting user}. Internal and private to the requester: never attach this file to the customer PDF or share it. No contact emails, phone numbers, meeting links or passcodes in this file; use record ids.

Every row has a source. Tag who said it:
- **[CUST]** the customer said it (call, form, email). Write it in the paper as theirs: "you told us", "your list has".
- **[VP-REP]** a Visualping rep said it (quote, plan, date). Must be confirmed by the rep before sending.
- **[CRM]** HubSpot field. **[USAGE]** warehouse aggregate. **[SLACK]** internal thread. **[PUBLIC]** a public web page, checked today.
- **[G-#]** a product claim from references/claims-guardrails.md.
Status: Verified / Customer-stated / Needs rep confirmation / Conflict (explain) / Do not use.

## 1. Account snapshot
| # | Fact | Tag | Source (record id, call + timestamp, URL, query name) | Status |
|---|---|---|---|---|
| F1 | Company name and domain | CRM | HubSpot company {id} | |
| F2 | Industry, size (as a range, not a precise figure unless public) | CRM / PUBLIC | | |
| F3 | Deal stage, close date, owner (AE) | CRM | HubSpot deal {id} | |
| F4 | Contacts on the deal: role or title only (no personal emails or phone numbers in the paper) | CRM | | |

## 2. The problem in their words
| # | Fact | Tag | Source | Status |
|---|---|---|---|---|
| F10 | Use case in one sentence, ideally their own words from the demo form or call | CUST | form / tl;dv {meeting id} @ mm:ss | |
| F11 | Why now (trigger, risk, deadline) | CUST | | |
| F12 | Scale: how many sites, pages, vendors, competitors (state the unit) | CUST | | |
| F13 | Where the list lives today (CRM export, spreadsheet, nowhere) | CUST | | |
| F14 | What "a match" means to them (the alert rule in plain language) | CUST | | |
| F15 | Who reviews alerts, how often, and in which tool | CUST | | |
| F16 | Limits and things they said they do not want (objections and budget go in section 5, never in the paper) | CUST | | |

## 3. Current Visualping usage (aggregates only)
| # | Fact | Tag | Source | Status |
|---|---|---|---|---|
| F20 | Users on the domain, first signup, last login; users on personal plans | USAGE | Q1, Q1b | |
| F21 | CONFIRMED workspace ids (admin from the domain, most members from the domain, confirmed by requester or rep), plan, limits and trial status | USAGE | Q2, Q2b | |
| F22 | Monitors: total, active, frequency mix, auto-created (Site scan / Domain Monitoring) | USAGE | Q3 | |
| F23 | Labels in use (names only if they are generic, such as "Competitors") | USAGE | Q4 | |
| F24 | Checks and alerts, last 90 days | USAGE | Q5 | |
| F25 | Top monitored site types (counts, not URLs) | USAGE | Q3b | |

## 4. Commercials and plan (internal source of truth for page 6)
| # | Fact | Tag | Source | Status |
|---|---|---|---|---|
| F30 | Recommended plan(s) and why (G-3 Site scan is Business; G-4 Domain Monitoring is Solutions) | VP-REP | | |
| F31 | Price estimates, each with its unit (pages, check frequency, add-ons) | VP-REP | call @ mm:ss / HubSpot | |
| F32 | PoC scope (representative pages), start date, owner (POC_OWNER), success test (POC_SUCCESS_TEST: a known change to catch, cadence, reviewer, what counts as a useful alert), decision date (POC_DECISION_DATE) | VP-REP / CUST | | |
| F36 | Capacity check (G-21): per workspace: pages x checks per day x 31 on each monitor's own schedule vs that workspace's monthly checks, page count assumed per domain, expected alert volume and who handles it | VP-REP / G-21 | /pricing, {date} | |
| F35 | Account setup that changes the claims (for example the blank-diff first check, G-5) | VP-REP / SLACK | | |
| F33 | Go-live target | CUST | | |
| F34 | Rep name, title, email (phone only if the rep confirms it) | CRM / VP-REP | deal owner; confirmed by the rep, relayed by {who} on {date} | |

## 5. Internal context (never quoted in the paper)
| # | Fact | Tag | Source | Status |
|---|---|---|---|---|
| F40 | Internal notes that change what we promise (product limits, setup the team agreed to, e.g. the G-5 blank-diff first check) | SLACK | permalink | |
| F41 | Corrections from product or sales leads | SLACK | | |
| F42 | Budget timing, objections, remarks about vendors or colleagues (internal only) | CUST / VP-REP | | |

## 5b. Confirmations
| Item (F#) | Confirmed by (the rep) | Relayed by | When | How (call, message) |
|---|---|---|---|---|

## 6. Conflicts and gaps
Split gaps into "not reachable" (no access, tool error) and "searched, nothing found".
List every place two sources disagree (for example the public site gives one partner count and the call gives another) and how the paper handles it. List every placeholder you could not fill and the question to ask the rep.

## 7. Claims log (fill after drafting)
| Page | Exact sentence in the PDF (including fixed template text) | Fact / guardrail IDs | Source and date checked | Verdict (Verified / Customer-stated / Softened / Needs rep confirmation) |
|---|---|---|---|---|
