"""Install the Core-Py wheel alone and exercise its supported Host lifecycle contracts."""

from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
import tomllib
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check_core_runtime(wheel: Path | None = None) -> None:
    if wheel is None:
        project = tomllib.loads((ROOT / "runtimes/core-py/pyproject.toml").read_text())["project"]
        wheel = (
            ROOT
            / "dist"
            / (f"{project['name'].replace('-', '_')}-{project['version']}-py3-none-any.whl")
        )
    wheel = wheel.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="core-runtime-wheel-check-") as temporary:
        environment = Path(temporary)
        venv.EnvBuilder(with_pip=True, symlinks=os.name != "nt").create(environment)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run(
            [
                str(python),
                "-I",
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                str(wheel),
                "httpx>=0.28,<0.29",
            ],
            cwd=environment,
            check=True,
        )
        subprocess.run([str(python), "-I", "-m", "pip", "check"], cwd=environment, check=True)
        subprocess.run(
            [str(python), "-I", str(ROOT / "runtimes/core-py/check_lifecycle.py"), "--installed"],
            cwd=environment,
            check=True,
        )
    print("Core-Py wheel isolated installation and public lifecycle contract passed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path)
    check_core_runtime(parser.parse_args().wheel)
