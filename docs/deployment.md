# Deployment

The upstream repository is reusable software. Your schedule, Steam account,
spreadsheet, and credentials form a separate deployment. No personal scheduler
runs in the upstream repo.

## GitHub Actions: no fork, no local install

1. Complete [Google and Steam setup](google-sheets.md).
2. Create a small private GitHub repository, or use an existing one. You do not
   need to fork or check out the upstream repository.
3. Add repository Actions secrets named `GOOGLE_SHEET_ID`,
   `GOOGLE_CREDENTIALS_JSON` (the entire service-account JSON), `STEAM_ID`,
   and `STEAM_API_KEY`. Do not put values in the workflow file.
4. In GitHub's web editor, create `.github/workflows/steam-library.yml` from
   [the example](../examples/deployment.yml). Pin the Action to a reviewed full
   commit SHA; `v0.1.0` is a convenient release reference for the example.
5. Under Actions → My Steam library → Run workflow, select **init**. This creates
   the tabs. The dry-run setting applies only to sync, so init intentionally writes.
6. Run **sync** with dry run checked. Review the counts.
7. Run **sync** with dry run unchecked. Scheduled runs subsequently apply daily.

The example schedule is 07:23 UTC daily and is editable. GitHub scheduled runs
can be delayed, so this is not a precise timer. Run `init` before the first
scheduled invocation; a sync on an uninitialized sheet fails without modifying it.
To migrate later, first select **migrate** to preview, then run it with
`apply_migration` selected. Empty snapshots are not accepted by the example.

The composite Action supports Linux runners and uses an isolated Python 3.12
environment. It installs code from its own pinned Action directory; no caller
checkout is necessary. Inputs go through environment variables and allowlisted
commands, not shell interpolation. Runtime dependency versions have compatible
bounds; pinning the Action pins source, not the entire transitive Python environment.

Concurrency is scoped to your deployment repository. Configure only one writer
for a spreadsheet, including any local or alternate scheduled runs.

## CLI without a checkout

Download a release wheel, then install it with `python -m pip install <wheel>`.
Alternatively, with Python and Git already installed:

```console
python -m pip install "git+https://github.com/philipguin/steam-lib-db.git@v0.1.0"
```

Set the documented environment variables, then use the CLI commands from README.
For a local schedule, Windows Task Scheduler or an existing scheduler can invoke
the installed `steam-library sync` command with deployment-scoped environment
and credentials. Avoid keeping credentials in the task's command arguments.

## Docker

From a source checkout, build:

```console
docker build -t steam-lib-db:0.1.0 .
```

Supply non-secret IDs and the Steam key through an environment file **outside**
the checkout, and mount the Google key read-only. This Linux-shell example
assumes the mounted file is readable by container UID 10001:

```sh
docker run --rm --env-file /private/steam-library.env \
  -e GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/google.json \
  --mount type=bind,src=/private/google.json,dst=/run/secrets/google.json,readonly \
  steam-lib-db:0.1.0 sync --dry-run
```

Replace `sync --dry-run` with `init`, then use `sync` when ready. PowerShell uses
backticks rather than backslashes for line continuation; a single-line command
also works. The image contains only packaged software, runs as a non-root user,
and does not include credentials. v0.1 builds the Docker image in CI but does not
publish it to a container registry.

## Future friction reduction

A hosted authorization/setup service could remove the deployment repository,
service-account key creation, and manual scheduling. That is a separate product
with OAuth, credential storage, tenancy, and operating costs. v0.1 deliberately
keeps deployment under each user's control while making the engine reusable.

Reference: [GitHub workflow reuse](https://docs.github.com/en/actions/how-tos/reuse-automations).
