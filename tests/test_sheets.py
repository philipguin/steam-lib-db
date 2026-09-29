import copy

import pytest
from conftest import SheetsSession
from test_sync import ACCOUNT, Client

from steam_library.errors import LibraryError
from steam_library.schema import LEGACY_COLUMNS
from steam_library.steam import Game
from steam_library.storage.google_sheets import GoogleSheetsStore
from steam_library.sync import synchronize


def change_meta(session, key, value):
    for row in session.tabs[3]["rows"][1:]:
        if row[0] == key:
            row[1] = value
            return
    raise AssertionError(key)


def test_initialization_is_atomic_and_idempotent():
    session = SheetsSession(initialized=False)
    store = GoogleSheetsStore("synthetic", session)
    original = copy.deepcopy(session.tabs[99])
    assert store.initialize() is True
    assert store.initialize() is False
    assert len(session.writes) == 1
    assert session.tabs[99] == original
    assert store.read().meta["schema_version"] == "1"


def test_initialization_refuses_partial_reserved_tabs(sheets):
    store, session = sheets
    del session.tabs[2]
    with pytest.raises(LibraryError, match="Reserved tab names"):
        store.initialize()
    assert not session.writes


@pytest.mark.parametrize(
    "key,value",
    [
        ("schema_version", "9"),
        ("revision", "bad"),
        ("annotations_sheet_id", "1"),
        ("steam_sheet_id", "99"),
    ],
)
def test_unknown_schema_and_replaced_tabs_fail_closed(sheets, key, value):
    store, session = sheets
    change_meta(session, key, value)
    with pytest.raises(LibraryError):
        store.read()
    assert not session.writes


def test_header_and_duplicate_rows_fail_closed(sheets):
    store, session = sheets
    synchronize(store, Client(Game(10, "Ten", 0)), ACCOUNT)
    session.tabs[1]["rows"].append(copy.deepcopy(session.tabs[1]["rows"][1]))
    with pytest.raises(LibraryError, match="duplicate"):
        store.read()
    session.tabs[1]["rows"].pop()
    session.tabs[1]["rows"][0].append("user_notes")
    with pytest.raises(LibraryError, match="columns"):
        store.read()


def test_migration_preview_backups_and_repeatability(sheets):
    store, session = sheets
    synchronize(store, Client(Game(10, "Ten", 0), Game(20, "Twenty", 0)), ACCOUNT)
    synchronize(store, Client(Game(10, "Ten", 0)), ACCOUNT)
    change_meta(session, "schema_version", "0")
    session.tabs[1]["rows"] = [row[:-1] for row in session.tabs[1]["rows"]]
    assert session.tabs[1]["rows"][0] == list(LEGACY_COLUMNS)
    original = copy.deepcopy(session.tabs)
    writes = len(session.writes)
    assert "v0 -> v1" in store.migrate()
    assert session.tabs == original and len(session.writes) == writes
    with pytest.raises(LibraryError, match="migration"):
        synchronize(store, Client(Game(10, "Ten", 0)), ACCOUNT)
    assert "Migration committed" in store.migrate(apply=True)
    assert len(session.writes) == writes + 1
    assert session.tabs[2] == original[2]
    backups = [
        tab for tab in session.tabs.values() if tab["properties"]["title"].startswith("_backup_v0_")
    ]
    assert len(backups) == 2
    assert any(tab["rows"] == original[1]["rows"] for tab in backups)
    assert any(tab["rows"] == original[3]["rows"] for tab in backups)
    state = store.read()
    assert state.games[0]["last_seen_at"] == state.games[0]["last_synced_at"]
    assert state.games[1]["last_seen_at"] == ""
    assert "current" in store.migrate(apply=True)
    assert len(session.writes) == writes + 1


def test_migration_failure_does_not_advance_version(sheets):
    store, session = sheets
    change_meta(session, "schema_version", "0")
    session.tabs[1]["rows"][0] = list(LEGACY_COLUMNS)
    before = copy.deepcopy(session.tabs)
    session.fail_write = True
    with pytest.raises(LibraryError):
        store.migrate(apply=True)
    assert session.tabs == before
    assert len(session.writes) == 1


def test_grid_expands_and_never_shrinks(sheets):
    store, session = sheets
    session.tabs[1]["properties"]["gridProperties"]["rowCount"] = 1
    synchronize(store, Client(Game(10, "Ten", 0)), ACCOUNT)
    assert session.tabs[1]["properties"]["gridProperties"]["rowCount"] == 2
    synchronize(store, Client(), ACCOUNT, allow_empty=True)
    assert session.tabs[1]["properties"]["gridProperties"]["rowCount"] == 2


def test_oversized_atomic_batch_is_refused(sheets):
    store, session = sheets
    with pytest.raises(LibraryError, match="size budget"):
        store._batch([{"synthetic": "x" * 1_800_001}])
    assert not session.writes


def test_store_defends_against_delete_and_ownership_changes(sheets):
    store, session = sheets
    synchronize(store, Client(Game(10, "Ten", 0)), ACCOUNT)
    state = store.read()
    with pytest.raises(LibraryError, match="deletes"):
        store.commit(state, (), state.meta)
    with pytest.raises(LibraryError, match="ownership"):
        store.commit(state, state.games, dict(state.meta, steam_sheet_id="2"))
