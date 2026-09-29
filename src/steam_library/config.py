import os
import re
from dataclasses import dataclass, field

from .errors import LibraryError


@dataclass(frozen=True)
class Config:
    spreadsheet_id: str
    steam_id: str = ""
    steam_api_key: str = field(default="", repr=False)

    @classmethod
    def from_env(cls, *, steam: bool = False) -> "Config":
        sheet = os.environ.get("GOOGLE_SHEET_ID", "").strip()
        steam_id = os.environ.get("STEAM_ID", "").strip()
        key = os.environ.get("STEAM_API_KEY", "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]+", sheet):
            raise LibraryError("Set GOOGLE_SHEET_ID to the ID in your spreadsheet URL.")
        if steam and (not re.fullmatch(r"[0-9]{17}", steam_id) or not key):
            raise LibraryError("Set STEAM_ID to a 17-digit SteamID64 and STEAM_API_KEY.")
        return cls(sheet, steam_id, key)
