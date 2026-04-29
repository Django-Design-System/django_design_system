# PyPI Package Setup Plan

This document tracks the planned work to make `dj-design-system` a properly packaged,
documented, and CI-tested public PyPI package.

> **Working process:** Each phase ends with a review checkpoint. No phase is started
> until the previous phase has been verified locally and approved.

---

## Decisions

| Topic                   | Decision                                                                                          |
| ----------------------- | ------------------------------------------------------------------------------------------------- |
| Build backend           | Migrate Poetry → **hatchling** (full uv migration)                                                |
| Version management      | **hatch-vcs** reads version from git tags (`v1.2.3` → `1.2.3`), no sed required                   |
| Version bump trigger    | **GitHub Release published** event (not raw tag push)                                             |
| Support matrix          | **Native GHA matrix** — no tox                                                                    |
| Django version coverage | 5.2 (LTS), 6.0, **latest** (catch regressions before pinning)                                     |
| API docs                | **mkdocstrings** module-level — auto-discovers new classes automatically                          |
| PyPI publishing         | **Trusted Publisher / OIDC** — no API token secret needed                                         |
| Coverage reporting      | PR comment posted/updated by GHA action                                                           |
| Gallery on GH Pages     | wget spider of running dev server → static HTML snapshot (HTMX won't work, acceptable)            |
| MkDocs theme            | material theme, styled to match gallery colours/fonts                                             |
| Pre-commit hook         | Writes `.git/hooks/pre-commit` that runs `just fix`                                               |
| Unpinned deps           | Transitive deps (markdown, etc.) left unpinned; only Django is range-pinned as we test against it |

---

## Phase 1 — Package & Tooling Foundation

> **Review checkpoint:** After completing this phase, run `uv sync --all-extras`,
> `just test`, `just check`, and `just demo`. Confirm all pass before proceeding.

### Step 1 — Migrate `pyproject.toml`

- `[build-system]`: `requires = ["hatchling", "hatch-vcs"]`, `build-backend = "hatchling.build"`
- `[project]`:
  - `dynamic = ["version"]`
  - `requires-python = ">=3.13"`
  - `dependencies = ["django>=5.2,<8", "markdown"]` — markdown intentionally unpinned
- `[project.optional-dependencies]`:
  - `testing`: pytest-django, pytest-playwright, pytest-mock, playwright, factory-boy, coverage, pytest-cov
  - `dev`: ruff, mypy, djlint, types-Markdown, types-Pygments
  - `docs`: mkdocs-material, mkdocstrings-python
- `[tool.hatch.version]`: `source = "vcs"` (reads from git tags via hatch-vcs)
- `[tool.hatch.build.targets.wheel]`: `packages = ["dj_design_system"]` (excludes tests/, example_project/ from wheel)
- Drop: `tox`, `psycopg2` (not actively tested against)
- Keep unchanged: all `[tool.ruff]`, `[tool.mypy]`, `[tool.coverage]`, `[tool.pytest.ini_options]`, `[tool.djlint]`

### Step 2 — Create `.python-version`

Single line: `3.13`

### Step 3 — Create `justfile`

| Recipe               | Purpose                                                                        |
| -------------------- | ------------------------------------------------------------------------------ |
| `install`            | `uv sync --all-extras`                                                         |
| `install-hooks`      | Write `.git/hooks/pre-commit` (runs `just fix`) + `chmod +x`                   |
| `test`               | `uv run pytest tests/ -m "not e2e"`                                            |
| `test-one pattern`   | `uv run pytest tests/ -k "{{pattern}}" -m "not e2e"`                           |
| `e2e`                | `uv run pytest tests/e2e/ -m e2e`                                              |
| `check`              | ruff check + djlint --check                                                    |
| `fix`                | ruff check --fix + ruff format + djlint --reformat                             |
| `fmt`                | alias for `fix`                                                                |
| `typecheck`          | `uv run mypy dj_design_system/`                                                |
| `coverage`           | pytest + `--cov --cov-report=term-missing`                                     |
| `docs-serve`         | `uv run mkdocs serve`                                                          |
| `docs-build`         | `uv run mkdocs build`                                                          |
| `install-playwright` | `uv run playwright install --with-deps chromium`                               |
| `build`              | `uv build`                                                                     |
| `demo`               | Start example_project at `:8000` + open browser (`xdg-open` / `open` fallback) |

---

## Phase 2 — Community & Governance Docs

> **Review checkpoint:** Read each new doc and confirm tone/content is right before proceeding.

| File                    | Contents                                                                                                                                               |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `CONTRIBUTING.md`       | uv + just setup, coding conventions, PR process, PyPI Trusted Publisher setup note                                                                     |
| `SECURITY.md`           | GitHub private advisory reporting process                                                                                                              |
| `CODE_OF_CONDUCT.md`    | Contributor Covenant v2.1                                                                                                                              |
| `CHANGELOG.md`          | Initial `[Unreleased]` and `0.0.1` entry                                                                                                               |
| `docs/ai-disclosure.md` | AI assistance disclosure — Python code is trusted and reviewed; gallery HTML/CSS/JS could benefit from human improvement and contributions are welcome |

---

## Phase 3 — MkDocs Site

> **Review checkpoint:** Run `just docs-serve`, browse all pages, confirm styling and API
> docs render correctly before proceeding.

### Step 9 — `mkdocs.yml`

- Theme: `material` with palette/font overrides matched to gallery CSS
- Plugins: `mkdocstrings[python]`, `search`
- `custom_css: [docs/assets/docs-theme.css]`
- `repo_url` pointing to GitHub repo
- Nav:
  ```
  Home             → docs/index.md
  Quick Start      → docs/quickstart.md
  Components       → docs/components.md
  Gallery          → docs/gallery.md
  Registry         → docs/registry.md
  Template Tags    → docs/templatetags.md
  Organisation     → docs/organisation.md
  API Reference
    Parameters     → docs/api/parameters.md
    Components     → docs/api/components.md
  AI Disclosure    → docs/ai-disclosure.md
  ```

### Step 10 — `docs/api/parameters.md`

Uses `::: dj_design_system.parameters` with `members: true` — **any new param class
added to the module is automatically included** with no config change.

### Step 11 — `docs/api/components.md`

Uses `::: dj_design_system.components` with `members: true` — same auto-discovery.

### Step 12 — Update `docs/assets/docs-theme.css`

Extend with CSS variables extracted from `gallery.css` / `gallery-toolbar.css` to
match colour palette and font stack on the MkDocs site.

### Step 13 — Update existing docs files

- Update any internal cross-reference links that should now point to the MkDocs site URL
- Add links to the static gallery site (GH Pages) in `docs/gallery.md` and `docs/quickstart.md`
- Add note in `docs/gallery.md` that the live interactive gallery is the running Django app,
  but a static snapshot is also browseable at the GH Pages URL

---

## Phase 4 — GitHub Actions CI/CD (7 workflows)

> **Review checkpoint:** Push a test branch, open a PR, confirm all check workflows
> appear and pass. Confirm PR coverage comment is created. Then approve before proceeding.

### Workflow overview

| File               | Trigger                     | Purpose                                                |
| ------------------ | --------------------------- | ------------------------------------------------------ |
| `lint.yml`         | push + PR to main           | ruff check + djlint check                              |
| `typecheck.yml`    | push + PR to main           | mypy on `dj_design_system/`                            |
| `test.yml`         | push + PR to main           | pytest unit matrix; coverage PR comment                |
| `e2e.yml`          | push + PR to main           | Playwright e2e tests                                   |
| `publish-test.yml` | push to main (all CI green) | build → publish to **Test PyPI** (OIDC)                |
| `publish.yml`      | release published           | build → publish to **production PyPI** (OIDC)          |
| `docs.yml`         | release published           | MkDocs → gh-pages; gallery snapshot → gh-pages-gallery |

### `test.yml` matrix

```yaml
matrix:
  python-version: ["3.13", "3.14"]
  django: ["Django>=5.2,<6", "Django>=6.0,<7", "Django"]
  # "Django" with no pin installs the latest available — catches future regressions
```

Coverage (xml) is generated only on Python 3.13 / `Django>=5.2,<6`.
`MishaKav/pytest-coverage-comment@main` posts a comment on the PR; subsequent
pushes to the same PR **update** rather than create a new comment.

### `publish-test.yml` — continuous Test PyPI deployment

Triggered on every push to `main`, but only runs **after** `lint.yml`, `typecheck.yml`,
`test.yml`, and `e2e.yml` all succeed (via `needs:` dependency chain or workflow
`workflow_run` trigger). Builds the package and publishes to Test PyPI using OIDC.

Version will be a dev/pre-release string from hatch-vcs (e.g. `0.1.dev5+gabcdef`),
which is valid on Test PyPI but won't conflict with production releases.

> **Test PyPI setup note (one-time, manual):** Configure a separate Trusted Publisher
> on test.pypi.org for this repo, workflow `publish-test.yml`, environment `test-pypi`.

### `publish.yml` — production PyPI on GitHub Release

Because we use `hatch-vcs`, the version is read directly from the git tag that was
created when the GH Release was published. No sed, no manual step — `uv build` picks
up the version automatically. Requires `id-token: write` permission for PyPI OIDC.

> **PyPI setup note (one-time, manual):** Create the project on PyPI and add
> Django-Design-System/django_design_system as a Trusted Publisher under the project
> settings. Details documented in `CONTRIBUTING.md`.

### `docs.yml` — gallery snapshot

```
1. Run: python example_project/manage.py collectstatic --noinput
2. Run: python example_project/manage.py runserver 8000 &
3. Run: wget --mirror --convert-links --adjust-extension --no-parent
         http://localhost:8000/
4. Deploy snapshot to gh-pages-gallery branch
```

Note: HTMX interactions won't work in the snapshot. This is acceptable; future work
could improve this (e.g. django-distill or server-side rendering at build time).

---

## Phase 5 — README Update

> **Review checkpoint:** Confirm all badges render correctly on GitHub before merging.

### Badges to add/update

```
Unit Tests  | existing workflow badge (updated path)
Lint        | existing workflow badge (updated path)
Typecheck   | new workflow badge
E2E         | new workflow badge
PyPI        | shields.io pypi/v/dj-design-system
Python      | shields.io pypi/pyversions/dj-design-system
Django      | manual badge: 5.2 | 6.0 | latest
```

### Content changes

- Supported versions table (Python 3.13/3.14, Django 5.2/6.0/latest)
- Updated `pip install dj-design-system` quick-start
- Links: CONTRIBUTING, SECURITY, CODE_OF_CONDUCT
- Links: MkDocs docs site (GH Pages URL), static gallery site (GH Pages URL)

---

## Verification Checklist

- [ ] `uv sync --all-extras` completes cleanly
- [ ] `just test` — all unit tests green
- [ ] `just check` — ruff + djlint pass
- [ ] `just typecheck` — mypy clean
- [ ] `just fix` applies fixes; `git commit` triggers pre-commit hook
- [ ] `just docs-build` — MkDocs builds, API pages include all classes
- [ ] `just e2e` — Playwright tests pass
- [ ] `just demo` — browser opens to gallery at localhost:8000
- [ ] Open a PR → lint, typecheck, test matrix (6 jobs), e2e all pass
- [ ] Coverage comment appears on PR; updates on re-push
- [ ] Create GH Release `v0.0.1` → publish to PyPI
- [ ] GH Release also triggers MkDocs + gallery deployment to GH Pages
- [ ] README badges all resolve correctly

---

## Out of Scope (this iteration)

- `settings-tox.py` — left in place as a harmless alias
- `psycopg2` — removed from deps; can be re-added if PostgreSQL testing is needed
- Codecov/Coveralls — inline PR comment is sufficient for now
- Making gallery GH Pages interactive (HTMX) — future iteration
- Changes to existing source code or tests
