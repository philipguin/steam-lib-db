from typing import Protocol

from ..schema import State


class SteamStore(Protocol):
    """No annotation read/write capability is exposed to the sync engine."""

    def read(self) -> State: ...

    def commit(self, before: State, games: tuple[dict, ...], meta: dict[str, str]) -> None: ...
