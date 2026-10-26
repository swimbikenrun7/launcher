# CLAUDE.md — launcher

A single-page Streamlit app at `~/projects/launcher` (port 8500) that serves as the home
page for Josh's locally hosted apps. This is a build-it-for-me project. Josh is a
programming novice, so end each task with plain-language notes and the exact terminal
commands to run it.

## What it does

- Reads `apps.yaml`. Each entry has a name, description, icon, project path, start
  command, and port. Initial entries:
  - run-planner: `~/projects/run-planner`, port 8501
  - Rental Investor: `~/projects/homeledger`, `apps/rentals/Home.py`, port 8502
  - Tax Helper: `~/projects/homeledger`, `apps/taxes/Home.py`, port 8503
- Shows one card per app with a running/stopped status (check whether the port answers)
  and a link that opens `http://localhost:<port>`.
- Includes a `start-all.sh` script, or systemd user units, so the apps start at login.
  Ask Josh which he prefers before building it.

## Rules

- Keep it small: no database, no shared code with other projects. It only knows what's in
  `apps.yaml`.
- It must not import from, or depend on, any app it launches.
- Python 3.12+, `.venv`, `pyproject.toml`, `ruff`, `pytest` (test the YAML loading and the
  status check).
- Commit on a branch; don't push or merge to `main` without Josh's OK.
