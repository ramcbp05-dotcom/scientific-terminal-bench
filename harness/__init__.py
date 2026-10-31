"""Harness for the Scientific Terminal Benchmark Suite.

The package contains three pieces:

``models``       dataclasses describing a task on disk (``task.yaml``).
``runner``       executes a task in a sandbox (local or Docker) and verifies it.
``stb_verify``   helpers that task verifiers import.
"""

__version__ = "0.1.0"
