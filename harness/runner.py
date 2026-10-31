"""Execute a benchmark task in a sandbox and verify the result.

Four run modes exist, and the pair of them that matters for calibration is
``oracle`` and ``null``:

``oracle``    apply ``solution/apply.sh``; the verifier **must** pass.
``null``      change nothing; the verifier **must** fail (proves the task bites).
``hardcode``  apply ``solution/hardcode.sh``, a plausible but cheating patch
              that prints the right numbers for one dataset; **must** fail,
              because the verifier re-seeds its probe data on every run.
``agent``     run an arbitrary command (an AI agent, or your own shell) in the
              workspace, then verify.
"""

from __future__ import annotations

import dataclasses
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .models import TaskSpec

MODES = ("null", "oracle", "hardcode", "agent")
BACKENDS = ("local", "docker")

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclasses.dataclass
class RunResult:
    task_id: str
    mode: str
    backend: str
    passed: bool
    expected_pass: bool
    returncode: int
    duration_sec: float
    seed: int
    run_dir: str
    detail: str = ""

    @property
    def calibrated(self) -> bool:
        """True when the outcome matches what this mode is supposed to do."""
        return self.passed is self.expected_pass

    def as_dict(self) -> dict:
        data = dataclasses.asdict(self)
        data["calibrated"] = self.calibrated
        return data


def expected_pass(mode: str) -> bool:
    return mode == "oracle"


def _prepare_workspace(spec: TaskSpec, run_dir: Path) -> Path:
    workspace = run_dir / "workspace"
    shutil.copytree(spec.environment_dir, workspace)
    return workspace


def _verifier_env(spec: TaskSpec, workspace: Path, seed: int) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        STB_WORKSPACE=str(workspace),
        STB_SEED=str(seed),
        STB_TIMEOUT=str(spec.timeout_sec),
        PYTHONPATH=os.pathsep.join([str(REPO_ROOT), env.get("PYTHONPATH", "")]).rstrip(os.pathsep),
        PYTHONDONTWRITEBYTECODE="1",
        MPLBACKEND="Agg",
    )
    return env


# --------------------------------------------------------------------------
# local backend
# --------------------------------------------------------------------------
def _run_local(spec: TaskSpec, mode: str, run_dir: Path, seed: int,
               agent_cmd: str | None, log) -> tuple[bool, int]:
    workspace = _prepare_workspace(spec, run_dir)
    env = _verifier_env(spec, workspace, seed)
    env["PYTHON"] = sys.executable

    patch_script = {"oracle": spec.oracle_script, "hardcode": spec.hardcode_script}.get(mode)
    if mode in ("oracle", "hardcode"):
        if not patch_script or not patch_script.is_file():
            log.write(f"[harness] mode {mode}: no {patch_script} -> nothing applied\n")
        else:
            log.write(f"[harness] applying {patch_script.relative_to(spec.root)}\n")
            proc = subprocess.run(
                ["bash", str(patch_script)],
                cwd=str(workspace), env=env, capture_output=True, text=True,
                timeout=spec.timeout_sec,
            )
            log.write(proc.stdout + proc.stderr)
            if proc.returncode != 0:
                log.write(f"[harness] patch script failed with {proc.returncode}\n")
                return False, proc.returncode
    elif mode == "agent":
        if not agent_cmd:
            raise ValueError("mode=agent requires --agent-cmd")
        log.write(f"[harness] agent command: {agent_cmd}\n")
        proc = subprocess.run(
            ["bash", "-lc", agent_cmd],
            cwd=str(workspace), env=env, capture_output=True, text=True,
            timeout=spec.timeout_sec,
        )
        log.write(proc.stdout + proc.stderr)

    log.write("[harness] running verifier\n")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider",
         str(spec.verifier_dir)],
        cwd=str(REPO_ROOT), env=env, capture_output=True, text=True,
        timeout=spec.timeout_sec + 120,
    )
    log.write(proc.stdout + proc.stderr)
    return proc.returncode == 0, proc.returncode


# --------------------------------------------------------------------------
# docker backend
# --------------------------------------------------------------------------
def _docker_available() -> bool:
    return shutil.which("docker") is not None


