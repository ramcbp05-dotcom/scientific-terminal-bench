"""Live container checks, enabled explicitly locally and required in Docker CI."""
import os
from pathlib import Path
import pytest
from harness import models, runner

pytestmark = pytest.mark.skipif(os.environ.get("STB_TEST_DOCKER") != "1", reason="set STB_TEST_DOCKER=1 to run live Docker checks")


def task():
    return next(s for s in models.discover(runner.REPO_ROOT / "tasks") if s.task_id == "fix-nan-propagation")


@pytest.mark.parametrize("mode,passed", [("oracle", True), ("null", False), ("hardcode", False)])
def test_live_docker_calibration(tmp_path, mode, passed):
    result = runner.run_task(task(), mode=mode, backend="docker", runs_dir=tmp_path)
    assert not result.error, result.detail
    assert result.passed is passed and result.calibrated is True


def test_live_agent_cannot_read_reference_but_valid_submission_passes(tmp_path):
    spec = task()
    source = (spec.root / "solution/fixed/summarize_sensor.py").read_text()
    # This is a known-good submission fixture supplied by the test, not an
    # answer path exposed to normal agents.
    command = ("test ! -e /solution && test ! -e /verifier && test ! -e /bench && "
               "test -f /instruction.md && test -z \"${STB_SEED:-}\" && "
               "cat > summarize_sensor.py <<'SUBMISSION'\n" + source + "\nSUBMISSION\n")
    result = runner.run_task(spec, mode="agent", backend="docker", runs_dir=tmp_path, agent_cmd=command)
    assert not result.error, result.detail
    assert result.passed and result.successful and result.calibrated is None


def test_live_agent_reference_copy_fails(tmp_path):
    result = runner.run_task(task(), mode="agent", backend="docker", runs_dir=tmp_path,
                             agent_cmd="cp /solution/fixed/summarize_sensor.py .")
    assert result.error and not result.successful
    assert "agent command failed" in result.detail
