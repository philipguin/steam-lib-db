import pytest
import requests
from conftest import Response

from steam_library.errors import LibraryError
from steam_library.steam import SteamClient, parse_owned_games


def payload(games):
    return {"response": {"game_count": len(games), "games": games}}


def test_parse_optional_fields_and_literal_name():
    games = parse_owned_games(payload([{"appid": 10, "name": "=literal", "playtime_forever": 42}]))
    assert games[0].name == "=literal"
    assert games[0].playtime_2weeks == 0
    assert parse_owned_games({"response": {"game_count": 0}}) == ()


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"response": {}},
        {"response": None},
        [],
        {"response": {"game_count": 2, "games": []}},
        {"response": {"game_count": True}},
        payload([{"appid": 0, "playtime_forever": 0}]),
        payload([{"appid": 10, "playtime_forever": -1}]),
        payload([{"appid": 10, "playtime_forever": 1.5}]),
        payload([{"appid": 10}]),
        payload([None]),
        payload([{"appid": 10, "name": 123, "playtime_forever": 0}]),
        payload([{"appid": 10, "playtime_forever": 0}] * 2),
    ],
)
def test_rejects_ambiguous_or_invalid_snapshot(data):
    with pytest.raises(LibraryError):
        parse_owned_games(data)


def test_client_includes_free_games_and_redacts_failure(monkeypatch):
    calls = []

    class Session:
        def request(self, method, url, **kwargs):
            calls.append(kwargs)
            return Response({}, 401)

    with pytest.raises(LibraryError) as caught:
        SteamClient("SECRET_API_KEY", "76561190000000000", Session()).owned_games()
    assert "SECRET_API_KEY" not in str(caught.value)
    assert calls[0]["params"]["include_played_free_games"] == "1"
    assert calls[0]["params"]["include_appinfo"] == "1"
    assert calls[0]["timeout"] == (10, 60)


def test_transient_reads_retry_and_network_errors_are_redacted(monkeypatch):
    monkeypatch.setattr("steam_library.http.time.sleep", lambda _: None)
    count = 0

    class Session:
        def request(self, *args, **kwargs):
            nonlocal count
            count += 1
            if count < 3:
                return Response({}, 429)
            return Response(payload([]))

    assert SteamClient("key", "id", Session()).owned_games() == ()
    assert count == 3

    class Broken:
        def request(self, *args, **kwargs):
            raise requests.ConnectionError("https://example.invalid?key=SECRET")

    with pytest.raises(LibraryError) as caught:
        SteamClient("key", "id", Broken()).owned_games()
    assert "SECRET" not in str(caught.value)
