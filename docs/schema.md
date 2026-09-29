# Schema v1

Reserved tab names and their bound numeric IDs are part of the contract. Keep
machine headers exactly as initialized. Do not add custom columns to `Steam`;
add arbitrary fields as rows in `Annotations`, or create your own dashboard tab.

## Steam

| Column | Type | Meaning |
| --- | --- | --- |
| `appid` | Positive integer | Stable primary key; unique in this tab |
| `name` | Text | Steam app name; missing app info preserves a known name |
| `playtime_forever` | Nonnegative integer | Lifetime minutes reported by Steam |
| `playtime_2weeks` | Nonnegative integer | Recent minutes; omitted API field becomes zero |
| `rtime_last_played` | Nonnegative integer | Unix seconds reported by Steam; zero means unavailable |
| `img_icon_url` | Text | Steam icon hash, despite the API field's name; not a full URL |
| `present` | Boolean | AppID appeared in the most recent accepted snapshot |
| `first_seen_at` | UTC ISO-8601 text | First observation by this datastore |
| `last_synced_at` | UTC ISO-8601 text | Last successful snapshot that evaluated this row |
| `last_seen_at` | UTC ISO-8601 text | Last snapshot containing this AppID |

Missing rows retain their name, playtime, icon, and observation history. They only
change `present` and `last_synced_at`. Reappearance preserves `first_seen_at`.
Counts in CLI summaries describe material changes, excluding observation times:
added, updated (existing present games), missing (newly absent), restored, and
unchanged are mutually exclusive. Every stored row belongs to one category.

## Annotations

| Column | Meaning |
| --- | --- |
| `appid` | Game identity, referencing a Steam AppID |
| `field` | Your field name, such as `rating`, `status`, `japanese_quality` |
| `value` | Your value, stored as text for flexible types |
| `provenance` | Suggested values: `manual`, `researched`, `ai` |
| `source_url` | Optional evidence link |
| `updated_at` | Suggested UTC ISO-8601 timestamp |
| `confidence` | Optional confidence in a researched assertion, e.g. 0–1 |
| `notes` | Context or qualifications |

Use one current assertion per `(appid, field)`. You may annotate games before
they appear in your library. The synchronizer does not validate or rewrite this
tab, so these are conventions for people and future annotation tools. A future
annotation writer should enforce its own uniqueness and conflict semantics.
Setup creates only the header; Steam sync does not even seed AppID rows here.
This makes concurrent manual annotation edits independent of sync.

## Metadata

`_Meta` has `key,value` columns. All metadata values are written as text, including
SteamID64, to prevent spreadsheet numeric precision loss.

Required keys: `schema_version`, `steam_sheet_id`, `annotations_sheet_id`,
`meta_sheet_id`, `steam_id`, `revision`, `last_successful_sync`, `tool_version`.
Unknown metadata keys are preserved. Account binding begins on the first
successful sync; a dry run does not bind it. Revision increments only on a sync
commit or migration. Setup begins at revision zero.

## Migrations

Schema version is independent of the Python package version. Sync accepts only
v1; `status` and `migrate` can read the specifically supported v0 shape. v0 is a
synthetic predecessor for testing the migration mechanism: it has every v1
Steam column except the final `last_seen_at`, and the same metadata keys.

`steam-library migrate` describes the change without writing. `--apply` sends
one batch that duplicates `Steam` and `_Meta` to unique `_backup_v0_*` tabs,
appends `last_seen_at`, and updates the version/revision. The new timestamp is
the existing `last_synced_at` for present games, blank for absent games where
history cannot be inferred. Repeating the migration on v1 is a no-op.

There is no automatic destructive downgrade or annotation migration. Recover
using the backup data in the original bound tabs (retain their IDs), preferably
in a copy of the whole spreadsheet first. Restoring the old `_Meta` also restores
its old version: use compatible code or run the migration again. Do not rename
backup tabs over originals; that changes tab IDs and triggers identity checks.
