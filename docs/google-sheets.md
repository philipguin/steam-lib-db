# Google Sheets and Steam setup

Your spreadsheet is the canonical datastore. Keep credentials and library
exports outside the software repository, even if your deployment repo is private.

## Google

1. Create or select a project in [Google Cloud Console](https://console.cloud.google.com/).
2. Enable the [Google Sheets API](https://console.cloud.google.com/apis/library/sheets.googleapis.com).
3. In IAM & Admin → Service Accounts, create a dedicated service account. It
   needs no project-wide Editor or Owner role to edit a shared spreadsheet.
4. Create a JSON key for that account if your organization permits it. Store it
   outside the checkout. For local use, point `GOOGLE_APPLICATION_CREDENTIALS`
   to the file; for Actions, put the entire JSON in `GOOGLE_CREDENTIALS_JSON`.
   Deployments supporting Application Default Credentials / workload identity
   can use those instead; the CLI requests only the Sheets scope.
5. Create a blank Google Sheet in your own Drive. Share it with the service
   account's `client_email` as **Editor**. The file need not be publicly shared.
6. Copy its spreadsheet ID from `https://docs.google.com/spreadsheets/d/ID/edit`.
   Set `GOOGLE_SHEET_ID` to that ID, not the URL or tab `gid`.

The Drive API is not required. Initialization creates three reserved tabs without
deleting the blank default tab or touching unrelated tabs. Existing reserved
names must either be a valid initialized schema or cause setup to stop.

Service-account keys are deployment credentials. Organization policies can
prohibit key creation; use your organization's approved ADC/workload identity
route in that case. No credential is sent to a project-maintained service.

## Steam

1. Obtain a Web API key from [Steam](https://steamcommunity.com/dev/apikey).
2. Use your numeric 17-digit SteamID64, available in your account data or profile
   URL when no custom vanity URL is selected. The CLI does not resolve vanity names.
3. Make the game-details data visible to the API. Private profiles/game details
   can produce an unavailable response. If playtime looks incomplete, inspect
   the separate playtime privacy setting too.
4. Set `STEAM_API_KEY` and `STEAM_ID` in your deployment.

The tool calls the public `api.steampowered.com` GetOwnedGames endpoint with
app info and played free games enabled. Never interpret absence as a guarantee
of lost ownership; API coverage and privacy affect what is visible.

## PowerShell example

Use a secret manager or secure prompt for the key; do not paste it into a command
that will be saved in your shell history:

```powershell
$env:GOOGLE_SHEET_ID = 'YOUR_SHEET_ID'
$env:GOOGLE_APPLICATION_CREDENTIALS = 'C:\private\service-account.json'
$env:STEAM_ID = 'YOUR_STEAM_ID64'
$steamSecret = Read-Host 'Steam API key' -AsSecureString
$env:STEAM_API_KEY = [System.Net.NetworkCredential]::new('', $steamSecret).Password
steam-library init
steam-library sync --dry-run
steam-library sync
```

These environment variables last for the current shell session. Example values
are placeholders, not working credentials. The tool never loads `.env` implicitly.

References: [Google service-account authentication](https://developers.google.com/identity/protocols/oauth2/service-account),
[Sheets scopes](https://developers.google.com/workspace/sheets/api/scopes),
[Steam API](https://partner.steamgames.com/doc/webapi/IPlayerService).
