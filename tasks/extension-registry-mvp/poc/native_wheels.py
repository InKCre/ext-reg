#!/usr/bin/env python3
"""Disposable PoC: build and load the six Core Extensions as native wheels."""

from __future__ import annotations

import argparse
import configparser
import functools
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import threading
import tomllib
import zipfile
from email.parser import Parser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

EXTENSION_IDS = ("github", "learn_english", "mail", "rss", "telegram", "twitter")


def run(*args: str, cwd: Path | None = None, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {args!r}\n{result.stdout}")
    return result.stdout


def quoted_list(values: list[str]) -> str:
    return "[" + ", ".join(json.dumps(value) for value in values) + "]"


def build_pyproject(extension_id: str, source: Path) -> str:
    original = tomllib.loads((source / "pyproject.toml").read_text())
    project = original["project"]
    nickname = (
        original.get("tool", {}).get("inkcre-ext", {}).get("nickname")
        or original.get("inkcre-ext", {}).get("nickname")
        or extension_id
    )
    return f"""\
[build-system]
requires = ["setuptools>=77", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = {json.dumps(project["name"])}
version = {json.dumps(project["version"])}
description = {json.dumps(project.get("description") or f"InKCre {extension_id} Extension")}
readme = "README.md"
requires-python = ">=3.12,<3.13"
dependencies = {quoted_list(project.get("dependencies", []))}

[project.entry-points."inkcre.core.extensions"]
{json.dumps(extension_id)} = {json.dumps(f"extensions.{extension_id}:Extension")}

[tool.inkcre-extension]
name = {json.dumps(f"inkcre/{extension_id}")}
nickname = {json.dumps(nickname)}
host-sdk = "core-py"
host-sdk-version = ">=0.1.0,<0.2.0"

[tool.setuptools.packages.find]
where = ["."]
include = ["extensions.{extension_id}*"]
namespaces = true
"""


def inspect_wheel(wheel: Path, extension_id: str) -> dict[str, object]:
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        entry_name = next(name for name in names if name.endswith(".dist-info/entry_points.txt"))
        metadata_name = next(name for name in names if name.endswith(".dist-info/METADATA"))
        parser = configparser.ConfigParser()
        parser.read_string(archive.read(entry_name).decode())
        entry = parser["inkcre.core.extensions"][extension_id]
        metadata = Parser().parsestr(archive.read(metadata_name).decode())
    package_prefix = f"extensions/{extension_id}/"
    return {
        "filename": wheel.name,
        "entry_point": entry,
        "project": metadata["Name"],
        "version": metadata["Version"],
        "requires_python": metadata["Requires-Python"],
        "namespace_init_present": "extensions/__init__.py" in names,
        "package_files": sum(name.startswith(package_prefix) for name in names),
    }


def normalized_project(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


class QuietSimpleHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


def prove_simple_install(
    *, core_python: Path, dist: Path, reports: dict[str, object], root: Path
) -> list[str]:
    packages = root / "packages"
    simple = root / "simple"
    packages.mkdir(parents=True)
    simple.mkdir()
    downloaded: list[str] = []
    for report in reports.values():
        record = report if isinstance(report, dict) else {}
        wheel = dist / str(record["filename"])
        shutil.copy2(wheel, packages / wheel.name)
        digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
        project_root = simple / normalized_project(str(record["project"]))
        project_root.mkdir()
        project_root.joinpath("index.html").write_text(
            '<!doctype html><a href="../../packages/'
            + html.escape(wheel.name)
            + "#sha256="
            + digest
            + '" data-requires-python="'
            + html.escape(str(record["requires_python"]), quote=True)
            + '">'
            + html.escape(wheel.name)
            + "</a>"
        )

    handler = functools.partial(QuietSimpleHandler, directory=str(root))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        download_root = root / "downloads"
        download_root.mkdir()
        index_url = f"http://127.0.0.1:{server.server_port}/simple/"
        for report in reports.values():
            record = report if isinstance(report, dict) else {}
            run(
                str(core_python),
                "-m",
                "pip",
                "download",
                "--disable-pip-version-check",
                "--no-input",
                "--no-deps",
                "--only-binary=:all:",
                "--index-url",
                index_url,
                "--dest",
                str(download_root),
                f"{record['project']}=={record['version']}",
            )
            downloaded.append(str(record["filename"]))
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
    return sorted(downloaded)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--core-repo", type=Path, required=True)
    parser.add_argument("--core-python", type=Path, required=True)
    options = parser.parse_args()
    core_repo = options.core_repo.resolve()
    core_python = Path(os.path.abspath(options.core_python))

    with tempfile.TemporaryDirectory(prefix="inkcre-native-wheel-poc-") as raw_tmp:
        tmp = Path(raw_tmp)
        archive_path = tmp / "extensions.tar"
        archive_path.write_bytes(
            subprocess.check_output(
                ["git", "-C", str(core_repo), "archive", "origin/main", "extensions"]
            )
        )
        source_root = tmp / "source"
        source_root.mkdir()
        with tarfile.open(archive_path) as archive:
            archive.extractall(source_root, filter="data")

        dist = tmp / "dist"
        dist.mkdir()
        reports: dict[str, object] = {}
        for extension_id in EXTENSION_IDS:
            source = source_root / "extensions" / extension_id
            build_root = tmp / "build" / extension_id
            package_root = build_root / "extensions" / extension_id
            shutil.copytree(
                source,
                package_root,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "pdm.lock", "pyproject.toml"),
            )
            readme = source / "README.md"
            (build_root / "README.md").write_text(
                readme.read_text() if readme.exists() else f"# {extension_id}\n"
            )
            (build_root / "pyproject.toml").write_text(build_pyproject(extension_id, source))
            run("uv", "build", "--wheel", "--out-dir", str(dist), str(build_root))
            wheel = next(dist.glob(f"*{extension_id.replace('_', '-')}*0.1.0*.whl"), None)
            if wheel is None:
                candidates = sorted(dist.glob("*.whl"), key=lambda path: path.stat().st_mtime)
                wheel = candidates[-1]
            reports[extension_id] = inspect_wheel(wheel, extension_id)

        site = tmp / "site"
        wheels = [str(path) for path in sorted(dist.glob("*.whl"))]
        simple_downloads = prove_simple_install(
            core_python=core_python,
            dist=dist,
            reports=reports,
            root=tmp / "index",
        )
        run(
            str(core_python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            "--no-deps",
            "--target",
            str(site),
            *wheels,
        )
        loader = """
import importlib.metadata
import inspect
import json

from app.business.info_base.resolver.main import ResolverManager
from app.business.source.main import SourceManager

result = {}
runtime_errors = []
for ep in importlib.metadata.entry_points(group='inkcre.core.extensions'):
    cls = ep.load()
    for phase in ('_init_sources', '_init_resolvers'):
        try:
            getattr(cls, phase)()
        except Exception as error:
            runtime_errors.append({
                'extension': ep.name,
                'phase': phase,
                'error': f'{type(error).__name__}: {error}',
            })
    result[ep.name] = {
        'value': ep.value,
        'class': f'{cls.__module__}:{cls.__qualname__}',
        'module_file': inspect.getfile(cls),
    }
print(json.dumps({
    'extensions': result,
    'source_types': sorted(
        key for key in SourceManager._SOURCE_CLASSES if key.startswith('extensions.')
    ),
    'resolver_types': sorted(
        str(key) for key, cls in ResolverManager.RESOLVER_CLS.items()
        if cls.__module__.startswith('extensions.')
    ),
    'runtime_errors': runtime_errors,
}, sort_keys=True))
"""
        environment = os.environ.copy()
        python_path = [str(site), str(core_repo)]
        if environment.get("PYTHONPATH"):
            python_path.append(environment["PYTHONPATH"])
        environment["PYTHONPATH"] = os.pathsep.join(python_path)
        environment.setdefault("DATABASE_URL", "postgresql+psycopg://poc:poc@127.0.0.1/poc")
        environment.setdefault("JWT_SECRET", "native-wheel-poc-only-secret-00000000")
        runtime = json.loads(run(str(core_python), "-c", loader, env=environment).splitlines()[-1])
        loaded = runtime["extensions"]
        expected = set(EXTENSION_IDS)
        if set(loaded) != expected:
            raise RuntimeError(f"entry-point set mismatch: {set(loaded)!r} != {expected!r}")
        if any(not Path(record["module_file"]).is_relative_to(site) for record in loaded.values()):
            raise RuntimeError(f"an Extension loaded outside the wheel site: {loaded!r}")
        if any(report["namespace_init_present"] for report in reports.values()):
            raise RuntimeError("a wheel unexpectedly owns extensions/__init__.py")

        print(
            json.dumps(
                {
                    "python": run(str(core_python), "--version").strip(),
                    "wheels": reports,
                    "simple_downloads": simple_downloads,
                    "loaded": loaded,
                    "source_types": runtime["source_types"],
                    "resolver_types": runtime["resolver_types"],
                    "runtime_errors": runtime["runtime_errors"],
                },
                indent=2,
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
