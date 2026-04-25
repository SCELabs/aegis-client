# Aegis Shell

## What It Is

Aegis Shell is a background control layer for AI-assisted workflows.

It is tool-agnostic and works without integrating directly with Claude, Codex, Cursor, Copilot, or other assistants. You run it once inside the repo being worked on.

Install Aegis once, then use it in any repo.

## Quick Start

```bash
pip install scelabs-aegis
aegis init

cd your-project
aegis start
```

Then use AI tools normally.

## Commands

`aegis start`:
- Starts background monitoring for the current repo.

`aegis status`:
- Shows background status, repo state, and last event.

`aegis summary`:
- Shows a session-level report.

`aegis stats`:
- Shows aggregate report data across sessions.

`aegis stop`:
- Stops background auto mode.

`aegis doctor`:
- Shows diagnostics for config, API, git, and runtime state.

`aegis reset`:
- Clears project `.aegis` runtime state only.

`aegis auto`:
- Runs foreground monitoring mode for users who want live output.

## How It Works

Aegis Shell observes git, filesystem, and diff signals in the current repo.

It treats the first observation as baseline, ignores `.aegis` runtime files, and sends detected signals to Aegis API for control decisions. If API is unavailable, it falls back to local monitoring behavior.

Flow:

observe -> detect -> Aegis control -> report -> summarize

## What It Detects

- retry and loop patterns
- scope drift
- large diff growth
- inefficient workflow changes

## What Aegis Outputs

```text
[Aegis] Scope drift detected
[Aegis] Control:
- Stop retries
- Limit changes to 2-3 files
- Avoid refactoring unrelated code
[Aegis] Impact:
- Estimated calls saved: 6
- Estimated cost saved: $1.20
```

## Background Mode

`aegis start` runs monitoring in the background.

Use `aegis status`, `aegis summary`, and `aegis stop` to inspect and control it.

On Windows, background mode avoids opening extra terminal windows when possible.

If background mode is unavailable in your environment, run `aegis auto` instead.

## Where To Run It

Run Aegis Shell inside the repo or project being worked on.

Aegis is installed once globally and creates project-local runtime state under `.aegis/`.

```bash
cd your-project
aegis start
```

## Troubleshooting

`aegis: command not found`:
- Reinstall with `pip install scelabs-aegis`.
- For local development, use `pip install -e .`.

No API key:
- Run `aegis init`.

Not a git repo:
- Run commands from the project root.

Reset local runtime state:
- Run `aegis reset`.

API unavailable:
- Aegis continues local monitoring when possible.
- Full optimization resumes when API is reachable again.

## Design Principles

- no tool lock-in
- no destructive actions
- no hidden file edits
- Aegis controls behavior, not code generation
- visible summaries and stats
