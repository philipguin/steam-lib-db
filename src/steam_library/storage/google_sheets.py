import hashlib
import json
import os
import secrets
import uuid

import google.auth
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

from .. import __version__
from ..errors import LibraryError
from ..http import request_json
from ..schema import (
    ANNOTATION_COLUMNS,
    META_COLUMNS,
    STEAM_COLUMNS,
    State,
    parse_meta,
    parse_rows,
)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
TITLES = ("Steam", "Annotations", "_Meta")


def authorized_session():
    try:
        raw = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        if raw:
            credentials = service_account.Credentials.from_service_account_info(
                json.loads(raw),
                scopes=SCOPES,
            )
        else:
            credentials, _ = google.auth.default(scopes=SCOPES)
        return AuthorizedSession(credentials)
    except Exception:
        raise LibraryError(
            "Google credentials could not be loaded. Set GOOGLE_APPLICATION_CREDENTIALS "
            "to a service-account JSON file, GOOGLE_CREDENTIALS_JSON, or configure ADC."
        ) from None


def cell(value):
    if type(value) is bool:
        return {"userEnteredValue": {"boolValue": value}}
    if type(value) is int:
        return {"userEnteredValue": {"numberValue": value}}
    return {"userEnteredValue": {"stringValue": str(value)}}


def update_cells(sheet_id, rows):
    # Typed values prevent formula injection and preserve SteamID64 strings.
    return {
        "updateCells": {
            "start": {"sheetId": sheet_id, "rowIndex": 0, "columnIndex": 0},
            "rows": [{"values": [cell(value) for value in row]} for row in rows],
            "fields": "userEnteredValue",
        }
    }


def meta_rows(meta):
    return [list(META_COLUMNS)] + [[key, value] for key, value in sorted(meta.items())]


def game_rows(games):
    return [list(STEAM_COLUMNS)] + [[game[key] for key in STEAM_COLUMNS] for game in games]


