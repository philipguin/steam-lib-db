from dataclasses import dataclass

import requests

from .errors import LibraryError
from .http import request_json


@dataclass(frozen=True)
class Game:
    appid: int
    name: str
    playtime_forever: int
    playtime_2weeks: int = 0
    rtime_last_played: int = 0
    img_icon_url: str = ""


def integer(value, *, positive=False):
    if type(value) is not int or value < (1 if positive else 0):
        raise LibraryError("Steam returned an invalid numeric field; sync aborted.")
    return value


def parse_owned_games(payload) -> tuple[Game, ...]:
    if not isinstance(payload, dict) or not isinstance(payload.get("response"), dict):
        raise LibraryError("Steam returned an invalid response; sync aborted.")
    response = payload["response"]
    if "game_count" not in response:
        raise LibraryError(
            "Steam library is unavailable. Check game-details privacy and API access."
        )
    count = integer(response["game_count"])
    rows = response.get("games", [] if count == 0 else None)
    if not isinstance(rows, list) or len(rows) != count:
        raise LibraryError("Steam game count does not match the response; sync aborted.")
    games = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise LibraryError("Steam returned an invalid game; sync aborted.")
        appid = integer(row.get("appid"), positive=True)
        if appid in seen:
            raise LibraryError("Steam returned duplicate AppIDs; sync aborted.")
        seen.add(appid)
        name = row.get("name", "")
        icon = row.get("img_icon_url", "")
        if not isinstance(name, str) or not isinstance(icon, str):
            raise LibraryError("Steam returned invalid app info; sync aborted.")
        games.append(
            Game(
                appid,
                name,
                integer(row.get("playtime_forever")),
                integer(row.get("playtime_2weeks", 0)),
                integer(row.get("rtime_last_played", 0)),
                icon,
            )
        )
    return tuple(games)


class SteamClient:
    def __init__(self, api_key: str, steam_id: str, session=None):
        self.api_key = api_key
        self.steam_id = steam_id
        self.session = session or requests.Session()

    def owned_games(self) -> tuple[Game, ...]:
        payload = request_json(
            self.session,
            "GET",
            "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/",
            service="Steam",
            params={
                "key": self.api_key,
                "steamid": self.steam_id,
                "include_appinfo": "1",
                "include_played_free_games": "1",
                "format": "json",
            },
        )
        return parse_owned_games(payload)
