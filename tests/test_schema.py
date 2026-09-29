import pytest

from steam_library.errors import LibraryError
from steam_library.schema import STEAM_COLUMNS, parse_meta, parse_rows


@pytest.mark.parametrize("presence", [1, 0, "yes", "", None])
def test_presence_must_be_boolean(presence):
    row = [10, "Ten", 0, 0, 0, "", presence, "", "", ""]
    with pytest.raises(LibraryError, match="presence"):
        parse_rows([STEAM_COLUMNS, row])


@pytest.mark.parametrize(
    "rows",
    [
        [],
        [["wrong"]],
        [["key", "value"], ["x", "a"], ["x", "b"]],
        [["key", "value"], []],
        [["key", "value"], ["key", "value"]],
    ],
)
def test_malformed_metadata_is_rejected(rows):
    with pytest.raises(LibraryError):
        parse_meta(rows)
