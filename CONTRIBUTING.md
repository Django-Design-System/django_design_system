# Contributing to dj-design-system

Thank you for taking the time to contribute!

## Setting up a development environment

**Prerequisites:** [uv](https://docs.astral.sh/uv/) and [just](https://just.systems/) must be installed.

```bash
git clone https://github.com/Django-Design-System/django_design_system.git
cd django_design_system
just install
just install-hooks   # installs the pre-commit git hook
just install-playwright  # installs Playwright browsers (needed for e2e tests)
```

## Running things locally

| Command                   | Purpose                                             |
| ------------------------- | --------------------------------------------------- |
| `just test`               | Run all unit tests                                  |
| `just test-one <pattern>` | Run tests matching a keyword                        |
| `just e2e`                | Run Playwright end-to-end tests                     |
| `just coverage`           | Unit tests with coverage report                     |
| `just check`              | Lint and formatting check (no changes)              |
| `just fix`                | Auto-fix all lint and formatting issues             |
| `just typecheck`          | Run mypy type checking                              |
| `just docs-serve`         | Serve the documentation site locally                |
| `just demo`               | Start the example component gallery in your browser |

The pre-commit hook installed by `just install-hooks` runs `just fix` automatically before every commit.

## Code conventions

- **Python style** is enforced by [ruff](https://docs.astral.sh/ruff/) — run `just fix` before committing.
- **HTML/template style** is enforced by [djlint](https://djlint.com/) — also covered by `just fix`.
- **Type annotations** are checked by [mypy](https://mypy-lang.org/) — run `just typecheck`.
- Line length is 88 characters.
- All new public classes and functions should have docstrings — they feed directly into the auto-generated API documentation.

## Submitting a pull request

1. Fork the repository and create a branch from `main`.
2. Make your changes, add tests for any new behaviour.
3. Run `just test` and `just check` — both must pass.
4. Open a PR against `main`. All CI checks must be green before merging.
5. A maintainer will review and merge.

For bug reports or feature requests, please [open an issue](https://github.com/Django-Design-System/django_design_system/issues) first.
