import copy

import pytest

from steam_library.errors import LibraryError
from steam_library.steam import Game
from steam_library.sync import synchronize

ACCOUNT = "76561190000000000"  # Synthetic; never used against a real API.


class Client:
    def __init__(self, *games):
        self.games = games

    def owned_games(self):
        return self.games


def test_lifecycle_retains_missing_restores_and_preserves_annotations(sheets):
    store, session = sheets
    annotations = copy.deepcopy(session.tabs[2])
    dashboard = copy.deepcopy(session.tabs[99])
    first = synchronize(store, Client(Game(20, "Twenty", 12), Game(10, "Ten", 4)), ACCOUNT)
    assert first.added == 2
    assert [g["appid"] for g in store.read().games] == [10, 20]
    seen = store.read().games[1]["last_seen_at"]
    second = synchronize(store, Client(Game(10, "Renamed", 50)), ACCOUNT)
    assert (second.updated, second.missing) == (1, 1)
    absent = store.read().games[1]
    assert absent["present"] is False
    assert absent["name"] == "Twenty" and absent["last_seen_at"] == seen
    third = synchronize(store, Client(Game(20, "", 12), Game(10, "Renamed", 50)), ACCOUNT)
    assert (third.restored, third.unchanged) == (1, 1)
    assert store.read().games[1]["name"] == "Twenty"
    assert session.tabs[2] == annotations and session.tabs[99] == dashboard
    assert store.read().meta["revision"] == "3"
    assert store.read().meta["steam_id"] == ACCOUNT
    for _, _, kwargs in session.writes:
        for request in kwargs["json"]["requests"]:
            if "updateCells" in request:
                assert request["updateCells"]["start"]["sheetId"] in {1, 3}


def test_dry_run_has_no_writes_or_account_binding(sheets):
    store, session = sheets
    before = copy.deepcopy(session.tabs)
    plan = synchronize(store, Client(Game(10, "Ten", 0)), ACCOUNT, dry_run=True)
    assert plan.added == 1
    assert session.tabs == before and not session.writes


def test_empty_snapshot_requires_explicit_override(sheets):
    store, session = sheets
    synchronize(store, Client(Game(10, "Ten", 0)), ACCOUNT)
    before = copy.deepcopy(session.tabs)
    with pytest.raises(LibraryError, match="zero games"):
        synchronize(store, Client(), ACCOUNT)
    assert session.tabs == before
    synchronize(store, Client(), ACCOUNT, allow_empty=True)
    assert len(store.read().games) == 1 and not store.read().games[0]["present"]


def test_account_mismatch_aborts_before_api_call(sheets):
    store, session = sheets
    synchronize(store, Client(Game(10, "Ten", 0)), ACCOUNT)

    class MustNotFetch:
        def owned_games(self):
            raise AssertionError("Should fail before calling Steam")

    with pytest.raises(LibraryError, match="different Steam account"):
        synchronize(store, MustNotFetch(), "76561190000000001")
    assert len(session.writes) == 1


def test_api_failure_does_not_mark_missing_or_advance_metadata(sheets):
    store, session = sheets
    synchronize(store, Client(Game(10, "Ten", 0)), ACCOUNT)
    before = copy.deepcopy(session.tabs)

    class Broken:
        def owned_games(self):
            raise LibraryError("Steam unavailable")

    with pytest.raises(LibraryError):
        synchronize(store, Broken(), ACCOUNT)
    assert session.tabs == before


def test_concurrent_mutation_is_detected(sheets):
    store, session = sheets

    class Concurrent:
        def owned_games(self):
            for row in session.tabs[3]["rows"]:
                if row[0] == "revision":
                    row[1] = "1"
            return (Game(10, "Ten", 0),)

    with pytest.raises(LibraryError, match="changed during"):
        synchronize(store, Concurrent(), ACCOUNT)
    assert not session.writes


def test_literal_formula_name_and_failure_do_not_retry_write(sheets):
    store, session = sheets
    synchronize(store, Client(Game(10, '=HYPERLINK("bad")', 0)), ACCOUNT)
    update = session.writes[0][2]["json"]["requests"][0]["updateCells"]
    assert update["rows"][1]["values"][1]["userEnteredValue"] == {
        "stringValue": '=HYPERLINK("bad")',
    }
    before = copy.deepcopy(session.tabs)
    session.fail_write = True
    with pytest.raises(LibraryError, match="503"):
        synchronize(store, Client(Game(10, "Changed", 99)), ACCOUNT)
    assert session.tabs == before
    assert len(session.writes) == 2
