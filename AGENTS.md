# Agent and contributor contract

- Prefer `mncs-language` for implementation.
- State sample rate, channel shape, numeric representation, latency and allocation behavior where relevant.
- Real-time paths must not silently allocate, block or take unbounded work.
- Validate transforms/filters against trusted vectors, reconstruction properties and frequency-domain expectations.
- Distinguish throughput-oriented batch execution from hard/soft real-time streaming contracts.
- Record language/compiler/runtime gaps in `docs/LANGUAGE_PRESSURES.md`.
