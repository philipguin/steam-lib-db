from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from . import __version__
from .errors import LibraryError
from .schema import SCHEMA_VERSION, State
from .steam import Game
from .storage.base import SteamStore


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class Plan:
    games: tuple[dict, ...]
    added: int
    updated: int
    missing: int
    restored: int
    unchanged: int

    def summary(self):
        return {key: value for key, value in asdict(self).items() if key != "games"}


def plan_sync(state: State, incoming: tuple[Game, ...], now: str, *, allow_empty=False) -> Plan:
    if not incoming and not allow_empty:
        raise LibraryError(
            "Steam reports zero games. Review privacy; use --allow-empty if intentional."
        )
    by_id = {game.appid: game for game in incoming}
    if len(by_id) != len(incoming):
        raise LibraryError("Duplicate incoming AppIDs; sync aborted.")
    output = []
    added = updated = missing = restored = unchanged = 0
    for old in state.games:
        row = dict(old)
        game = by_id.pop(old["appid"], None)
        if game is None:
            missing += int(old["present"])
            unchanged += int(not old["present"])
            row["present"] = False
        else:
            values = asdict(game)
            # Missing app info can occur for delisted titles; preserve what we know.
            values["name"] = game.name or old["name"]
            values["img_icon_url"] = game.img_icon_url or old["img_icon_url"]
            changed = any(old[key] != value for key, value in values.items())
            restored += int(not old["present"])
            updated += int(old["present"] and changed)
            unchanged += int(old["present"] and not changed)
            row.update(values, present=True, last_seen_at=now)
        row["last_synced_at"] = now
        output.append(row)
    for appid in sorted(by_id):
        output.append(
            dict(
                asdict(by_id[appid]),
                present=True,
                first_seen_at=now,
                last_seen_at=now,
                last_synced_at=now,
            )
        )
        added += 1
    return Plan(tuple(output), added, updated, missing, restored, unchanged)


def synchronize(store: SteamStore, client, steam_id: str, *, dry_run=False, allow_empty=False):
    state = store.read()
    if state.meta["schema_version"] != str(SCHEMA_VERSION):
        raise LibraryError("Run 'steam-library migrate' to review the required migration.")
    if state.meta["steam_id"] not in ("", steam_id):
        raise LibraryError(
            "This spreadsheet belongs to a different Steam account; use another sheet."
        )
    now = utc_now()
    plan = plan_sync(state, client.owned_games(), now, allow_empty=allow_empty)
    if not dry_run:
        meta = dict(
            state.meta,
            steam_id=steam_id,
            last_successful_sync=now,
            revision=str(int(state.meta["revision"]) + 1),
            tool_version=__version__,
        )
        store.commit(state, plan.games, meta)
    return plan
