# mncs-signal

<!-- MNCS:generated:begin -->
## Project entry

Sampled-signal DSP written in MNCS: descriptors with explicit timebases, complex-f64 arithmetic, DFT/IDFT/FFT, FIR filtering and convolution, windows, resampling, spectra, and a bounded ring-buffer discipline, verified against an independent numpy oracle.

```bash
python3 scripts/signal_check.py
```

Declared capabilities (declarations do not establish execution health):

- `sampled-signal-dsp/0.1` — mncs-library (experimental)

Semantic sources and ownership: `.mncs/projections.json`.
<!-- MNCS:generated:end -->

Sampled-signal DSP for MNCS, written in MNCS: descriptors with explicit
timebases, complex-f64 arithmetic, DFT/IDFT/FFT, FIR filtering and
convolution, windows, resampling, spectra, and a bounded ring-buffer
discipline — verified against an independent numpy oracle with exact-bit
corpora where bit-exact and in-MNCS tolerance windows where host libm is
involved.

> **Status:** native realization. 8 kernels, 33 `mncs test` proofs, 85
> oracle cases meeting expectations on portable-WASM, research-bytecode,
> and Cranelift with 85/85 bit-exact cross-backend agreement.

“Signal” here means signal *processing*, not events or subscriptions:
pure per-lane functions over f64 with no tasks, queues, callbacks, or
registries — hence no delivery semantics to define and no scheduler to
bound. See `docs/SIGNAL_MODEL.md`.

## Layout

```text
mncs/signal/    types.mncs     descriptors, validation, complex-f64, tolerance
                dft.mncs       exact DFT4/IDFT4, real-input DFT8, tolerance windows
                fft.mncs       radix-2 FFT8 + executable DFT/FFT agreement predicate
                filters.mncs   FIR direct form, moving average, valid convolution
                windows.mncs   Hann/Hamming weights + window checks
                resample.mncs  linear interpolation / upsample-mid primitives
                ring.mncs      bounded ring index discipline (capacity 4)
                spectrum.mncs  power/magnitude spectra, first-maximum peak-pick
tests/signal/   five native suites (33 tests, profile 0.18)
tests/test_signal.py   oracle/generator/agreement checks (5 tests)
corpora/        frozen oracle corpora (generator-built, drift-gated)
scripts/        build_signal_corpora.py (numpy oracle), signal_check.py
                (enforcement boundary), fetch_mncs_executor.py
docs/           SIGNAL_MODEL.md, TOOLCHAIN.md, ARCHITECTURE.md,
                LANGUAGE_PRESSURES.md (grounded entries + dispositioned targets),
                rfcs/0001-foundation.md
pressure/       reproducers/import-gap/ (SIG-PRESS-001)
```

## Quick start

```bash
# Explicit digest-verified executor (or a sibling mncs-language build).
python3 scripts/fetch_mncs_executor.py --dest ~/.local/bin/mncs-executor

# Full boundary: corpora sync + native suites + 3-backend runs + agreement.
python3 scripts/signal_check.py
```

## Ownership

Signal owns sampled-signal DSP semantics over canonical numeric owners:
primitives and approx policy stay in `mncs-numerics`, float kernels and
trig stay in `mncs-math` (consumed as bare intrinsics plus one labeled
Newton mirror, `sig_sqrt`, forced by the corpus-path import gap).
Execution, persistence, telemetry, and planning belong to
Forge/Fabric/Store/System Monitor/RAVEL — Signal has no tasks, no state
store, no monitors, and no experiment records (that layer is Lab's).

## Verification

- `mncs test` suites: identities (i·i=−1), oracle vectors (ramp DFT,
  numpy FFT bins), reconstruction (IDFT∘DFT), agreement predicates,
  fault cases (zero descriptors, stale ring ages, peak ties).
- Oracle corpora: numpy-generated, exact bits where libm-free,
  in-MNCS tolerance windows otherwise; generator deterministic and
  drift-gated.
- Backends: every case met on all three; returned values compared
  bit-exact across backends (85/85). Suite status PASS-or-UNKNOWN per
  the math precedent — obligation lists are reported, not hidden.
- `mncs-doctor doctor`: known-skewed — all findings are DOC102
  unknown-profile-0.18 (registry lags the toolchain; identical on
  mncs-test). No Signal-attributable finding.

## Pressures

- SIG-PRESS-001 (major, open): cross-repo imports unresolvable on the
  experiment path (MNE173) — same root cause as Harness's mirrored
  lattice; filing to Commons this campaign.
- SIG-PRESS-002 (moderate, open): required-but-undischarged
  float-finite/integer-overflow obligations make PASS unreachable for
  numeric kernels — observation attached to `MNCS-TOOLING-01C791D9EFF4`,
  no duplicate.
- Bootstrap speculation dispositioned in `docs/LANGUAGE_PRESSURES.md`
  (realized / open / declined with reasons).

## License

Apache-2.0. See `LICENSE`.
