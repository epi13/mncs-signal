# Architecture

## Layers

1. **Signal model** — samples, channels, rates, timebases and buffers.
2. **Math kernels** — complex arithmetic, FFT, convolution, windows and vector operations.
3. **Filters/resampling** — FIR/IIR, interpolation and sample-rate conversion.
4. **Streaming graph** — bounded buffers, scheduling, backpressure and lifecycle.
5. **Acceleration** — SIMD, multithreaded and CUDA-capable kernels.
6. **Verification** — known vectors, reconstruction, impulse/frequency response, latency and determinism evidence.

## First milestones

1. Signal/buffer types and complex arithmetic.
2. FFT/IFFT with verification corpus.
3. FIR/IIR and convolution.
4. Resampling.
5. Allocation-bounded streaming graph and accelerated kernels.
