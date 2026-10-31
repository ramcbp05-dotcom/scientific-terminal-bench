"""Task specification: the on-disk contract every task directory follows.

Layout of ``tasks/<task-id>/``::

    task.yaml            metadata parsed into :class:`TaskSpec`
    instructions.md      the only prose the agent is allowed to see
    Dockerfile           reproducible environment for the Docker backend
    environment/         copied verbatim into the agent's /workspace
    solution/apply.sh    oracle patch (never shown to the agent)
    solution/hardcode.sh optional cheating patch, used for null-ish runs
    verifier/test_*.py   pytest verifier (never shown to the agent)
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import yaml

DIFFICULTIES = ("easy", "medium", "hard")


class TaskSpecError(ValueError):
    """Raised when a ``task.yaml`` is malformed or the layout is incomplete."""


@dataclasses.dataclass(frozen=True)
class TaskSpec:
    task_id: str
    title: str
    difficulty: str
    tags: tuple[str, ...]
    timeout_sec: int
    summary: str
    root: Path

    # --- derived paths -------------------------------------------------
    @property
    def instructions_path(self) -> Path:
        return self.root / "instructions.md"

    @property
    def environment_dir(self) -> Path:
        return self.root / "environment"

    @property
    def dockerfile(self) -> Path:
        return self.root / "Dockerfile"

    @property
    def oracle_script(self) -> Path:
        return self.root / "solution" / "apply.sh"

    @property
    def hardcode_script(self) -> Path:
        return self.root / "solution" / "hardcode.sh"

    @property
    def verifier_dir(self) -> Path:
        return self.root / "verifier"

    @classmethod
    def load(cls, root: Path) -> "TaskSpec":
        root = Path(root)
        meta_path = root / "task.yaml"
        if not meta_path.is_file():
            raise TaskSpecError(f"{root}: missing task.yaml")
        data: dict[str, Any] = yaml.safe_load(meta_path.read_text()) or {}

        missing = [k for k in ("id", "title", "difficulty", "summary") if k not in data]
        if missing:
            raise TaskSpecError(f"{meta_path}: missing keys {missing}")
        if data["difficulty"] not in DIFFICULTIES:
            raise TaskSpecError(
                f"{meta_path}: difficulty {data['difficulty']!r} not in {DIFFICULTIES}"
            )
        if data["id"] != root.name:
            raise TaskSpecError(f"{meta_path}: id {data['id']!r} != directory {root.name!r}")

        spec = cls(
            task_id=data["id"],
            title=data["title"],
            difficulty=data["difficulty"],
            tags=tuple(data.get("tags", ())),
            timeout_sec=int(data.get("timeout_sec", 300)),
            summary=data["summary"],
            root=root,
        )
        spec.validate_layout()
        return spec

    def validate_layout(self) -> None:
        required = [
            self.instructions_path,
            self.environment_dir,
            self.dockerfile,
            self.oracle_script,
            self.verifier_dir,
        ]
        for path in required:
            if not path.exists():
                raise TaskSpecError(f"{self.task_id}: missing {path.relative_to(self.root)}")
        if not any(self.verifier_dir.glob("test_*.py")):
            raise TaskSpecError(f"{self.task_id}: verifier/ has no test_*.py")


def discover(tasks_dir: Path) -> list[TaskSpec]:
    """Load every task under ``tasks_dir``, sorted by id."""
    tasks_dir = Path(tasks_dir)
    specs = [
        TaskSpec.load(child)
        for child in sorted(tasks_dir.iterdir())
        if child.is_dir() and (child / "task.yaml").is_file()
    ]
    return specs
