# Releasing

1. Update `pyproject.toml`, `steam_library.__version__`, examples, and changelog.
2. Run tests, lint, formatting checks, and `python -m build`.
3. Verify the wheel's CLI in a clean environment. Run the Docker smoke check in
   CI. Confirm Python 3.10 / 3.12 / 3.14 on Windows and Linux are green.
4. Review the exact tracked file list for personal data and secrets. The public
   repo must contain only code, documentation, and synthetic fixtures.
5. If possible, opt in to a live smoke test against a disposable spreadsheet:
   initialize, dry-run, sync twice, confirm annotations survive, verify status.
   Record when this was not performed; mocked tests are not live API verification.
6. Tag the reviewed commit `vX.Y.Z` and push the tag. The release workflow checks
   version agreement, runs tests/lint/build/container checks, then creates a
   GitHub release with wheel and source distribution. No PyPI token is required.
7. Confirm CI and release jobs completed and the artifacts are downloadable.

The Action can be consumed at the release tag or immutable commit SHA. Do not
move release tags. Fix releases with a new patch version. Dependency bounds are
not a complete reproducible lock; application operators may apply their own
reviewed constraints for tightly controlled environments.

v0.1 is an alpha release. There is no published compatibility promise for
undocumented internals; storage schema compatibility is explicit and guarded.
