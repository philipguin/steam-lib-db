import json

import pytest

from steam_library.cli import main
from steam_library.config import Config
from steam_library.errors import LibraryError
from steam_library.storage.google_sheets import authorized_session


def test_help_and_version_work_without_credentials(capsys):
    with pytest.raises(SystemExit) as caught:
        main(["--version"])
    assert caught.value.code == 0
    assert "0.1.0" in capsys.readouterr().out


def test_missing_configuration_returns_safe_error(monkeypatch, capsys):
    monkeypatch.delenv("GOOGLE_SHEET_ID", raising=False)
    assert main(["sync"]) == 2
    assert "GOOGLE_SHEET_ID" in capsys.readouterr().err


def test_steam_config_validation(monkeypatch):
    monkeypatch.setenv("GOOGLE_SHEET_ID", "synthetic-sheet")
    monkeypatch.setenv("STEAM_ID", "not-a-steamid")
    monkeypatch.setenv("STEAM_API_KEY", "SECRET")
    with pytest.raises(LibraryError):
        Config.from_env(steam=True)
    assert "SECRET" not in repr(Config.from_env())


def test_invalid_credentials_are_redacted(monkeypatch):
    monkeypatch.setenv("GOOGLE_CREDENTIALS_JSON", "SECRET_INVALID_JSON")
    with pytest.raises(LibraryError) as caught:
        authorized_session()
    assert "SECRET_INVALID_JSON" not in str(caught.value)


def test_status_init_and_migrate_cli(sheets, monkeypatch, capsys):
    store, _ = sheets
    monkeypatch.setenv("GOOGLE_SHEET_ID", "synthetic-sheet")
    monkeypatch.setattr("steam_library.cli.GoogleSheetsStore", lambda _: store)
    assert main(["status"]) == 0
    assert json.loads(capsys.readouterr().out)["games"] == 0
    assert main(["init"]) == 0
    assert "already" in capsys.readouterr().out
    assert main(["migrate"]) == 0
    assert "current" in capsys.readouterr().out


def test_sync_cli_defaults_to_write_and_dry_run_is_explicit(sheets, monkeypatch, capsys):
    from test_sync import ACCOUNT, Client

    from steam_library.steam import Game

    store, session = sheets
    monkeypatch.setenv("GOOGLE_SHEET_ID", "synthetic-sheet")
    monkeypatch.setenv("STEAM_ID", ACCOUNT)
    monkeypatch.setenv("STEAM_API_KEY", "synthetic-key")
    monkeypatch.setattr("steam_library.cli.GoogleSheetsStore", lambda _: store)
    monkeypatch.setattr("steam_library.cli.SteamClient", lambda *_: Client(Game(10, "Ten", 0)))
    assert main(["sync", "--dry-run"]) == 0
    assert json.loads(capsys.readouterr().out)["dry_run"] is True
    assert not session.writes
    assert main(["sync"]) == 0
    assert json.loads(capsys.readouterr().out)["added"] == 1
    assert len(session.writes) == 1
