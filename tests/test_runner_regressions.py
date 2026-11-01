"""Agent isolation and valid-result semantics."""
import io
import subprocess
from pathlib import Path
import pytest
from harness import cli, models, runner


@pytest.fixture
def spec():
    return models.discover(runner.REPO_ROOT / "tasks")[0]


def test_local_agent_is_rejected_before_execution(spec, tmp_path):
    marker = tmp_path / "should-not-exist"
    result = runner.run_task(spec, mode="agent", backend="local", runs_dir=tmp_path,
                             agent_cmd=f"touch {marker}")
    assert result.error and not result.successful
    assert "requires --backend docker" in result.detail
    assert not marker.exists()


@pytest.mark.parametrize("passed,exit_code", [(True, 0), (False, 1)])
def test_agent_cli_measures_success_instead_of_calibration(monkeypatch, spec, passed, exit_code):
    result = runner.RunResult(spec.task_id, "agent", "docker", passed, None,
                               0 if passed else 1, 0.1, 1, "runs/example")
    monkeypatch.setattr(runner, "run_task", lambda *a, **k: result)
    assert cli.main(["run", "-t", spec.task_id, "-m", "agent", "-b", "docker", "--agent-cmd", "true"]) == exit_code
    summary = runner.summarise([result])
    assert summary["calibration_total"] == 0
    assert summary["miscalibrated"] == []
    assert result.calibrated is None


@pytest.mark.parametrize("code,output", [(2, "1 error"), (5, "no tests ran"), (1, "1 error"), (0, "0 passed")])
def test_execution_errors_do_not_count_as_negative_calibration(code, output):
    with pytest.raises(runner.HarnessError):
        runner._verdict(subprocess.CompletedProcess([], code, output, ""))


def test_docker_agent_and_verifier_have_separate_mounts(monkeypatch, spec, tmp_path):
    commands = []
    def run(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "1 passed" if "pytest" in command else "", "")
    monkeypatch.setattr(runner, "_docker_available", lambda: True)
    monkeypatch.setattr(runner.subprocess, "run", run)
    assert runner._run_docker(spec, "agent", tmp_path, 123, "true", io.StringIO()) == (True, 0)
    build, agent, verifier = commands
    agent_text = " ".join(agent)
    assert "/solution" not in agent_text and "/verifier" not in agent_text
    assert "/bench" not in agent_text and "STB_SEED" not in agent_text
    assert "/instruction.md:ro" in agent_text
    assert "/verifier:ro" in " ".join(verifier)
    assert "/solution" not in " ".join(verifier)


def test_build_failure_cannot_calibrate_null_mode(monkeypatch, spec, tmp_path):
    monkeypatch.setattr(runner, "_docker_available", lambda: True)
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess([], 1, "", "build failed"))
    result = runner.run_task(spec, mode="null", backend="docker", runs_dir=tmp_path)
    assert result.error and result.calibrated is False
