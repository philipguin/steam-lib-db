# Changelog

## 0.1.0

Initial release of the reusable Steam-to-Google-Sheets synchronizer.

* Strict owned-games validation, playtime/app info, dry-run summaries, account binding.
* Non-destructive presence tracking with stable AppID identity.
* Isolated annotations with per-field provenance and optional research sources.
* Atomic initialization and sync, explicit backed-up v0-to-v1 migration path.
* CLI, reusable GitHub Action, Docker packaging, CI, and release workflow.

Limits: one writer per sheet; 1.8 MB atomic write budget; no store enrichment,
hosted OAuth service, or annotation-writing agent. Credentials are user supplied.
