# Third-Party Notices

This project's own source is licensed as described in [`LICENSE`](LICENSE).
It depends on the following third-party software, each under its own
license. None of it is vendored or redistributed by this repository — it is
installed separately via `pip` (see `pyproject.toml`).

## Runtime dependency

| Package | License | Project |
| :--- | :--- | :--- |
| [Playwright for Python](https://playwright.dev/python/) | Apache License 2.0 | https://github.com/microsoft/playwright-python |

Playwright drives a Chromium browser instance; Chromium itself is installed
separately via `playwright install chromium` and is licensed under its own
terms (primarily BSD-style, with components under other open-source
licenses) — see https://www.chromium.org/chromium-projects/ for details.

## Development-only dependencies

Not distributed with the installed package; used only to develop and test
this repository (`pyproject.toml` `[project.optional-dependencies].dev`).

| Package | License | Project |
| :--- | :--- | :--- |
| [pytest](https://docs.pytest.org/) | MIT License | https://github.com/pytest-dev/pytest |
| [ruff](https://docs.astral.sh/ruff/) | MIT License | https://github.com/astral-sh/ruff |

## Governance framework

Development of this repository is governed by the Token-Optimized Agent
Pipeline, vendored as a git submodule at `.agents/` with its own license and
notices under `.agents/LICENSE.txt` and `.agents/NOTICE.md`.
