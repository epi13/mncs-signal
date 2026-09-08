# RFC 0001: Signal-processing foundation

Status: Draft

## Principles

- Sample rate, channel structure and numeric representation are explicit.
- Batch and real-time execution share semantics but may use different physical strategies.
- Real-time contracts include bounded memory, latency and blocking behavior.
- Transform/filter correctness is validated independently of performance.
- SIMD/GPU acceleration must preserve declared numerical tolerance and ordering semantics.
- Pipelines expose backpressure and lifecycle rather than relying on hidden queues.

## Pressure objectives

Complex numbers, generic numeric kernels, SIMD, ring buffers, zero-allocation hot paths, const sizes, iterators/streams, bounded queues, concurrency, real-time scheduling, CUDA kernels, vectorization and numerical tolerance evidence.
