# Aegis Shell

## What It Is

Aegis Shell is a zero-integration pipeline sidecar for AI-assisted workflows.

It is tool-agnostic and works without integrating directly with Claude, Codex, Cursor, Copilot, or other assistants. You run it once inside the repo being worked on.

Install Aegis once, then use it in any repo.

Aegis Shell is a sidecar:

- your AI tool does the implementation work
- Aegis observes and emits controls
- Aegis does not replace your AI tool
- Aegis does not run destructive commands

Primary purpose:

- Attach Aegis to your AI pipeline and see what it would control before you integrate.
- Use SDK integration as the upgrade path to enforce controls automatically.

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

`aegis attach --cmd "..."`:
- Runs your existing command under Aegis observation and simulation.

`aegis attach --cmd "..." --json`:
- Prints a machine-readable simulation report.

`aegis attach --cmd "..." --log pipeline.log`:
- Includes log file signals in the simulation.

`aegis control`:
- Shows the active persisted control state.

`aegis control --json`:
- Prints raw `.aegis/control.json`.

`aegis control apply-prompt`:
- Prints a pasteable control block for Codex/Claude/Cursor/Copilot workflows.

`aegis control clear`:
- Deletes `.aegis/control.json`.

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

Attach flow:

attach command -> observe process/log/repo signals -> generate control decisions -> persist control state -> simulation report

The current active controls are persisted at `.aegis/control.json`.
Session history remains in `.aegis/session.jsonl`.

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
- Estimated AI iterations avoided: 6
- Prevented 2-4 unnecessary retries
- Reduced scope from 6 files to 3
```

Example `aegis control`:

```text
[Aegis] Active Controls
[Aegis] Source: Aegis API
[Aegis] Event: scope_drift_signal
[Aegis] Confidence: high
[Aegis] Escalation: medium
[Aegis] Status: active
[Aegis] Expires: 2026-04-25T18:30:00+00:00
[Aegis] Controls:
[Aegis] - Stop retries
[Aegis] - Limit changes to 2-3 files
[Aegis] - Avoid refactoring unrelated code
[Aegis] - Validate changes before next step
```

Example `aegis control apply-prompt`:

```text
Aegis active control state:
- Stop retries
- Limit changes to 2-3 files
- Avoid refactoring unrelated code
- Validate changes before next step

Follow these controls while completing the current task. Do not expand scope unless explicitly instructed.
```

Example attach run:

```bash
aegis attach --cmd "python run_agent.py" --log run.log
```

Example attach report:

```text
[Aegis] Pipeline Simulation Report

[Aegis] Observed:
[Aegis] - Runtime: 120 sec
[Aegis] - Exit status: 0
[Aegis] - Repeated retry patterns: 3
[Aegis] - Scope drift: 4 -> 11 files
[Aegis] - Validation failures observed: 2

[Aegis] Aegis would have:
[Aegis] - Stopped repeated retries
[Aegis] - Restricted scope to 2-3 files
[Aegis] - Required validation before continuing

[Aegis] Projected impact:
[Aegis] - Estimated AI iterations avoided: 8-12
[Aegis] - Retry loops prevented: 2
[Aegis] - Scope reduced from 11 files to 3
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
