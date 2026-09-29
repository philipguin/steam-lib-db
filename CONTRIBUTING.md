# Contributing

See README for installation and checks. Python 3.10 is the compatibility floor.
Keep the core merge plan independent from the network and storage adapter.

Changes must preserve these invariants:

* Steam sync cannot write annotations or delete stored games.
* Invalid snapshots cannot change presence or successful-sync metadata.
* AppID is identity; title and row number are not.
* Migrations are explicit, validated, backed up, and atomic.
* Tests, docs, and examples contain only synthetic deployment data.

Add behavioral tests for changed semantics, especially failure paths. Use fake
transports by default; credentialed integration checks must be opt-in against a
disposable spreadsheet. Never make CI depend on a contributor's Steam account.

Before opening a PR, run tests, lint, formatting checks, and a package build.
Document any schema change separately from the package version. Release work
must follow [the checklist](docs/releases.md).
