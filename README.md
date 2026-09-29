# Steam Library DB

[![CI](https://github.com/philipguin/steam-lib-db/actions/workflows/test.yml/badge.svg)](https://github.com/philipguin/steam-lib-db/actions/workflows/test.yml)

Keep your Steam library current in Google Sheets, while your ratings, notes, and
research stay yours. A small Python CLI and reusable GitHub Action; no hosted
service, database server, or fork required.

**v0.1.0:** owned games, app names/icons, playtime, presence tracking, dry runs,
account binding, explicit schema migrations, and Google Sheets storage.
Storefront enrichment and AI annotation writers are future work.

## How the sheet works

| Tab | Owned by | Purpose |
| --- | --- | --- |
| `Steam` | Synchronizer | One row per AppID; fresh API data and observation times |
| `Annotations` | You / your research tools | One row per `(appid, field)` with value and provenance |
| `_Meta` | Tool | Schema version, account binding, revision, and last successful sync |

Steam synchronization **never writes annotations or deletes missing games**.
Missing games get `present=false`; returning games become present again. A
private, malformed, or incomplete API response aborts before any write. An
explicit empty library needs `--allow-empty`. One sheet binds to one Steam account.

Personal preferences and research share `Annotations` because the synchronizer
must preserve both. You can add fields such as `rating`, `status`, or
`japanese_dialogue_replay` without changing the schema. See the
[design rationale](docs/architecture.md) and [schema](docs/schema.md).

## Start here

1. [Prepare a Google Sheet and credentials](docs/google-sheets.md).
2. Choose [browser-only GitHub Actions setup](docs/deployment.md#github-actions-no-fork-no-local-install)
   or the local CLI below.
3. Initialize once, review a dry run, then sync.

The browser-only path uses your own tiny deployment repository (or an existing
one) with a workflow calling this project's Action. No fork or local installation
is required. Credentials live in your deployment secrets, never in this public
repository. It still requires Google and Steam authorization.

### Local CLI

Requires Python 3.10+. Install from the repository root:

```console
python -m pip install .
steam-library --help
```

Or install a wheel from a published GitHub release with `python -m pip install
<wheel-path>`. This project does not currently claim a PyPI release.

Set these environment variables in your shell or secret manager:

| Variable | Purpose |
| --- | --- |
| `GOOGLE_SHEET_ID` | ID between `/d/` and `/edit` in your sheet URL |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to a service-account JSON file outside this checkout |
| `STEAM_ID` | Your 17-digit SteamID64 (not your profile name) |
| `STEAM_API_KEY` | Your Steam Web API key |

`GOOGLE_CREDENTIALS_JSON` can supply JSON directly for CI; it takes precedence
over file/ADC credentials. `.env` files are **not** automatically loaded.

```console
steam-library init
steam-library sync --dry-run
steam-library sync
steam-library status
```

`init` is safe to repeat on a valid initialized sheet. `migrate` previews changes;
`migrate --apply` creates in-sheet backups and commits the migration atomically.
All commands use exit code 0 for success, 2 for expected validation/access errors.
Invalid CLI arguments also return 2. Output contains counts, not game names or IDs.

## What safety means here

* Separate tabs and a narrow storage interface enforce annotation ownership.
* Steam updates and success metadata use one atomic Google Sheets batch.
* Schema drift, duplicate AppIDs, replaced tabs, and account mismatch fail closed.
* Literal cell values prevent API-provided names from becoming formulas.
* Only reads are retried; ambiguous write failures tell you to check status.
* A pre-write check catches observed concurrent edits, but Sheets has no
  compare-and-swap guarantee. **Use one writer per spreadsheet.** The example
  workflow serializes runs; do not run a second scheduler against the same sheet.

The Google credential can access all tabs: ownership isolation is enforced by
code, not separate Google permissions. Edit annotations freely; leave `Steam`
and `_Meta` to the tool. `present` describes the last accepted API response, not
definitive ownership. Played free games are included; Steam API coverage may
differ from the client library. v0.1 refuses atomic payloads over 1.8 MB rather
than splitting one sync across non-atomic requests.

## Development

```console
python -m pip install -e ".[dev]"
python -m pytest --cov=steam_library --cov-report=term-missing
python -m ruff check .
python -m ruff format --check .
python -m build
```

Tests use synthetic games and fake HTTP; they require no accounts or secrets.
The initial implementation has not been exercised against a live, credentialed
Steam/Google Sheets deployment; use a disposable sheet for your first run.
See [contributing](CONTRIBUTING.md), [operations](docs/operations.md),
[deployment](docs/deployment.md), and [release checklist](docs/releases.md).
Licensed under [MIT](LICENSE). Not affiliated with Valve or Google.
