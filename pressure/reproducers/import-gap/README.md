# Reproducer: SIG-PRESS-001 (cross-repo imports on the experiment path)

`importing_kernel.mncs` imports `mncs.numerics.scalar_float` and calls
`sqrt_value`; `corpus.json` holds one exact-bit case (sqrt(4) = 2).

```bash
mncs experiment run importing_kernel.mncs --backend mncs-portable-wasm-mvp \
  --corpus corpus.json --output-dir /tmp/import-gap
```

Observed at `mncs-language 066897e`: exit 1, no result written,
`MNE173: imported module 'mncs.numerics.scalar_float' is unavailable to
the resolver` at the `use` line. The identical module shape passes
`mncs test` with `MNCS_LIBRARY_PATH` pointing at the numerics checkout
(the path resolves imports; the experiment CLI resolves `use` relative
to the importing file only).

Control: every kernel under `mncs/signal/` imports only sibling
`mncs.signal.*` modules plus bare intrinsics and runs green on three
backends (see `scripts/signal_check.py`).
