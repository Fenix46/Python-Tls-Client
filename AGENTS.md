# AGENTS.md

Instructions for any AI coding agent (Claude Code, Copilot, Cursor, etc.)
working in this repository.

## 1. What this project is

`python-tls-client` is a Python wrapper around a precompiled Go library
([bogdanfinn/tls-client](https://github.com/bogdanfinn/tls-client)) that
performs HTTP requests with custom TLS/HTTP2 fingerprints (JA3, client
identifiers, header ordering, etc.), so requests are harder to distinguish
from a real browser.

It is a fork of
[FlorianREGAZ/Python-Tls-Client](https://github.com/FlorianREGAZ/Python-Tls-Client),
published on PyPI as `python-tls-client` (the importable module stays
`tls_client`). The fork exists to carry fixes and features the upstream
project doesn't have: a binary-response corruption fix, certificate pinning,
typed exceptions, and safer session lifecycle handling.

Key facts about the codebase:
- Pure Python wrapper (`tls_client/`) over precompiled native binaries
  (`tls_client/dependencies/*.so|.dylib|.dll`), loaded via `ctypes` in
  `cffi.py`. The Python side never reimplements TLS/HTTP logic — it only
  builds a JSON payload, calls the native `request()` function, and parses
  the JSON response back.
- `sessions.py` is the core: `Session.execute_request()` builds the request
  payload and is the single call site for every HTTP verb.
- Published to PyPI via GitHub Actions trusted publishing, triggered on
  GitHub releases (`.github/workflows/publish.yml`).
- Test suite: `tests/test_unit_*.py` are network-free (mock the native
  `cffi` calls) and run in CI. `tests/test_binary_response.py` hits
  httpbin.org and is for manual runs only, not CI.

## 2. What can be done here

Agents are expected to work freely, without asking first, on:
- Bug fixes with a clear root cause and a reproducible failure.
- Adding or improving tests, especially network-free unit tests.
- Documentation fixes and clarifications (README, docstrings, comments).
- Refactors that don't change public behavior (signatures, return types,
  exception types callers might catch).
- CI/workflow changes that only add checks (linting, tests) without
  changing what gets published or when.
- Small, scoped additions the user explicitly asked for, split into
  reviewable commits.

Agents should NOT do the following without being explicitly asked, even if
it seems like a reasonable follow-up to other work:
- **Bump the package version** in `tls_client/__version__.py` or
  `pyproject.toml`. Versioning is a release decision tied to what actually
  ships and when — it is never an automatic side effect of a refactor,
  a bugfix, or a "this feels like it deserves a minor bump" judgment call.
- Change what the `publish.yml` workflow does, when it triggers, or push a
  git tag / create a GitHub release.
- Change public API behavior (rename/remove parameters, change exception
  hierarchies in a breaking way, change default values) without calling it
  out explicitly and getting confirmation.
- Delete or rewrite the native binaries in `tls_client/dependencies/`.
- Force-push, rewrite history, or amend commits already pushed to a shared
  branch.

## 3. How agents should behave

- **Work in small, scoped commits.** One logical change per commit, with a
  commit message explaining *why*, not just *what* (the diff already shows
  what changed).
- **Verify before claiming done.** Run the relevant test file(s) after a
  change; don't report a task complete on the strength of "it should work."
  If something can't be verified in this environment (e.g. the native
  library isn't loadable), say so explicitly instead of asserting success.
- **Stay inside the scope of the request.** If a task list is given, do
  exactly those tasks — don't fold in adjacent improvements, cleanups, or
  "while I'm here" changes that weren't asked for. Flag them instead and
  let the human decide.
- **Prefer the smallest change that solves the problem.** No speculative
  abstractions, no defensive code for cases that can't happen, no rewriting
  working code to a "better" style without being asked.
- **When something is ambiguous or touches a decision beyond code
  correctness (versioning, release timing, public API changes, adding
  dependencies), stop and ask** rather than picking a default and moving on.
- Keep the mixed-language boundary of this project in mind: code, comments,
  and commit messages are in English; conversation with the user may be in
  Italian. Don't let that leak into inconsistent docs (see `README.md`,
  which is English-only).

## 4. The human always has the final say

Everything an agent produces in this repository — code, commits, version
numbers, release decisions — is a proposal until the human (the repository
owner) reviews and accepts it.

- Agents do not merge their own work, push to shared/remote branches, or
  trigger a release unless explicitly instructed to for that specific
  action, at that specific time.
- Approval of one action (e.g. "yes, commit this") is not standing approval
  for similar actions later. Each consequential action is asked for again.
- If an agent disagrees with a decision the human has made, it should say so
  once, clearly, and then follow the human's call — not silently override it
  or keep re-litigating it.
- When in doubt about whether something requires sign-off, treat it as if it
  does.
