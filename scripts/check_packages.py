"""Install the built Registry and Toolkit wheels without workspace/editable imports."""

from __future__ import annotations

import email
import os
import subprocess
import tempfile
import tomllib
import venv
import zipfile
from pathlib import Path

from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    wheels = []
    for directory in (ROOT, ROOT / "toolkit"):
        project = tomllib.loads((directory / "pyproject.toml").read_text())["project"]
        wheels.append(
            ROOT
            / "dist"
            / f"{project['name'].replace('-', '_')}-{project['version']}-py3-none-any.whl"
        )
    with zipfile.ZipFile(wheels[0]) as archive:
        metadata_path = next(
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        )
        metadata = email.message_from_bytes(archive.read(metadata_path))
    requirement = next(
        item
        for value in metadata.get_all("Requires-Dist", [])
        if (item := Requirement(value)).name == "inkcre-extension-toolkit"
    )
    # 0.2.1 lacks documentation admission, even if the workspace import succeeds.
    assert "0.2.1" not in requirement.specifier, (
        "Registry wheel admits Toolkit without documentation API"
    )
    with tempfile.TemporaryDirectory(prefix="registry-wheel-check-") as temporary:
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
                *map(str, wheels),
            ],
            cwd=environment,
            check=True,
        )
        subprocess.run([str(python), "-I", "-m", "pip", "check"], cwd=environment, check=True)
        subprocess.run(
            [
                str(python),
                "-I",
                "-c",
                "from inkcre_extension_registry.service.app import create_app; "
                "from inkcre_extension_toolkit.documentation import inspect_documentation; "
                "assert create_app().openapi()['paths']['/v1/documentation-hosting']",
            ],
            cwd=environment,
            check=True,
        )
    print("Registry and Toolkit wheel metadata, isolated installation and service import passed.")


if __name__ == "__main__":
    main()
