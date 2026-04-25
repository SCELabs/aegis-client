# Aegis Shell Attach Demos

Use these tiny scripts to demo attach-mode simulation without editing your own pipeline code.

```bash
python -m aegis.shell.cli attach --cmd "python examples/shell_attach/retry_loop_pipeline.py" --no-live
python -m aegis.shell.cli attach --cmd "python examples/shell_attach/noisy_rag_pipeline.py" --no-live
python -m aegis.shell.cli attach --cmd "python examples/shell_attach/context_bloat_pipeline.py" --no-live
python -m aegis.shell.cli attach --cmd "python examples/shell_attach/retry_loop_pipeline.py" --no-live --report .aegis/reports/retry-demo.md
```
