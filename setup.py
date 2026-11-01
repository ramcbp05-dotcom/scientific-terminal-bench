"""Include the checkout's benchmark inputs in binary distributions."""
from pathlib import Path
from shutil import copytree, ignore_patterns
from setuptools import setup
from setuptools.command.build_py import build_py


class BuildWithInputs(build_py):
    def run(self):
        super().run()
        root = Path(__file__).parent
        target = Path(self.build_lib) / 'harness' / "_data"
        for folder in ['tasks']:
            copytree(root / folder, target / folder, dirs_exist_ok=True,
                     ignore=ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"))


setup(cmdclass={"build_py": BuildWithInputs})
