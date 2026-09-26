#!/usr/bin/env python3
"""Build (or verify) the Signal kernel execution corpora.

Values come from an independent oracle (numpy: a different DFT/FFT/filter
implementation than the MNCS kernels) and are frozen here. Exact-bit cases
cover libm-free paths (descriptors, complex envelopes, DFT4, impulses, DC,
integer FIR, ring, peak-pick); tolerance-window cases cover libm-dependent
paths (DFT8/FFT8 general bins, windows, magnitudes) with the comparison
executing in MNCS so corpus expectations stay exact booleans.

``--verify`` rebuilds into a temp dir and fails on any drift (CI gate).

Requires numpy only for generation; the checked-in corpora are plain JSON.
Oracle pinned at generation time: see docs/TOOLCHAIN.md.
"""

from __future__ import annotations

import argparse
import json
import struct
import tempfile
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
CORPUS_DIR = REPO / "corpora"

TYPES = "mncs.signal.types"
DFT = "mncs.signal.dft"
FFT = "mncs.signal.fft"
FILTERS = "mncs.signal.filters"
WINDOWS = "mncs.signal.windows"
RESAMPLE = "mncs.signal.resample"
RING = "mncs.signal.ring"
SPECTRUM = "mncs.signal.spectrum"


def f64(value: float) -> dict:
    bits = struct.unpack("<Q", struct.pack("<d", float(value)))[0]
    return {"float": {"bits": bits, "type": {"bits": 64}}}


def u64(value: int) -> dict:
    return {"integer": {"value": int(value), "type": {"bits": 64, "signed": False}}}


def finite(module: str, enum: str, variant: str, discriminant: int) -> dict:
    return {
        "finite": {
            "type_identity": f"mncs:0.2:finite-type:{module}::{enum}",
            "variant_identity": f"mncs:0.2:finite-variant:{module}::{enum}::{variant}",
            "discriminant": discriminant,
        }
    }


def boolean(value: bool) -> dict:
    return {"boolean": {"value": bool(value)}}


def case(cid: str, module: str, function: str, args: list, expected: list,
         *, budget: int = 16384) -> dict:
    return {
        "id": cid,
        "request": {
            "schema_version": "0.1",
            "target": {"module": module, "function": function},
            "arguments": args,
            "step_budget": budget,
        },
        "expected": expected,
    }


STATUS = ("Ok", "BadRate", "BadChannels", "BadLength")


def st(variant: str) -> dict:
    return finite(TYPES, "SignalStatus", variant, STATUS.index(variant))


def types_cases() -> list:
    return [
        case("desc-ok", TYPES, "validate_descriptor",
             [u64(44100), u64(2), u64(1024)], [st("Ok")]),
        case("desc-rate", TYPES, "validate_descriptor",
             [u64(0), u64(2), u64(1024)], [st("BadRate")]),
        case("desc-channels", TYPES, "validate_descriptor",
             [u64(48000), u64(0), u64(512)], [st("BadChannels")]),
        case("desc-length", TYPES, "validate_descriptor",
             [u64(48000), u64(1), u64(0)], [st("BadLength")]),
        case("desc-priority", TYPES, "validate_descriptor",
             [u64(0), u64(0), u64(0)], [st("BadRate")]),
        case("cadd-re", TYPES, "c_add_re",
             [f64(1.5), f64(2.5), f64(3.25), f64(4.75)], [f64(4.75)]),
        case("cadd-im", TYPES, "c_add_im",
             [f64(1.5), f64(2.5), f64(3.25), f64(4.75)], [f64(7.25)]),
        case("cmul-re", TYPES, "c_mul_re",
             [f64(1.0), f64(2.0), f64(3.0), f64(4.0)], [f64(-5.0)]),
        case("cmul-im", TYPES, "c_mul_im",
             [f64(1.0), f64(2.0), f64(3.0), f64(4.0)], [f64(10.0)]),
        case("cconj-im", TYPES, "c_conj_im",
             [f64(3.0), f64(-4.5)], [f64(4.5)]),
        case("cnorm2", TYPES, "c_norm2_flat",
             [f64(3.0), f64(4.0)], [f64(25.0)]),
    ]


def _split4(values: list) -> list:
    return [f64(v) for v in values]


