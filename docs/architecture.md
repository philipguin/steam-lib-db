# Architecture and decisions

This document records the design before implementation. Status: accepted for v0.1.

## Ownership, identity, and storage

Google Sheets is the initial canonical datastore. The reusable software owns no
library database: each deployment supplies credentials and a spreadsheet ID.
Steam AppID is the stable game key; names are display data and may change.

Three tabs represent two ownership domains and control state:

* `Steam`: one row per AppID, written only by the synchronizer.
* `Annotations`: user/AI-owned assertions keyed by (AppID, field), never written
  by synchronization or migrations. Setup creates its header once.
* `_Meta`: schema version, bound tab IDs, bound Steam account, revision, and last
  successful sync time. It contains deployment data and never belongs in Git.

Personal and Research are unified. Both are annotations from the sync engine's
perspective; neither is safe for Steam to replace. Per-field provenance,
source URL, date, and optional confidence distinguish a rating from researched
language support without imposing a second lifecycle or arbitrary tab boundary.
The long-form annotation model allows custom fields without schema changes.
Separate research storage becomes justified only if a future enrichment agent
needs independently refreshable assertions, conflicts, or multiple sources.

The storage protocol exposes only Steam state and control metadata to the sync
engine. The Sheets adapter validates tab identity and restricts sync writes to
the bound Steam and metadata IDs. This is an application boundary, not a Google
permission boundary: Sheets credentials grant access to the whole spreadsheet.

## Synchronization contract

Fetch and validate a complete owned-games response before planning any writes.
Missing games are retained with `present=false`; this means absent from the last
accepted API snapshot, not proof of refund, deletion, or loss of ownership.
Unknown/private responses, duplicate AppIDs, count mismatches, and malformed
records abort. An explicit empty library additionally requires `--allow-empty`.
Playtime is stored in minutes, timestamps in UTC, and SteamID64 as text.
Played free games are always included; changing query scope must not silently
change the meaning of presence. API coverage is not the entire Steam client
library (for example, family sharing and unplayed free titles can differ).

Preserve existing row order and append new AppIDs in numeric order. Never clear,
delete, or sort entire tabs. Write literal strings rather than formulas.
Steam rows and successful-sync metadata are committed in one atomic Sheets
batch. Dry runs perform reads and validation but no mutation.

Bind a spreadsheet to a Steam account on its first successful sync. Refuse a
different account, unknown schema versions, unexpected headers, duplicate keys,
or replaced tabs. Re-read state immediately before writing to detect concurrent
changes. Sheets has no compare-and-swap transaction for this read/write sequence;
deployments must use one writer per spreadsheet. Annotation editing is safe
during sync; editing machine-owned tabs is not.

## Schema evolution

Initialization creates schema v1 atomically in unused reserved tab names; it does
not adopt unknown existing data. Ordinary sync never runs migrations implicitly.
Explicit migrations have exact source-schema preconditions, a reviewable plan,
and atomic backup copies of affected machine-owned tabs plus the migration.
Backups remain in the spreadsheet. Unknown/newer versions fail closed. v0 is a
documented synthetic legacy schema used to exercise the migration path, not an
assertion that an earlier release existed. Annotations are untouched.

## Repository layout

```text
src/steam_library/
  cli.py, config.py, errors.py    command boundary and deployment configuration
  steam.py                      validated Steam Web API client
  sync.py                       pure merge plan and orchestration
  schema.py                     versioned contracts and validation
  storage/base.py                narrow storage protocol
  storage/google_sheets.py       Sheets transport, initialization, migrations
tests/                          synthetic data; no credentials or personal data
docs/                           architecture, schema, setup, operations, releases
examples/                       deployment workflow and environment template
action.yml                      reusable composite GitHub Action
Dockerfile                      portable execution image
.github/workflows/              CI and release artifacts; no personal scheduler
```

Python is appropriate for an IO-oriented utility with mature Google auth support.
Keep business logic independent of HTTP and Sheets so a later SQLite or hosted
adapter can reuse identity, validation, and merge semantics.

## Deployment model and friction

The public repository contains only reusable code, docs, and synthetic fixtures.
Credentials, schedules, IDs, library snapshots, and backups belong to a user's
deployment. Never upload them as workflow artifacts or log API bodies/URLs.

The v0.1 browser-only path is a tiny user-owned deployment repository with one
workflow and secrets calling the public Action at a pinned commit. No fork or
local install is necessary once the upstream repository is published. An
existing private repository can host this workflow. This is zero local install,
not zero configuration: Google authorization and Steam API access are required.

CLI and Docker serve desktop and self-hosted schedules. Release archives include
a Python wheel and source distribution; package-index publishing and a hosted
multi-tenant service are deliberately not prerequisites. A future OAuth web
onboarding service could remove the deployment repository but adds credential
custody, tenancy, abuse controls, and operating costs outside v0.1.

## Scope

v0.1 covers initialization, owned games with API app info and playtime, planning,
sync, account binding, explicit migrations, automation, packaging, and tests.
Storefront tags/reviews/genres, AI research, annotation writers, OAuth hosting,
and automatic chat-triggered execution are follow-on work. Store enrichment
should have a separate refresh lifecycle and must not be mistaken for ownership.

## Upstream references

* [Steam IPlayerService](https://partner.steamgames.com/doc/webapi/IPlayerService)
* [Steam Web API overview](https://partner.steamgames.com/doc/webapi_overview)
* [Sheets atomic batch requests](https://developers.google.com/workspace/sheets/api/guides/batch)
* [GitHub reusable automation](https://docs.github.com/en/actions/how-tos/reuse-automations)
