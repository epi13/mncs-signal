# MNCS language pressure ledger

Record workload, observed behavior, desired semantic, reproducer, owner, workaround and verification.
Speculative targets from the bootstrap sit below; grounded entries from attempted work come first.
Family-wide filings live in the Commons exchange; repo-local IDs are preserved there as legacyIds.

## Grounded entries (native realization campaign)

### SIG-PRESS-001 — Cross-repo imports unresolvable on the experiment path

- **Category:** tooling/compiler contract
- **Severity:** major
- **Status:** open, workaround in all DSP kernels
- **Owner candidate:** `mncs-language` (research CLI resolver)
- **Commons record:** `MNCS-TOOLING-<filed at campaign end>` (legacyId `mncs-signal:SIG-PRESS-001`)

**Workload:** any kernel importing `mncs.math.*`/`mncs.numerics.*` executed
via `mncs experiment run`.

**Observed:** `MNE173: imported module ... is unavailable to the resolver`
for every cross-repo import, while the identical file passes `mncs test`
(which resolves through `MNCS_LIBRARY_PATH`). The experiment CLI resolves
`use` relative to the importing file only — no package registry. Same
root cause as Harness's mirrored verdict lattice.

**Desired:** one documented import mechanism that works on both paths, or
an explicit diagnostic naming the path split.

**Reproducer:** `pressure/reproducers/import-gap/` (importing kernel +
minimal corpus + observed MNE173; control kernel with sibling-only
imports passes).

**Workaround:** kernels import only sibling `mncs.signal.*` plus bare
`sin`/`cos` intrinsics; `sig_sqrt` mirrors numerics Newton iteration with
a labeled comment and an in-process cross-check test. All mirrors are
removable the moment the resolver unifies.

**Verification:** full corpus suite green on three backends with
sibling-only imports; `mncs test` proves the mirrors agree with canonical
sources (`sig_sqrt_matches_numerics`).

### SIG-PRESS-002 — Required-but-undischarged obligations make PASS unreachable for numeric kernels

- **Category:** language/compiler contract
- **Severity:** moderate
- **Status:** open, accepted per family precedent
- **Owner candidate:** `mncs-language` (experiment contract)
- **Commons:** observation attached to `MNCS-TOOLING-01C791D9EFF4`
  (no duplicate declaration)

**Workload:** all 8 DSP kernels × 3 backends (85 cases, all met).

**Observed:** every suite reports UNKNOWN with
`compilation retained required unresolved obligations`: `float-finite`
per f64 op, `integer-overflow` per checked u64 op,
`iteration-exact-resource-cost` per loop. No backend discharges them.
Math's `scripts/check.sh` already accepts `PASS-or-UNKNOWN with all met`;
Signal follows that precedent.

**Desired:** either backends discharge finiteness/overflow obligations
they can decide, or the contract distinguishes “obligations no backend
could discharge” from real unknowns, so numeric repos can gate on PASS
again.

**Reproducer:** any Signal corpus run (e.g. `signal-ring`, pure u64:
4× `integer-overflow` obligations, zero unmet).

**Workaround:** none needed beyond the documented gate (status in
PASS/UNKNOWN + zero unmet + bit-exact cross-backend agreement).

**Verification:** `scripts/signal_check.py` enforces and reports the
obligation lists per kernel/backend instead of hiding them.

## Initial pressure targets (bootstrap speculation, still open unless noted)

- efficient complex-number abstraction — PARTLY RELIEVED: records +
  f64 pairs suffice for DSP; no new abstraction demonstrated necessary
- generic fixed/float signal kernels — REALIZED for f64 via generics
  (`dot_all<N>`, `diff`-style folds); fixed-point DSP not attempted
- SIMD intrinsics/vector types and auto-vectorization evidence — OPEN,
  untouched (no kernel needs them at N≤8; record, don't build)
- aligned/contiguous buffer control — OPEN, untouched
- ring buffers and lock-free/bounded queues — REALIZED as pure index
  discipline (`mncs.signal.ring`); lock-free queues belong to
  Forge/Fabric, not Signal
- no-allocation real-time regions — OPEN as evidence (compiler study
  data retained in run outputs; no claim made)
- const-sized arrays/windows — REALIZED (`[f64; N]` throughout)
- streaming iterators and backpressure — DECLINED: pure per-lane
  functions need no iterators; queue backpressure is Forge/Fabric's
- thread scheduling and priority hooks — DECLINED: no tasks in Signal
- CPU/CUDA kernel parity — DECLINED: no accelerator capability;
  cross-backend agreement (wasm/bytecode/cranelift 85/85) is the
  portability evidence instead
- deterministic transforms where promised — REALIZED: bit-exact
  agreement across three backends
- compiler evidence for allocation/vectorization decisions — OPEN,
  untouched

- efficient complex-number abstraction
- generic fixed/float signal kernels
- SIMD intrinsics/vector types and auto-vectorization evidence
- aligned/contiguous buffer control
- ring buffers and lock-free/bounded queues
- no-allocation real-time regions
- const-sized arrays/windows
- streaming iterators and backpressure
- thread scheduling and priority hooks
- CPU/CUDA kernel parity
- deterministic transforms where promised
- compiler evidence for allocation/vectorization decisions