def dft_cases() -> list:
    cases = []
    # Exact DFT4: impulse, DC, ramp (oracle: direct complex DFT).
    xr = [1.0, 0.0, 0.0, 0.0]
    xi = [0.0, 0.0, 0.0, 0.0]
    X = np.fft.fft(np.array(xr) + 1j * np.array(xi))
    for m in range(4):
        cases.append(case(f"dft4-impulse-{m}", DFT, "dft4_bin_re",
                          _split4(xr) + _split4(xi) + [u64(m)], [f64(X[m].real)]))
        cases.append(case(f"dft4-impulse-im-{m}", DFT, "dft4_bin_im",
                          _split4(xr) + _split4(xi) + [u64(m)], [f64(X[m].imag)]))
    xr = [1.0, 2.0, 3.0, 4.0]
    X = np.fft.fft(np.array(xr))
    for m in range(4):
        cases.append(case(f"dft4-ramp-{m}", DFT, "dft4_bin_re",
                          _split4(xr) + _split4(xi) + [u64(m)], [f64(X[m].real)]))
        cases.append(case(f"dft4-ramp-im-{m}", DFT, "dft4_bin_im",
                          _split4(xr) + _split4(xi) + [u64(m)], [f64(X[m].imag)]))
    # Exact IDFT4 reconstruction of the ramp spectrum.
    Xr = [float(v.real) for v in X]
    Xi = [float(v.imag) for v in X]
    xr_back = np.fft.ifft(np.array(Xr) + 1j * np.array(Xi))
    for m in range(4):
        cases.append(case(f"idft4-ramp-{m}", DFT, "idft4_bin_re",
                          _split4(Xr) + _split4(Xi) + [u64(m)],
                          [f64(xr_back[m].real)]))
    # Exact DFT8: impulse and DC (no libm values involved).
    x8 = [1.0] + [0.0] * 7
    for m in (0, 3, 7):
        cases.append(case(f"dft8r-impulse-{m}", DFT, "dft8r_bin_re",
                          [f64(v) for v in x8] + [u64(m)], [f64(1.0)]))
        cases.append(case(f"dft8r-impulse-im-{m}", DFT, "dft8r_bin_im",
                          [f64(v) for v in x8] + [u64(m)], [f64(0.0)]))
    x8 = [1.0] * 8
    cases.append(case("dft8r-dc-0", DFT, "dft8r_bin_re",
                      [f64(v) for v in x8] + [u64(0)], [f64(8.0)]))
    cases.append(case("dft8r-dc-4", DFT, "dft8r_bin_re",
                      [f64(v) for v in x8] + [u64(4)], [f64(0.0)]))
    # Tolerance windows: general real inputs via the numpy oracle.
    x8 = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    X = np.fft.fft(np.array(x8))
    for m in (1, 5):
        cases.append(case(f"dft8r-ramp-{m}", DFT, "dft8r_within_re",
                          [f64(v) for v in x8] + [u64(m), f64(X[m].real), f64(1e-9)],
                          [boolean(True)]))
        cases.append(case(f"dft8r-ramp-im-{m}", DFT, "dft8r_within_im",
                          [f64(v) for v in x8] + [u64(m), f64(X[m].imag), f64(1e-9)],
                          [boolean(True)]))
    return cases


def fft_cases() -> list:
    cases = []
    x8 = [1.0] + [0.0] * 7
    for m in (0, 5):
        cases.append(case(f"fft8r-impulse-{m}", FFT, "fft8r_bin_re",
                          [f64(v) for v in x8] + [u64(m)], [f64(1.0)]))
    x8 = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    X = np.fft.fft(np.array(x8))
    for m in (1, 5):
        cases.append(case(f"fft8r-ramp-{m}", FFT, "fft8r_within_re",
                          [f64(v) for v in x8] + [u64(m), f64(X[m].real), f64(1e-9)],
                          [boolean(True)]))
        cases.append(case(f"fft8r-ramp-im-{m}", FFT, "fft8r_within_im",
                          [f64(v) for v in x8] + [u64(m), f64(X[m].imag), f64(1e-9)],
                          [boolean(True)]))
        cases.append(case(f"agree-ramp-{m}", FFT, "dft_fft_agree_re",
                          [f64(v) for v in x8] + [u64(m), f64(1e-9)],
                          [boolean(True)]))
        cases.append(case(f"agree-ramp-im-{m}", FFT, "dft_fft_agree_im",
                          [f64(v) for v in x8] + [u64(m), f64(1e-9)],
                          [boolean(True)]))
    return cases


def filter_cases() -> list:
    return [
        case("fir-impulse", FILTERS, "fir4",
             [f64(1.0), f64(0.0), f64(0.0), f64(0.0),
              f64(0.5), f64(0.25), f64(0.125), f64(0.125)], [f64(0.5)]),
        case("fir-dc", FILTERS, "fir4",
             [f64(2.0)] * 4 + [f64(0.5), f64(0.25), f64(0.125), f64(0.125)],
             [f64(2.0)]),
        case("fir-ramp", FILTERS, "fir4",
             [f64(1.0), f64(2.0), f64(3.0), f64(4.0),
              f64(1.0), f64(0.0), f64(0.0), f64(0.0)], [f64(1.0)]),
        case("ma-const", FILTERS, "ma4",
             [f64(3.0)] * 4, [f64(3.0)]),
        case("ma-step", FILTERS, "ma4",
             [f64(0.0), f64(0.0), f64(0.0), f64(4.0)], [f64(1.0)]),
        case("conv-lane0", FILTERS, "conv32_bin",
             [f64(1.0), f64(2.0), f64(3.0), f64(1.0), f64(-1.0), u64(0)],
             [f64(-1.0)]),
        case("conv-lane1", FILTERS, "conv32_bin",
             [f64(1.0), f64(2.0), f64(3.0), f64(1.0), f64(-1.0), u64(1)],
             [f64(-1.0)]),
    ]


