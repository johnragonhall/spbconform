# Releasing

Releases publish to PyPI from GitHub Actions using trusted publishing (OIDC).
No API token is stored anywhere.

## One-time setup

On https://pypi.org, open Your account, then Publishing, then "Add a new
pending publisher" (the project does not exist yet, so use a pending
publisher). Enter exactly:

| Field | Value |
| --- | --- |
| PyPI project name | `spbconform` |
| Owner | `johnragonhall` |
| Repository name | `spbconform` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

Then in the GitHub repository, open Settings, then Environments, and create an
environment named `pypi`. Add yourself as a required reviewer so every publish
needs an approval click.

Optional, for dry runs: repeat the pending publisher on https://test.pypi.org
with the same values except Environment name `testpypi`, and create a
`testpypi` environment on GitHub. Then run the Release workflow by hand
(Actions, Release, Run workflow); a manual run publishes to TestPyPI only.

## Each release

1. Change `__version__` in `src/spbconform/__init__.py`. It is the only place
   the version lives.
2. Run `uv run ruff check .` and `uv run pytest`, and fix anything that fails.
3. Commit the bump (`chore(release): 0.1.1`) and push it to `main`.
4. Tag the commit (`git tag v0.1.1`) and push the tag.
5. On GitHub, create a release from that tag and publish it. Publishing the
   release starts the workflow: tests, build, `twine check`, then the publish
   job, which waits for approval on the `pypi` environment.
6. Check https://pypi.org/project/spbconform/ and run
   `uvx --from spbconform==0.1.1 spbconform --help`.

PyPI never lets a version be uploaded twice, so a failed release needs a new
version number.
