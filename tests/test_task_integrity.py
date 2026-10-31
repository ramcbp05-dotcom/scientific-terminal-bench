"""Repo-level checks on the task collection itself.

These are not task verifiers: they guard the properties a benchmark suite has
to hold as a whole: that the layout contract is met, that difficulty is spread
across the tiers, that nothing in the agent-visible material leaks the answer,
and that every task ships the null/hardcode counterexamples that make its
calibration claim checkable.
"""

from __future__ import annotations

import re
import stat
from pathlib import Path

import pytest
import yaml

from harness import models

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = REPO_ROOT / "tasks"

SPECS = models.discover(TASKS_DIR)
IDS = [s.task_id for s in SPECS]


def test_suite_size_is_in_the_advertised_range():
    assert 10 <= len(SPECS) <= 15, (
        f"the README advertises 10-15 tasks; found {len(SPECS)}"
    )


def test_task_ids_are_unique_and_kebab_case():
    assert len(set(IDS)) == len(IDS), "duplicate task ids"
    for task_id in IDS:
        assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", task_id), (
            f"{task_id!r} is not kebab-case"
        )


def test_every_tier_is_represented():
    counts = {tier: sum(s.difficulty == tier for s in SPECS)
              for tier in models.DIFFICULTIES}
    for tier, count in counts.items():
        assert count >= 2, (
            f"only {count} {tier} task(s); a benchmark with an empty tier cannot "
            f"separate capability levels. Distribution: {counts}"
        )


@pytest.mark.parametrize("spec", SPECS, ids=IDS)
def test_metadata_is_complete(spec):
    assert spec.tags, f"{spec.task_id}: no tags"
    assert all(t == t.lower() for t in spec.tags), f"{spec.task_id}: tags must be lowercase"
    assert 30 <= spec.timeout_sec <= 900, (
        f"{spec.task_id}: timeout_sec={spec.timeout_sec} is outside 30..900"
    )
    assert len(spec.summary.split()) >= 15, (
        f"{spec.task_id}: summary is too short to describe the defect"
    )
    assert len(spec.title) <= 90, f"{spec.task_id}: title is too long for a table"


@pytest.mark.parametrize("spec", SPECS, ids=IDS)
def test_instructions_state_the_contract(spec):
    text = spec.instructions_path.read_text()
    assert text.startswith("# "), f"{spec.task_id}: instructions must open with an H1"
    assert len(text.split()) >= 80, (
        f"{spec.task_id}: instructions are too thin to be unambiguous"
    )
    assert "## Task" in text or "## Task\n" in text, (
        f"{spec.task_id}: instructions have no '## Task' section"
    )
    assert "python " in text, (
        f"{spec.task_id}: instructions never show the command line the grader uses"
    )


@pytest.mark.parametrize("spec", SPECS, ids=IDS)
def test_agent_visible_material_does_not_leak_the_solution(spec):
    """The environment and instructions must not mention the hidden directories."""
    visible = [spec.instructions_path] + sorted(spec.environment_dir.rglob("*"))
    for path in visible:
        if not path.is_file():
            continue
        text = path.read_text(errors="replace")
        for leak in ("solution/apply.sh", "solution/fixed", "verifier/test_task.py"):
            assert leak not in text, f"{path.relative_to(spec.root)} mentions {leak}"


@pytest.mark.parametrize("spec", SPECS, ids=IDS)
def test_oracle_and_counterexample_scripts_exist(spec):
    assert spec.oracle_script.is_file(), f"{spec.task_id}: no solution/apply.sh"
    assert spec.hardcode_script.is_file(), (
        f"{spec.task_id}: no solution/hardcode.sh. Every task needs a plausible "
        "wrong patch, otherwise its 'a cheating solution fails' claim is untested."
    )
    for script in (spec.oracle_script, spec.hardcode_script):
        text = script.read_text()
        assert text.startswith("#!/usr/bin/env bash"), f"{script.name}: missing shebang"
        assert "set -euo pipefail" in text, f"{script.name}: missing strict mode"
        assert not re.search(r"^\s*python\s", text, re.MULTILINE), (
            f"{script.name}: calls a bare `python`. Use \"${{PYTHON:-python3}}\" so the "
            "script works on hosts where only python3 is on PATH."
        )


@pytest.mark.parametrize("spec", SPECS, ids=IDS)
def test_verifier_uses_the_per_run_seed(spec):
    """A verifier with fixed expectations can be satisfied by a hardcoded answer."""
    sources = [p.read_text() for p in sorted(spec.verifier_dir.glob("test_*.py"))]
    joined = "\n".join(sources)
    assert "rng(" in joined, (
        f"{spec.task_id}: the verifier never calls rng(), so its probe data is the "
        "same on every run and a memorised answer would pass"
    )
    assert "from harness.stb_verify import" in joined, (
        f"{spec.task_id}: the verifier does not use the shared helper module"
    )


@pytest.mark.parametrize("spec", SPECS, ids=IDS)
def test_verifier_failures_carry_an_explanation(spec):
    """Bare asserts give an agent nothing to act on."""
    for path in sorted(spec.verifier_dir.glob("test_*.py")):
        lines = path.read_text().splitlines()
        bare = [
            (i + 1, line.strip())
            for i, line in enumerate(lines)
            if re.match(r"^\s*assert .+", line)
            and "," not in line
            and not line.rstrip().endswith("(")
            and "assert_close" not in line
            and not re.search(r"assert \w+ ==", line)
        ]
        assert not bare, (
            f"{path.relative_to(spec.root)}: asserts without a message at lines "
            f"{[n for n, _ in bare]}"
        )


@pytest.mark.parametrize("spec", SPECS, ids=IDS)
def test_dockerfile_pins_its_dependencies(spec):
    text = spec.dockerfile.read_text()
    assert re.search(r"^FROM python:3\.\d+", text, re.MULTILINE), (
        f"{spec.task_id}: Dockerfile must start from a pinned python base image"
    )
    pip_lines = [l for l in text.splitlines() if "pip install" in l]
    assert pip_lines, f"{spec.task_id}: Dockerfile installs nothing"
    for line in pip_lines:
        assert "==" in line, (
            f"{spec.task_id}: unpinned pip install ({line.strip()}); a benchmark that "
            "floats its dependencies stops being reproducible"
        )


@pytest.mark.parametrize("spec", SPECS, ids=IDS)
def test_environment_is_not_empty_and_has_no_junk(spec):
    files = [p for p in spec.environment_dir.rglob("*") if p.is_file()]
    assert files, f"{spec.task_id}: environment/ is empty"
    for path in files:
        assert "__pycache__" not in path.parts, f"{path} is build junk"
        assert path.suffix not in (".pyc", ".pyo"), f"{path} is build junk"


def test_task_yaml_round_trips():
    for spec in SPECS:
        data = yaml.safe_load((spec.root / "task.yaml").read_text())
        assert data["id"] == spec.task_id
        assert data["difficulty"] in models.DIFFICULTIES