def _run_docker(spec: TaskSpec, mode: str, run_dir: Path, seed: int,
                agent_cmd: str | None, log) -> tuple[bool, int]:
    if not _docker_available():
        raise RuntimeError("docker executable not found; use --backend local")

    workspace = _prepare_workspace(spec, run_dir)
    tag = f"stbench/{spec.task_id}:latest"

    log.write(f"[harness] docker build -t {tag}\n")
    build = subprocess.run(
        ["docker", "build", "-q", "-t", tag, str(spec.root)],
        capture_output=True, text=True, timeout=1800,
    )
    log.write(build.stdout + build.stderr)
    if build.returncode != 0:
        return False, build.returncode

    steps = []
    if mode == "oracle":
        steps.append("bash /solution/apply.sh")
    elif mode == "hardcode":
        steps.append("test -f /solution/hardcode.sh && bash /solution/hardcode.sh || true")
    elif mode == "agent":
        if not agent_cmd:
            raise ValueError("mode=agent requires --agent-cmd")
        steps.append(agent_cmd)
    steps.append("python -m pytest -q --no-header -p no:cacheprovider /verifier")

    script = "set -e\ncd /workspace\n" + "\n".join(steps) + "\n"
    cmd = [
        "docker", "run", "--rm", "--network", "none",
        "-v", f"{workspace}:/workspace",
        "-v", f"{spec.verifier_dir}:/verifier:ro",
        "-v", f"{spec.root / 'solution'}:/solution:ro",
        "-v", f"{REPO_ROOT / 'harness'}:/bench/harness:ro",
        "-e", "PYTHONPATH=/bench",
        "-e", f"STB_WORKSPACE=/workspace",
        "-e", f"STB_SEED={seed}",
        "-e", f"STB_TIMEOUT={spec.timeout_sec}",
        "-e", "MPLBACKEND=Agg",
        "-w", "/workspace",
        tag, "bash", "-c", script,
    ]
    log.write(f"[harness] docker run ({mode})\n")
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=spec.timeout_sec + 600)
    log.write(proc.stdout + proc.stderr)
    return proc.returncode == 0, proc.returncode


# --------------------------------------------------------------------------
def run_task(spec: TaskSpec, *, mode: str = "oracle", backend: str = "local",
             runs_dir: Path | None = None, seed: int | None = None,
             agent_cmd: str | None = None) -> RunResult:
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    if backend not in BACKENDS:
        raise ValueError(f"backend must be one of {BACKENDS}")

    seed = secrets.randbelow(2**31 - 1) if seed is None else seed
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    runs_dir = Path(runs_dir or REPO_ROOT / "runs")
    run_dir = runs_dir / f"{stamp}-{mode}-{backend}" / spec.task_id
    run_dir.mkdir(parents=True, exist_ok=True)

    started = time.perf_counter()
    log_path = run_dir / "run.log"
    with log_path.open("w") as log:
        log.write(f"# task     {spec.task_id} ({spec.difficulty})\n")
        log.write(f"# mode     {mode}\n# backend  {backend}\n# seed     {seed}\n")
        log.write(f"# started  {stamp}Z\n\n")
        try:
            impl = _run_local if backend == "local" else _run_docker
            passed, rc = impl(spec, mode, run_dir, seed, agent_cmd, log)
            detail = ""
        except subprocess.TimeoutExpired as exc:
            log.write(f"[harness] TIMEOUT after {spec.timeout_sec}s: {exc}\n")
            passed, rc, detail = False, 124, f"timeout after {spec.timeout_sec}s"
        except Exception as exc:  # noqa: BLE001 - harness must not crash a sweep
            log.write(f"[harness] ERROR {type(exc).__name__}: {exc}\n")
            passed, rc, detail = False, 1, f"{type(exc).__name__}: {exc}"

    duration = time.perf_counter() - started
    result = RunResult(
        task_id=spec.task_id, mode=mode, backend=backend, passed=passed,
        expected_pass=expected_pass(mode), returncode=rc,
        duration_sec=round(duration, 2), seed=seed,
        run_dir=str(run_dir.relative_to(REPO_ROOT)) if run_dir.is_relative_to(REPO_ROOT) else str(run_dir),
        detail=detail,
    )
    (run_dir / "result.json").write_text(json.dumps(result.as_dict(), indent=2) + "\n")
    return result


def summarise(results: list[RunResult]) -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": len(results),
        "passed": sum(r.passed for r in results),
        "calibrated": sum(r.calibrated for r in results),
        "miscalibrated": [r.task_id for r in results if not r.calibrated],
        "results": [r.as_dict() for r in results],
    }
