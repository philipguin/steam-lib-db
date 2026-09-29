import argparse
import json
import sys

from . import __version__
from .config import Config
from .errors import LibraryError
from .steam import SteamClient
from .storage.google_sheets import GoogleSheetsStore
from .sync import synchronize


def parser():
    root = argparse.ArgumentParser(
        prog="steam-library",
        description="Sync Steam to Google Sheets while preserving annotations.",
    )
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("init", help="Create schema v1 tabs; safe to repeat")
    commands.add_parser("status", help="Validate schema and report counts; no Steam API call")
    sync = commands.add_parser("sync", help="Fetch, validate, and merge Steam games")
    sync.add_argument("--dry-run", action="store_true", help="Read and plan without writing")
    sync.add_argument(
        "--allow-empty", action="store_true", help="Accept an explicit zero-game response"
    )
    migrate = commands.add_parser(
        "migrate", help="Review a schema migration (no writes by default)"
    )
    migrate.add_argument("--apply", action="store_true", help="Back up and atomically migrate")
    return root


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        config = Config.from_env(steam=args.command == "sync")
        store = GoogleSheetsStore(config.spreadsheet_id)
        if args.command == "init":
            print("Created schema v1." if store.initialize() else "Schema v1 already initialized.")
        elif args.command == "status":
            state = store.read()
            print(
                json.dumps(
                    {
                        "schema_version": int(state.meta["schema_version"]),
                        "games": len(state.games),
                        "present": sum(row["present"] for row in state.games),
                        "account_bound": bool(state.meta["steam_id"]),
                        "last_successful_sync": state.meta["last_successful_sync"],
                        "revision": int(state.meta["revision"]),
                    },
                    indent=2,
                )
            )
        elif args.command == "migrate":
            print(store.migrate(apply=args.apply))
        else:
            client = SteamClient(config.steam_api_key, config.steam_id)
            plan = synchronize(
                store, client, config.steam_id, dry_run=args.dry_run, allow_empty=args.allow_empty
            )
            print(json.dumps({"dry_run": args.dry_run, **plan.summary()}, indent=2))
        return 0
    except LibraryError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
