# Aegis Shell

## What It Is

Aegis Shell is a zero-integration sidecar for AI pipelines.

It runs your existing command, observes pipeline behavior, writes active control state, and produces a simulation report.

It does not modify your code.
It does not replace your pipeline.
It does not execute AI work.

Core message:

- Attach Aegis to your AI pipeline and see what it would control before you integrate.

## Primary Workflow

```bash
aegis attach --cmd "python run_agent.py"
```

No code changes are required.

## Attach Options

`--cmd`:
- Required command to run under observation.

`--log PATH`:
- Read an existing log file and include its signals in simulation.

`--json`:
- Emit machine-readable simulation report.

`--report PATH`:
- Save rendered report output to file.
- With `--json`, saves JSON output to file.

`--no-live`:
- Suppress live pass-through command output.

`--simulate` / `--no-simulate`:
- Enable or disable control simulation.

`--interval`:
- Observation polling interval (bounded 2-5 seconds).

## What Aegis Observes

External signals only:

- process stdout/stderr
- existing logs (`--log`)
- exit status
- repeated retry/error patterns
- validation failures
- context/token limit signals
- retrieval/RAG signals visible in output
- repo/diff growth as a supporting signal

## What Aegis Produces

- `.aegis/control.json` active controls
- `.aegis/session.jsonl` event history
- `.aegis/attach_runs.jsonl` compact attach run history
- optional report file (`--report`)

Attach reports are honest simulations:

- observed behavior
- Aegis would have controlled
- projected impact
- recommended SDK integration points

## Simulation vs Enforcement

Shell:

- observes
- simulates
- reports

SDK:

- enforces controls in production

## Demo Examples

```bash
python -m aegis.shell.cli attach --cmd "python examples/shell_attach/retry_loop_pipeline.py" --no-live
python -m aegis.shell.cli attach --cmd "python examples/shell_attach/noisy_rag_pipeline.py" --no-live
python -m aegis.shell.cli attach --cmd "python examples/shell_attach/context_bloat_pipeline.py" --no-live
python -m aegis.shell.cli attach --cmd "python examples/shell_attach/retry_loop_pipeline.py" --no-live --report .aegis/reports/retry-demo.md
```

## Other Commands

- `aegis init`
- `aegis attach`
- `aegis control`
- `aegis summary`
- `aegis stats`
- `aegis doctor`
- `aegis reset`

## Advanced / Background Monitoring

These commands are still available, but attach mode is the primary proof-of-value workflow:

- `aegis start`
- `aegis auto`
- `aegis stop`
- `aegis status`
