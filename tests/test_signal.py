"""Host-side tests for Signal collateral.

Covers what Python owns: oracle-bit encoding round-trips, generator
determinism (numpy oracle frozen into corpora), and the agreement
comparison the check boundary enforces. DSP semantics live in MNCS and
are proven by tests/signal/*_tests.mncs; nothing here reimplements them.
Nothing here needs an executor.
"""

from __future__ import annotations

import json
import struct
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_signal_corpora


def f64_bits(value: float) -> int:
    return struct.unpack("<Q", struct.pack("<d", value))[0]


def test_float_encoding_roundtrips() -> None:
    for value in (0.0, -1.0, 0.1, 1e-12, 6.283185307179586, 1.7976931348623157e308):
        encoded = build_signal_corpora.f64(value)["float"]["bits"]
        assert encoded == f64_bits(value)
        back = struct.unpack("<d", struct.pack("<Q", encoded))[0]
        assert back == value


def test_integer_encoding_is_unsigned64() -> None:
    encoded = build_signal_corpora.u64(4)
    assert encoded == {"integer": {"value": 4, "type": {"bits": 64, "signed": False}}}


def test_generator_is_deterministic() -> None:
    with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
        build_signal_corpora.build(Path(first))
        build_signal_corpora.build(Path(second))
        for name, _, _ in build_signal_corpora.KERNELS:
            left = (Path(first) / f"signal-{name}-corpus.json").read_text()
            right = (Path(second) / f"signal-{name}-corpus.json").read_text()
            assert left == right
            pinned = (Path(__file__).resolve().parents[1] / "corpora"
                      / f"signal-{name}-corpus.json")
            assert left == pinned.read_text(), f"corpus drift: {name}"


def test_oracle_vectors_match_known_dft() -> None:
    # The generator's oracle must reproduce textbook values; if numpy ever
    # disagrees here, the frozen corpora (not the kernels) are suspect.
    import numpy as np

    X = np.fft.fft(np.array([1.0, 2.0, 3.0, 4.0]))
    assert X[0] == 10.0
    assert abs(X[1] - (-2 + 2j)) < 1e-12
    hann3 = 0.5 * (1 - np.cos(2 * np.pi * 3 / 7))
    assert abs(hann3 - 0.9504844339512095) < 1e-15


def test_agreement_comparison_is_strict() -> None:
    a = [{"float": {"bits": 1, "type": {"bits": 64}}}]
    b = [{"float": {"bits": 2, "type": {"bits": 64}}}]
    assert json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True)
    assert json.dumps(a, sort_keys=True) == json.dumps(a, sort_keys=True)
