import copy

import pytest

from steam_library.schema import ANNOTATION_COLUMNS, STEAM_COLUMNS
from steam_library.storage.google_sheets import GoogleSheetsStore, meta_rows


class Response:
    def __init__(self, data, status=200):
        self.data, self.status_code = data, status

    def json(self):
        return self.data


class SheetsSession:
    """A synthetic workbook API double, including typed cells and atomic batches."""

    def __init__(self, initialized=True):
        self.calls = []
        self.tabs = {
            99: {
                "properties": {
                    "sheetId": 99,
                    "title": "My dashboard",
                    "gridProperties": {"rowCount": 1000, "columnCount": 26},
                },
                "rows": [["untouched"]],
            }
        }
        self.fail_write = False
        if initialized:
            for title, sheet_id, rows in (
                ("Steam", 1, [list(STEAM_COLUMNS)]),
                (
                    "Annotations",
                    2,
                    [
                        list(ANNOTATION_COLUMNS),
                        [10, "rating", "9", "manual", "", "", "", "keep me"],
                    ],
                ),
                (
                    "_Meta",
                    3,
                    meta_rows(
                        {
                            "schema_version": "1",
                            "steam_sheet_id": "1",
                            "annotations_sheet_id": "2",
                            "meta_sheet_id": "3",
                            "steam_id": "",
                            "revision": "0",
                            "last_successful_sync": "",
                            "tool_version": "0.1.0",
                        }
                    ),
                ),
            ):
                self.tabs[sheet_id] = {
                    "properties": {
                        "sheetId": sheet_id,
                        "title": title,
                        "gridProperties": {"rowCount": 1000, "columnCount": len(rows[0])},
                    },
                    "rows": rows,
                }

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if method == "GET" and url.endswith("/values:batchGet"):
            by_name = {tab["properties"]["title"]: tab for tab in self.tabs.values()}
            return Response(
                {
                    "valueRanges": [
                        {"values": copy.deepcopy(by_name[name.strip("'")]["rows"])}
                        for name in kwargs["params"]["ranges"]
                    ]
                }
            )
        if method == "GET":
            return Response(
                {
                    "sheets": [
                        {"properties": copy.deepcopy(tab["properties"])}
                        for tab in self.tabs.values()
                    ]
                }
            )
        if self.fail_write:
            return Response({}, 503)
        staged = copy.deepcopy(self.tabs)
        for request in kwargs["json"]["requests"]:
            if "addSheet" in request:
                prop = request["addSheet"]["properties"]
                staged[prop["sheetId"]] = {"properties": prop, "rows": []}
            elif "updateCells" in request:
                update = request["updateCells"]
                rows = [
                    [next(iter(cell["userEnteredValue"].values())) for cell in row["values"]]
                    for row in update["rows"]
                ]
                target = staged[update["start"]["sheetId"]]["rows"]
                target[: len(rows)] = rows
            elif "appendDimension" in request:
                update = request["appendDimension"]
                dimension = "rowCount" if update["dimension"] == "ROWS" else "columnCount"
                staged[update["sheetId"]]["properties"]["gridProperties"][dimension] += update[
                    "length"
                ]
            elif "duplicateSheet" in request:
                update = request["duplicateSheet"]
                new_id = max(staged) + 1
                staged[new_id] = copy.deepcopy(staged[update["sourceSheetId"]])
                staged[new_id]["properties"].update(sheetId=new_id, title=update["newSheetName"])
        self.tabs = staged
        return Response({})

    @property
    def writes(self):
        return [call for call in self.calls if call[0] == "POST"]


@pytest.fixture
def sheets():
    session = SheetsSession()
    return GoogleSheetsStore("synthetic-sheet", session), session