class GoogleSheetsStore:
    def __init__(self, spreadsheet_id: str, session=None):
        self.session = session if session is not None else authorized_session()
        self.url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"

    def _get(self, suffix="", **kwargs):
        return request_json(
            self.session, "GET", self.url + suffix, service="Google Sheets", **kwargs
        )

    def _batch(self, requests):
        body = {"requests": requests}
        if len(json.dumps(body).encode("utf-8")) > 1_800_000:
            raise LibraryError(
                "Atomic update exceeds the v0.1 size budget (1.8 MB); no writes made."
            )
        request_json(
            self.session, "POST", self.url + ":batchUpdate", service="Google Sheets", json=body
        )

    def _properties(self):
        result = self._get(params={"fields": "sheets(properties)"})
        try:
            return {sheet["properties"]["title"]: sheet["properties"] for sheet in result["sheets"]}
        except (KeyError, TypeError):
            raise LibraryError("Google Sheets returned invalid tab metadata.") from None

    def read(self) -> State:
        props = self._properties()
        if not all(title in props for title in TITLES):
            raise LibraryError(
                "Required tabs are missing. Run 'steam-library init' on a fresh sheet."
            )
        result = self._get(
            "/values:batchGet",
            params={
                "ranges": ["'Steam'", "'_Meta'"],
                "valueRenderOption": "FORMULA",
            },
        )
        try:
            ranges = result["valueRanges"]
            steam_rows, metadata_rows = (r.get("values", []) for r in ranges)
        except (KeyError, TypeError, ValueError):
            raise LibraryError("Google Sheets returned invalid cell data.") from None
        meta = parse_meta(metadata_rows)
        for title, key in (
            ("Steam", "steam_sheet_id"),
            ("Annotations", "annotations_sheet_id"),
            ("_Meta", "meta_sheet_id"),
        ):
            if meta[key] != str(props[title]["sheetId"]):
                raise LibraryError("A managed tab was replaced or renamed; no writes made.")
        games = parse_rows(steam_rows, int(meta["schema_version"]))
        canonical = json.dumps(
            [steam_rows, metadata_rows, [props[t]["sheetId"] for t in TITLES]],
            sort_keys=True,
            separators=(",", ":"),
        )
        fingerprint = hashlib.sha256(canonical.encode()).hexdigest()
        return State(games, meta, fingerprint)

    def initialize(self):
        props = self._properties()
        occupied = set(props) & set(TITLES)
        if occupied:
            if occupied == set(TITLES):
                state = self.read()
                if state.meta["schema_version"] != "1":
                    raise LibraryError("An older schema exists; run 'steam-library migrate'.")
                return False
            raise LibraryError("Reserved tab names already exist. Use a fresh spreadsheet.")
        used = {p["sheetId"] for p in props.values()}
        ids = {}
        for title in TITLES:
            candidate = secrets.randbelow(2_000_000_000)
            while candidate in used:
                candidate = secrets.randbelow(2_000_000_000)
            used.add(candidate)
            ids[title] = candidate
        meta = {
            "schema_version": "1",
            "steam_sheet_id": str(ids["Steam"]),
            "annotations_sheet_id": str(ids["Annotations"]),
            "meta_sheet_id": str(ids["_Meta"]),
            "steam_id": "",
            "revision": "0",
            "last_successful_sync": "",
            "tool_version": __version__,
        }
        requests = []
        for title, columns in (
            ("Steam", STEAM_COLUMNS),
            ("Annotations", ANNOTATION_COLUMNS),
            ("_Meta", META_COLUMNS),
        ):
            sheet_id = ids[title]
            requests.append(
                {
                    "addSheet": {
                        "properties": {
                            "sheetId": sheet_id,
                            "title": title,
                            "gridProperties": {
                                "rowCount": 1000,
                                "columnCount": len(columns),
                                "frozenRowCount": 1,
                            },
                        }
                    }
                }
            )
            requests.append(
                update_cells(sheet_id, meta_rows(meta) if title == "_Meta" else [columns])
            )
            requests.append(
                {
                    "repeatCell": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {"red": 0.12, "green": 0.20, "blue": 0.30},
                                "textFormat": {
                                    "bold": True,
                                    "foregroundColor": {
                                        "red": 1,
                                        "green": 1,
                                        "blue": 1,
                                    },
                                },
                            }
                        },
                        "fields": "userEnteredFormat",
                    }
                }
            )
            if title != "_Meta":
                requests.append({"setBasicFilter": {"filter": {"range": {"sheetId": sheet_id}}}})
            if title != "Annotations":
                requests.append(
                    {
                        "addProtectedRange": {
                            "protectedRange": {
                                "range": {"sheetId": sheet_id},
                                "warningOnly": True,
                                "description": "Managed data. Put notes in Annotations.",
                            }
                        }
                    }
                )
        self._batch(requests)
        return True

    def _check_unchanged(self, before):
        if self.read().fingerprint != before.fingerprint:
            raise LibraryError(
                "Steam data or metadata changed during the run. Retry with one writer."
            )

    def _write_requests(self, before, games, meta):
        steam_id = int(before.meta["steam_sheet_id"])
        meta_id = int(before.meta["meta_sheet_id"])
        props = self._properties()
        requests = []
        for title, count, width in (
            ("Steam", len(games) + 1, len(STEAM_COLUMNS)),
            ("_Meta", len(meta) + 1, 2),
        ):
            grid = props[title]["gridProperties"]
            for dimension, current, needed in (
                ("ROWS", grid["rowCount"], count),
                ("COLUMNS", grid["columnCount"], width),
            ):
                if needed > current:
                    requests.append(
                        {
                            "appendDimension": {
                                "sheetId": props[title]["sheetId"],
                                "dimension": dimension,
                                "length": needed - current,
                            }
                        }
                    )
        requests.extend(
            [update_cells(steam_id, game_rows(games)), update_cells(meta_id, meta_rows(meta))]
        )
        return requests

    def commit(self, before, games, meta):
        if before.meta["schema_version"] != "1" or meta["schema_version"] != "1":
            raise LibraryError("Schema changes require an explicit migration.")
        # Defense in depth: synchronization cannot remove/reorder records or retarget tabs.
        if [r["appid"] for r in games[: len(before.games)]] != [r["appid"] for r in before.games]:
            raise LibraryError("Refusing a sync that deletes or reorders stored AppIDs.")
        for key in ("steam_sheet_id", "annotations_sheet_id", "meta_sheet_id"):
            if before.meta[key] != meta[key]:
                raise LibraryError("Refusing a sync that changes tab ownership.")
        parse_rows(game_rows(games))
        requests = self._write_requests(before, games, meta)
        self._check_unchanged(before)
        self._batch(requests)

    def migrate(self, *, apply=False):
        before = self.read()
        if before.meta["schema_version"] == "1":
            return "Schema v1 is current; no migration needed."
        description = (
            "v0 -> v1: back up Steam and _Meta; append last_seen_at, using "
            "last_synced_at for present games and blank for absent games. Annotations untouched."
        )
        if not apply:
            return description + " Re-run with --apply to commit."
        games = tuple(
            dict(row, last_seen_at=row["last_synced_at"] if row["present"] else "")
            for row in before.games
        )
        meta = dict(
            before.meta,
            schema_version="1",
            tool_version=__version__,
            revision=str(int(before.meta["revision"]) + 1),
        )
        suffix = uuid.uuid4().hex[:12]
        requests = [
            {
                "duplicateSheet": {
                    "sourceSheetId": int(before.meta[key]),
                    "newSheetName": f"_backup_v0_{title}_{suffix}",
                }
            }
            for title, key in (("Steam", "steam_sheet_id"), ("Meta", "meta_sheet_id"))
        ]
        requests.extend(self._write_requests(before, games, meta))
        self._check_unchanged(before)
        self._batch(requests)
        return description + " Migration committed; backups retained in the spreadsheet."
