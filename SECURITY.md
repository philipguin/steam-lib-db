# Security

Do not include secrets or personal library data in public reports. For a suspected
vulnerability, use the repository's private vulnerability reporting feature when
enabled. Otherwise contact the maintainer privately before providing details.

The software sends credentials only to Steam and Google endpoints needed for
sync. The public project does not collect credentials, telemetry, or libraries.
Google Sheets permissions cover an entire spreadsheet; the annotation boundary
is implemented by the adapter and tests, not by per-tab Google authorization.

Pin the reusable Action to a reviewed commit. Keep deployment secrets in a
separate repository or secret manager. Rotate a credential at its provider if
it is exposed; deleting a Git commit is not sufficient.