def window_cases() -> list:
    n = np.arange(8)
    hann = 0.5 * (1 - np.cos(2 * np.pi * n / 7))
    hamming = 0.54 - 0.46 * np.cos(2 * np.pi * n / 7)
    return [
        case("hann-end0", WINDOWS, "hann_weight",
             [u64(0), u64(8)], [f64(hann[0])]),
        case("hann-end7", WINDOWS, "hann_weight",
             [u64(7), u64(8)], [f64(hann[7])]),
        case("hann-mid", WINDOWS, "hann_within",
             [u64(3), u64(8), f64(hann[3]), f64(1e-12)], [boolean(True)]),
        case("hamming-mid", WINDOWS, "hamming_within",
             [u64(3), u64(8), f64(hamming[3]), f64(1e-12)], [boolean(True)]),
        case("hamming-end", WINDOWS, "hamming_within",
             [u64(0), u64(8), f64(hamming[0]), f64(1e-12)], [boolean(True)]),
    ]


def resample_cases() -> list:
    return [
        case("lerp-lo", RESAMPLE, "lerp",
             [f64(2.0), f64(6.0), f64(0.0)], [f64(2.0)]),
        case("lerp-hi", RESAMPLE, "lerp",
             [f64(2.0), f64(6.0), f64(1.0)], [f64(6.0)]),
        case("lerp-quarter", RESAMPLE, "lerp",
             [f64(2.0), f64(6.0), f64(0.25)], [f64(3.0)]),
        case("up2-mid", RESAMPLE, "up2_mid",
             [f64(1.0), f64(3.0)], [f64(2.0)]),
    ]


def ring_cases() -> list:
    return [
        case("push-empty", RING, "push_head", [u64(4)], [u64(0)]),
        case("push-next", RING, "push_head", [u64(1)], [u64(2)]),
        case("advance-wrap", RING, "ring_advance", [u64(3)], [u64(0)]),
        case("advance-invalid", RING, "ring_advance", [u64(9)], [u64(4)]),
        case("slot-recent", RING, "ring_slot", [u64(2), u64(0)], [u64(2)]),
        case("slot-back", RING, "ring_slot", [u64(2), u64(2)], [u64(0)]),
        case("slot-wrap", RING, "ring_slot", [u64(0), u64(1)], [u64(3)]),
        case("slot-stale", RING, "ring_slot", [u64(1), u64(4)], [u64(4)]),
        case("slot-corrupt", RING, "ring_slot", [u64(7), u64(0)], [u64(4)]),
        case("count-sat", RING, "ring_count", [u64(99)], [u64(4)]),
        case("count-open", RING, "ring_count", [u64(2)], [u64(2)]),
    ]


def spectrum_cases() -> list:
    mags = np.abs(np.fft.fft(np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])))
    return [
        case("mag2-34", SPECTRUM, "mag2", [f64(3.0), f64(4.0)], [f64(25.0)]),
        case("mag-34", SPECTRUM, "mag_within",
             [f64(3.0), f64(4.0), f64(5.0), f64(1e-12)], [boolean(True)]),
        case("mag-bin1", SPECTRUM, "mag_within",
             [f64(-4.0), f64(9.65685424949238), f64(mags[1]), f64(1e-9)],
             [boolean(True)]),
        case("peak-first", SPECTRUM, "peak_bin4",
             [f64(1.0), f64(5.0), f64(5.0), f64(2.0)], [u64(1)]),
        case("peak-last", SPECTRUM, "peak_bin4",
             [f64(0.5), f64(0.25), f64(0.125), f64(0.9)], [u64(3)]),
    ]


KERNELS = (
    ("types", TYPES, types_cases),
    ("dft", DFT, dft_cases),
    ("fft", FFT, fft_cases),
    ("filters", FILTERS, filter_cases),
    ("windows", WINDOWS, window_cases),
    ("resample", RESAMPLE, resample_cases),
    ("ring", RING, ring_cases),
    ("spectrum", SPECTRUM, spectrum_cases),
)


def build(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    built = {}
    for name, module, fn in KERNELS:
        doc = {"schema_version": "0.1", "name": f"signal-{name}", "cases": fn()}
        (out_dir / f"signal-{name}-corpus.json").write_text(
            json.dumps(doc, indent=1) + "\n", encoding="utf-8"
        )
        built[name] = len(doc["cases"])
    return built


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        with tempfile.TemporaryDirectory(prefix="signal-corpora-") as tmp:
            build(Path(tmp))
            for name, _, _ in KERNELS:
                fresh = (Path(tmp) / f"signal-{name}-corpus.json").read_text()
                pinned = (CORPUS_DIR / f"signal-{name}-corpus.json").read_text()
                if fresh != pinned:
                    raise SystemExit(f"corpus drift: corpora/signal-{name}-corpus.json")
        print("corpora in sync")
    else:
        print(build(CORPUS_DIR))


if __name__ == "__main__":
    main()
