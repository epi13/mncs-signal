# Signal semantic model

## What “signal” means in MNCS

A signal is **sampled data with an explicit timebase**: a finite,
bounded-length sequence of f64 samples plus a descriptor stating the
sample rate, channel count, and length (`mncs.signal.types.SignalDesc`).
Nothing here is an event bus, a subscription system, or OS signal
handling — the repository history, Atlas charter, and RFCs are unanimous
that `mncs-signal` is signal *processing* (DSP). Reactive/observable,
pub/sub, cancellation, and host-signal semantics are explicitly
out of scope (see “Non-model” below).

## What mncs-signal owns

- signal descriptors and validation (rate/channels/length travel with
  samples; zeros fail structurally with priority rate → channels → length);
- complex-f64 DSP arithmetic (total over finite inputs);
- DFT/IDFT (exact N=4), real-input DFT8, radix-2 FFT8 with an executable
  DFT/FFT agreement predicate;
- direct-form FIR, moving average, valid-mode convolution/correlation lanes;
- Hann/Hamming windows with tolerance-window entries;
- linear-interpolation resampling primitives;
- magnitude/magnitude-squared spectra, first-maximum peak-pick;
- bounded ring-buffer index discipline (capacity 4; stale ages report
  INVALID instead of wrapping).

## What it explicitly does not own

| Concern | Owner | Signal relationship |
|---|---|---|
| numeric primitives, approx policy | `mncs-numerics` | consumer (imports on the test path; labeled mirrors on the corpus path) |
| float kernels, sin/cos, exact tiers | `mncs-math` | consumer (bare intrinsics on the corpus path) |
| execution, scheduling, cancellation | Forge/Fabric/engine | none — kernels are pure functions, no tasks, no queues |
| persistence | Store | none — no durable signal state; corpora are frozen test vectors, not a database |
| telemetry | System Monitor | none — Signal collects nothing |
| provenance | Lineage | corpora carry oracle identity in the generator; no event graph |
| assertions/suites | `mncs-test` | suites are `test` declarations; no private assert machinery |
| planning/evidence obligations | RAVEL/Lab | Signal produces pressure, not experiment records |

## Stateless by construction

Every kernel is a pure function of its arguments. There are no
subscribers, no callbacks, no registries, no background tasks — hence no
races, no reentrancy hazards, no leaked subscriptions, no unsubscribe
protocol, and no scheduler to bound. The “streaming graph” of the
original architecture is realized as composable per-lane functions plus
the ring index discipline; anything needing tasks/queues/backpressure
belongs to Forge/Fabric, and is recorded as a boundary, not built here.

## Typed payloads, no stringly topics

Payloads are f64 scalars, fixed f64 arrays, records (`C64`,
`SignalDesc`), and finite enums (`SignalStatus`). Cross-module calls use
canonical module identities (`mncs.signal.*`); the one structuring
limitation found is documented under pressure SIG-PRESS-001 (corpus path
resolves only sibling-relative imports).

## Delivery, ordering, backpressure: N/A by design

Synchronous pure calls have no delivery semantics to define: the caller
observes the return, in order, exactly once, with no buffer. Fan-out is
calling the function twice. This is not a limitation to fix — it is why
Signal cannot become a second execution system.

## Failure model

- invalid descriptors → `SignalStatus` enum (BadRate/BadChannels/BadLength);
- stale ring ages / corrupt heads → INVALID slot sentinel (4);
- negative sqrt input → 0.0 (scalar boundary; domain enums where the
  test path can carry them);
- non-finite float input/result → toolchain trap (float tier rule);
- integer overflow in index arithmetic → toolchain trap (checked ops);
- unmet corpus expectation / suite failure → check boundary fails closed.

No case collapses into a generic error; each is observable at its layer
and precise enough for Debug.

## Persistence boundary

Transient computed values are never persisted. Durable artifacts are:
frozen oracle corpora (test vectors with generator provenance),
pressure entries with reproducers, and docs. Signal keeps no event log
and no state database.

## Host code and why

`scripts/` owns process/filesystem effects only: numpy oracle generation,
executor invocation, JSON comparison, fetching the pinned executor.
Numerics owns numerics; math owns trig; the toolchain owns execution.
The one deliberate duplication is `sig_sqrt` (Newton iteration mirroring
numerics, labeled at the use site) — forced by SIG-PRESS-001, removable
the moment cross-repo imports resolve on the experiment path.
