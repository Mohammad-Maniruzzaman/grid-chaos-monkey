# Contributing

## Workflow

- Create an Issue first (feature/bug/docs).
- Branch from `master`: `feat/<name>` or `fix/<name>`.
- Submit PR with:
  - what changed
  - how tested
  - screenshots for UI changes
  - linked issue number

## Local quality gates

- `ruff check .` (informational until baseline is cleaned)
- `python -m pytest -q`

## Commits and merges

- Prefer small PRs.
- Squash-merge PRs to keep history clean.
