# Product usage queries (generic)

This public version describes what each query needs, not a real schema. Map each one to your own warehouse
before first use and keep that mapping private. Placeholders: `<warehouse>.<users_table>` and so on.

Rules for every query:
- One read-only statement per call (SELECT, or WITH ... SELECT). Never write.
- Substitute `:domain` only after checking it matches `^[a-z0-9.-]+\.[a-z]{2,}$`, and `:ws_ids` only as a comma-separated list of integers. Never paste other text into SQL.
- Never select every column of a users table (it may hold password hashes and personal data). Return counts, dates and ids, not emails, names, IPs, billing data or URL paths.
- Count rows that can repeat (check runs, events) with `count(distinct <run_id>)`.
- Treat "not deleted" carefully: if a deleted flag can be NULL or 0 for live rows, use `coalesce(<deleted_flag>, 0) = 0`.

**Ownership rule.** A domain match only finds candidate workspaces. A consultant or agency user from the domain can be a guest in someone else's workspace. Confirm ownership (Q2 signals plus the requester) before Q2b to Q5. For freemail or shared parent domains, skip the domain queries and use only workspace ids the rep confirms.

| ID | What it answers | Inputs | Needs from your warehouse | Returns |
|---|---|---|---|---|
| Q1 | Users on the account's email domain | `:domain` | `<warehouse>.<users_table>` with an email (domain part), a signup date and a last-login date | count, first signup, last login |
| Q1b | Domain users who own monitors outside any workspace (personal accounts) | `:domain` | users joined to `<warehouse>.<monitors_table>` on the owner id, live monitors only | count of users, count of monitors (not a subscription count) |
| Q2 | Candidate workspaces and ownership signals | `:domain` | `<warehouse>.<workspace_members_table>` (user id, workspace id, role) joined to users | per workspace id: members total, members from the domain, admins from the domain. No names, plans or status |
| Q2s | Ownership signals for workspace ids someone supplied | `:ws_ids`, `:domain` | same as Q2 | same as Q2 |
| Q2b | Plan, limits and use for confirmed workspaces | `:ws_ids` | `<warehouse>.<workspaces_table>` or a workspace summary view: plan, add-ons, status, trial marker, active monitors, monitor limit, schedule, estimated monthly checks | one row per workspace, no billing or payment ids |
| Q3 | Monitors in confirmed workspaces | `:ws_ids` | `<warehouse>.<monitors_table>`: workspace link, active flag, auto-created flag, created by scan or domain monitoring flag, check interval, created date | totals, active, auto-created, interval mix, first and latest |
| Q3b | Site mix (internal only) | `:ws_ids` | monitor URL; extract the host, stripping user info, query string, fragment and port | top hosts by monitor count. Never print third-party hosts; add them to `private-terms.txt` |
| Q3c | Distinct sites monitored | `:ws_ids` | same host extraction as Q3b | one count. Use this, not Q3b, for "N sites" |
| Q4 | Labels in use | `:ws_ids` | `<warehouse>.<labels_table>` (id, name, colour, org) and the monitor-to-label link | label name, colour, monitor count. Generic names only in the paper |
| Q5 | Checks and checks that triggered a notification, last 90 days | `:ws_ids` | `<warehouse>.<check_runs_table>`: run id, workspace id, monitor id, created time, a "notification triggered" flag | distinct checks, distinct notification-triggering checks, distinct monitors checked. This is not "alerts sent" |
| Q6 | Inferred use case and firmographics (internal context) | `:domain` | a CRM-enrichment table keyed by email domain, if you have one | aggregated use case, industry and size buckets |

Units: Q3c counts sites, Q3 counts monitors (pooled across workspaces, so do capacity per workspace), Q5 counts checks that triggered a notification. If usage goes in the paper, round it, use the right unit, and only with the rep's agreement.
