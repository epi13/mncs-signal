#!/usr/bin/env python3
"""Signal enforcement boundary: corpora, suites, and backend agreement.

Gates (fail closed, nonzero exit):

1. corpora in sync with the numpy-oracle generator (drift gate);
2. all five ``mncs test`` suites PASS on the canonical toolchain;
3. every corpus case meets expectations on wasm, bytecode, AND cranelift;
4. per-case returned values agree bit-exactly across the three backends.

Suite status may be PASS or UNKNOWN (math precedent: float-finite and
iteration obligations are retained by the toolchain while every
observation holds). UNKNOWN is reported per kernel, never hidden, and
never gates: the evidence is the met expectations, not the status word.

Cross-repo imports do not resolve on the experiment path, so kernels
import only sibling mncs.signal.* modules plus bare intrinsics; the
``mncs test`` path additionally resolves math/numerics/test libraries.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import build_signal_corpora

SUITES = (
    "tests/signal/types_tests.mncs",
    "tests/signal/dft_tests.mncs",
    "tests/signal/filter_tests.mncs",
    "tests/signal/stream_tests.mncs",
    "tests/signal/fft_tests.mncs",
)

SOURCES = {
    "types": "mncs/signal/types.mncs",
    "dft": "mncs/signal/dft.mncs",
    "fft": "mncs/signal/fft.mncs",
    "filters": "mncs/signal/filters.mncs",
    "windows": "mncs/signal/windows.mncs",
    "resample": "mncs/signal/resample.mncs",
    "ring": "mncs/signal/ring.mncs",
    "spectrum": "mncs/signal/spectrum.mncs",
}

BACKENDS = ("mncs-portable-wasm-mvp", "mncs-research-bytecode", "mncs-cranelift")


class SignalError(RuntimeError):
    pass


def find_executor() -> str:
    override = os.environ.get("MNCS_EXECUTOR")
    if override:
        return override
    found = shutil.which("mncs-executor")
    if found:
        return found
    for profile in ("release", "debug"):
        sibling = REPO.parent / "mncs-language" / "target" / profile / "mncs"
        if sibling.is_file():
            return str(sibling)
    raise SignalError(
        "no MNCS executor found: set MNCS_EXECUTOR, put mncs-executor on PATH "
        "(python3 scripts/fetch_mncs_executor.py), or check out mncs-language "
        "next to mncs-signal and build it"
    )


def library_path() -> str:
    roots = [
        REPO,
        Path(os.environ.get("MNCS_MATH_SRC", str(REPO.parent / "mncs-math" / "src"))),
        Path(os.environ.get("MNCS_NUMERICS_SRC",
                            str(REPO.parent / "mncs-numerics" / "src"))),
        Path(os.environ.get("MNCS_TEST_NATIVE",
                            str(REPO.parent / "mncs-test" / "native"))),
        Path(os.environ.get("MNCS_LANGUAGE_LIBRARY",
                            str(REPO.parent / "mncs-language" / "library"))),
    ]
    missing = [str(r) for r in roots if not r.is_dir()]
    if missing:
        raise SignalError(f"missing MNCS library roots: {missing}")
    return os.pathsep.join(str(r) for r in roots)


def check_corpora() -> None:
    with tempfile.TemporaryDirectory(prefix="signal-corpora-check-") as tmp:
        out = Path(tmp)
        build_signal_corpora.build(out)
        for name, _, _ in build_signal_corpora.KERNELS:
            fresh = (out / f"signal-{name}-corpus.json").read_text()
            pinned = (REPO / "corpora" / f"signal-{name}-corpus.json").read_text()
            if fresh != pinned:
                raise SignalError(f"corpus drift: corpora/signal-{name}-corpus.json")


def check_suites(executor: str) -> None:
    env = dict(os.environ, MNCS_LIBRARY_PATH=library_path())
    for suite in SUITES:
        completed = subprocess.run(
            [executor, "test", str(REPO / suite), "--format", "json"],
            capture_output=True, text=True, timeout=600, env=env, check=False)
        try:
            doc = json.loads(completed.stdout)
        except json.JSONDecodeError:
            raise SignalError(f"{suite}: unparseable test output")
        summary = doc.get("summary", {})
        if doc.get("classification") != "passed" or summary.get("failed", 1) != 0:
            raise SignalError(f"{suite}: suite not green: {summary}")
        print(f"{suite}: {summary['passed']} passed")


def run_corpus(executor: str, kernel: str, backend: str, tmp: Path) -> dict:
    out = tmp / f"{kernel}-{backend.replace('mncs-', '')}"
    completed = subprocess.run(
        [executor, "experiment", "run", str(REPO / SOURCES[kernel]),
         "--backend", backend,
         "--corpus", str(REPO / "corpora" / f"signal-{kernel}-corpus.json"),
         "--output-dir", str(out)],
        capture_output=True, text=True, timeout=600, check=False)
    result_file = out / "result.json"
    if completed.returncode != 0 or not result_file.is_file():
        raise SignalError(f"{kernel}/{backend}: run failed:\n{completed.stderr[-1500:]}")
    return json.loads(result_file.read_text(encoding="utf-8"))


def compare_returned(a: object, b: object) -> bool:
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def main() -> int:
    executor = find_executor()
    print(f"executor: {executor}")
    check_corpora()
    print("corpora in sync")
    check_suites(executor)
    with tempfile.TemporaryDirectory(prefix="signal-check-") as tmp:
        tmpdir = Path(tmp)
        per_kernel: dict[str, dict[str, dict]] = {}
        for kernel in SOURCES:
            per_backend = {}
            for backend in BACKENDS:
                result = run_corpus(executor, kernel, backend, tmpdir)
                status = result.get("status")
                unmet = [c.get("case_id") for c in result.get("cases", [])
                         if not c.get("expectation_met")]
                if status not in ("PASS", "UNKNOWN") or unmet:
                    raise SignalError(
                        f"{kernel}/{backend}: status={status} unmet={unmet} "
                        f"unresolved={result.get('unresolved_reasons')}")
                print(f"{kernel}/{backend}: {status} "
                      f"({len(result.get('cases', []))} met, "
                      f"unresolved={result.get('unresolved_reasons')})")
                per_backend[backend] = {
                    c.get("case_id"): c.get("returned")
                    for c in result.get("cases", [])}
            per_kernel[kernel] = per_backend
        total = disagreements = 0
        for kernel, per_backend in per_kernel.items():
            case_ids = set(per_backend[BACKENDS[0]])
            for backend in BACKENDS[1:]:
                if set(per_backend[backend]) != case_ids:
                    raise SignalError(f"{kernel}: case id sets differ across backends")
            for cid in sorted(case_ids):
                total += 1
                first = per_backend[BACKENDS[0]][cid]
                if any(not compare_returned(per_backend[b][cid], first)
                       for b in BACKENDS[1:]):
                    disagreements += 1
                    print(f"DIVERGE {kernel}::{cid}")
        print(f"cross-backend agreement: {total - disagreements}/{total}")
        if disagreements:
            raise SignalError(f"{disagreements} cross-backend divergences")
    print("signal boundary green")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SignalError, OSError, ValueError) as exc:
        print(f"signal_check FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
