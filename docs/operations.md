# Operations and troubleshooting

Run `status` to validate the sheet without contacting Steam. Run `sync --dry-run`
to inspect change counts. A dry run reads configuration, Sheets, and Steam but
never initializes tabs, updates timestamps, migrates, or binds an account.

Use a daily or weekly schedule and manual dispatch when freshness matters.
Coordinate every writer to a given spreadsheet. A revision/content re-read
detects changes that happened before the final check; it cannot lock out a
second write in the gap after the check. Google Sheets does not provide the
conditional write this would require. Multiple deployment repositories or a
local run plus an Action are not serialized by a single workflow's concurrency.

| Symptom | Next step |
| --- | --- |
| Google 403 | Enable Sheets API and share the exact file with the credential's account |
| Google 404 | Check spreadsheet ID and account access |
| Steam 401/403 | Check API key and access; do not paste it into an issue |
| Library unavailable | Check profile/game-details privacy; retain current data |
| Zero games | Inspect Steam visibility; only use `--allow-empty` if intentional |
| Unexpected headers / duplicate AppID | Restore machine-tab schema/data; keep annotations separate |
| Different Steam account | Use a new spreadsheet for that account |
| Schema migration required | Preview `migrate`, then `migrate --apply` |
| Concurrent change detected | Stop overlapping writers and retry |
| Write connection failure | Check `status`/revision before retrying; commit may have succeeded |
| 1.8 MB update budget exceeded | Keep existing data; a future bulk-storage adapter is needed |

Reads retry transient connection errors, 429, and 5xx at most three attempts with
bounded backoff. Writes are sent once. Google applies each batch atomically;
an HTTP failure or timeout can still leave the caller uncertain whether the
server committed. A repeated sync recomputes from canonical state and cannot
duplicate AppIDs. Do not assume a failed command means the server did nothing.

The size budget applies to the complete serialized update, not just game count;
large libraries may hit it at a few thousand games depending on title lengths.
There is no silent chunking. No local cache or library export is created.
Migrations retain backups inside the same spreadsheet; ordinary sync relies on
the canonical sheet and any separate backup policy you choose.

When reporting bugs, supply tool version, command, safe error text, and a minimal
synthetic example. Avoid HTTP debug logging, keys, service-account JSON, sheet
URLs, SteamIDs, personal notes, and raw library exports in public issues.
