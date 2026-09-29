from dataclasses import dataclass

from .errors import LibraryError

SCHEMA_VERSION = 1
STEAM_COLUMNS = (
    "appid",
    "name",
    "playtime_forever",
    "playtime_2weeks",
    "rtime_last_played",
    "img_icon_url",
    "present",
    "first_seen_at",
    "last_synced_at",
    "last_seen_at",
)
LEGACY_COLUMNS = STEAM_COLUMNS[:-1]
ANNOTATION_COLUMNS = (
    "appid",
    "field",
    "value",
    "provenance",
    "source_url",
    "updated_at",
    "confidence",
    "notes",
)
META_COLUMNS = ("key", "value")
REQUIRED_META = {
    "schema_version",
    "steam_sheet_id",
    "annotations_sheet_id",
    "meta_sheet_id",
    "steam_id",
    "revision",
    "last_successful_sync",
    "tool_version",
}


@dataclass(frozen=True)
class State:
    games: tuple[dict, ...]
    meta: dict[str, str]
    fingerprint: str


def parse_meta(rows) -> dict[str, str]:
    if not rows or tuple(rows[0]) != META_COLUMNS:
        raise LibraryError("Unexpected _Meta header; no writes made.")
    meta = {}
    for row in rows[1:]:
        if not row or len(row) > 2 or not isinstance(row[0], str) or row[0] in meta:
            raise LibraryError("Invalid or duplicate metadata keys; no writes made.")
        meta[row[0]] = str(row[1]) if len(row) == 2 else ""
    if not REQUIRED_META.issubset(meta):
        raise LibraryError("Required metadata is missing; no writes made.")
    if meta["schema_version"] not in {"0", "1"}:
        raise LibraryError("Unsupported schema version. Upgrade the tool before proceeding.")
    if not meta["revision"].isascii() or not meta["revision"].isdigit():
        raise LibraryError("Invalid metadata revision; no writes made.")
    return meta


def parse_rows(rows, version=SCHEMA_VERSION) -> tuple[dict, ...]:
    columns = STEAM_COLUMNS if version == 1 else LEGACY_COLUMNS
    if not rows or tuple(rows[0]) != columns:
        raise LibraryError("Unexpected Steam columns. Restore the schema before syncing.")
    result = []
    seen = set()
    for row in rows[1:]:
        if not row or len(row) > len(columns):
            raise LibraryError("Blank or oversized Steam row; no writes made.")
        item = dict(zip(columns, list(row) + [""] * (len(columns) - len(row)), strict=True))
        for field in ("appid", "playtime_forever", "playtime_2weeks", "rtime_last_played"):
            value = str(item[field])
            if not value.isascii() or not value.isdigit():
                raise LibraryError("Invalid Steam numeric cell; no writes made.")
            item[field] = int(value)
        if item["appid"] <= 0 or item["appid"] in seen:
            raise LibraryError("Invalid or duplicate stored AppID; no writes made.")
        seen.add(item["appid"])
        if type(item["present"]) is not bool and item["present"] not in ("TRUE", "FALSE"):
            raise LibraryError("Invalid presence cell; no writes made.")
        item["present"] = item["present"] is True or item["present"] == "TRUE"
        for field in set(columns) - {
            "appid",
            "playtime_forever",
            "playtime_2weeks",
            "rtime_last_played",
            "present",
        }:
            if (
                not isinstance(item[field], str)
                or item[field].startswith("=")
                and field.endswith("_at")
            ):
                raise LibraryError("Invalid Steam text cell; no writes made.")
        result.append(item)
    return tuple(result)
