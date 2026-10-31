"""Helpers imported by task verifiers.

Design note: why verifiers are seeded at run time
--------------------------------------------------
Every run exports ``STB_SEED`` with a fresh random value. Verifiers build their
probe data from :func:`rng`, so the numbers a solution must produce are *not*
knowable when the solution is written. A submission that hardcodes the expected
output passes at most one seed out of 2**32 and therefore fails in practice.
That is the mechanism behind the "hardcoded solution must fail" requirement.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np


class VerifierError(AssertionError):
    """Verifier-level failure with the captured process output attached."""


def workspace() -> Path:
    """Directory holding the (possibly modified) task environment."""
    raw = os.environ.get("STB_WORKSPACE")
    if not raw:
        raise VerifierError("STB_WORKSPACE is not set; run verifiers through the harness")
    path = Path(raw).resolve()
    if not path.is_dir():
        raise VerifierError(f"STB_WORKSPACE={path} is not a directory")
    return path


def seed() -> int:
    return int(os.environ.get("STB_SEED", "0"))


def rng(salt: int = 0) -> np.random.Generator:
    """Per-run random generator. ``salt`` separates independent probes."""
    return np.random.default_rng(seed() + salt)


def timeout_sec() -> int:
    return int(os.environ.get("STB_TIMEOUT", "300"))


def run(argv: list[str], *, cwd: Path | None = None, check: bool = True,
        stdin: str | None = None) -> subprocess.CompletedProcess:
    """Run a command inside the workspace and fail loudly with its output."""
    cwd = cwd or workspace()
    proc = subprocess.run(
        argv,
        cwd=str(cwd),
        input=stdin,
        capture_output=True,
        text=True,
        timeout=timeout_sec(),
    )
    if check and proc.returncode != 0:
        raise VerifierError(
            f"command failed ({proc.returncode}): {' '.join(argv)}\n"
            f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
        )
    return proc


def run_python(script: str, *args: str, check: bool = True,
               cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run a script from the workspace with the harness interpreter."""
    return run([sys.executable, script, *args], cwd=cwd, check=check)


def read_json(path: Path | str) -> dict:
    path = Path(path)
    if not path.is_file():
        raise VerifierError(f"expected output file is missing: {path}")
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise VerifierError(f"{path} is not valid JSON: {exc}") from exc


def require_keys(payload: dict, keys: list[str], *, where: str) -> None:
    missing = [k for k in keys if k not in payload]
    if missing:
        raise VerifierError(f"{where}: missing keys {missing}; got {sorted(payload)}")


def assert_close(actual, expected, *, rtol: float = 1e-9, atol: float = 0.0,
                 what: str = "value") -> None:
    actual_arr = np.asarray(actual, dtype=float)
    expected_arr = np.asarray(expected, dtype=float)
    if actual_arr.shape != expected_arr.shape:
        raise VerifierError(
            f"{what}: shape {actual_arr.shape} != expected {expected_arr.shape}"
        )
    if not np.all(np.isfinite(actual_arr)):
        raise VerifierError(f"{what}: contains non-finite entries: {actual_arr}")
    if not np.allclose(actual_arr, expected_arr, rtol=rtol, atol=atol):
        err = np.max(np.abs(actual_arr - expected_arr))
        raise VerifierError(
            f"{what}: max abs deviation {err:.6g} exceeds rtol={rtol} atol={atol}\n"
            f"  got      {actual_arr}\n  expected {expected_arr}"
        )


def assert_source_changed(relpath: str, *, forbidden: list[str] | None = None) -> str:
    """Read a workspace source file and reject obvious no-op or stub answers."""
    path = workspace() / relpath
    if not path.is_file():
        raise VerifierError(f"{relpath} was deleted; the task asks you to fix it, not remove it")
    text = path.read_text()
    if not text.strip():
        raise VerifierError(f"{relpath} is empty")
    for needle in forbidden or []:
        if needle in text:
            raise VerifierError(f"{relpath} still contains the buggy construct {needle!r}")
    return text
