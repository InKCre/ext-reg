"""Regenerate package-local consumers from canonical checked contracts."""

import argparse
import filecmp
import subprocess
import sys
import tempfile
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
REPOSITORY = PACKAGE.parents[1]
GENERATED = PACKAGE / "src/inkcre_extension_runtime_core_py/generated"
COMMON = [
    sys.executable,
    "-m",
    "datamodel_code_generator",
    "--output-model-type",
    "pydantic_v2.BaseModel",
    "--target-python-version",
    "3.12",
    "--use-standard-collections",
    "--use-union-operator",
    "--collapse-root-models",
    "--disable-timestamp",
]


def generate(source: Path, input_type: str, output: Path) -> None:
    subprocess.run(
        [*COMMON, "--input", str(source), "--input-file-type", input_type, "--output", str(output)],
        cwd=REPOSITORY,
        check=True,
    )


def generate_all(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    generate(REPOSITORY / "contracts/openapi.json", "openapi", output / "registry.py")
    generate(
        REPOSITORY / "contracts/python-installed-extension.schema.json",
        "jsonschema",
        output / "installed.py",
    )
    subprocess.run(
        ["ruff", "format", str(output / "registry.py"), str(output / "installed.py")],
        cwd=REPOSITORY,
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    if not arguments.check:
        generate_all(GENERATED)
        return
    with tempfile.TemporaryDirectory(prefix="inkcre-runtime-contracts-") as temporary:
        expected = Path(temporary)
        generate_all(expected)
        stale = [
            name
            for name in ("registry.py", "installed.py")
            if not filecmp.cmp(expected / name, GENERATED / name, shallow=False)
        ]
    if stale:
        parser.error(f"generated contract consumers are stale: {', '.join(stale)}")


if __name__ == "__main__":
    main()
