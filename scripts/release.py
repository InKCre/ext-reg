"""Validate and prepare the independent Python release units."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRAGMENT_TYPES = ("added", "changed", "deprecated", "removed", "fixed", "security")
FRAGMENT_PATTERN = re.compile(rf"^(?:[+][^.]+|[^+.][^.]*)[.]({'|'.join(FRAGMENT_TYPES)})[.]md$")
BUMPS = {
    "added": "minor",
    "changed": "patch",
    "deprecated": "minor",
    "removed": "major",
    "fixed": "patch",
    "security": "patch",
}
BUMP_RANK = {"patch": 1, "minor": 2, "major": 3}


class ReleaseError(RuntimeError):
    """The repository does not describe an unambiguous release."""


@dataclass(frozen=True)
class Project:
    key: str
    directory: Path
    version: tuple[int, int, int]

    @property
    def pyproject(self) -> Path:
        return self.directory / "pyproject.toml"

    @property
    def changelog(self) -> Path:
        return self.directory / "CHANGELOG.md"

    @property
    def fragments(self) -> Path:
        return self.directory / ".changes"


def run(arguments: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(arguments, cwd=ROOT, check=False, capture_output=True, text=True)
    if check and result.returncode:
        raise ReleaseError((result.stderr or result.stdout).strip())
    return result


def git(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["git", *arguments], check=check)


def parse_version(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"(0|[1-9][0-9]*)[.](0|[1-9][0-9]*)[.](0|[1-9][0-9]*)", value)
    if match is None:
        raise ReleaseError(f"{value!r} is not a stable SemVer")
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch)


def projects() -> tuple[Project, ...]:
    root = tomllib.loads((ROOT / "pyproject.toml").read_text())
    directories = [ROOT]
    directories.extend(ROOT / item for item in root["tool"]["pdm"]["workspace"]["members"])
    result = []
    for directory in directories:
        project = tomllib.loads((directory / "pyproject.toml").read_text())["project"]
        name = project["name"]
        if name == "inkcre-extension-registry":
            key = "registry"
        elif name.startswith("inkcre-extension-"):
            key = name.removeprefix("inkcre-extension-")
        else:
            raise ReleaseError(f"unknown Python release unit {name!r}")
        result.append(Project(key, directory, parse_version(project["version"])))
    return tuple(result)


def fragments(project: Project) -> tuple[Path, ...]:
    return tuple(
        path
        for path in sorted(project.fragments.glob("*"))
        if path.is_file() and path.name != ".gitkeep"
    )


def validate_fragments(project: Project) -> list[str]:
    problems = []
    for path in fragments(project):
        if FRAGMENT_PATTERN.fullmatch(path.name) is None:
            problems.append(f"{project.key}: invalid fragment name {path.name!r}")
        if not path.read_text().strip():
            problems.append(f"{project.key}: empty fragment {path.name!r}")
    if not problems and fragments(project):
        draft = run(
            [
                sys.executable,
                "-m",
                "towncrier",
                "build",
                "--draft",
                "--config",
                str(ROOT / "towncrier.toml"),
                "--dir",
                str(project.directory),
                "--version",
                ".".join(map(str, project.version)),
            ],
            check=False,
        )
        if draft.returncode:
            problems.append(f"{project.key}: {(draft.stderr or draft.stdout).strip()}")
    return problems


def show_version(project: Project, revision: str) -> tuple[int, int, int] | None:
    path = project.pyproject.relative_to(ROOT).as_posix()
    result = git("show", f"{revision}:{path}", check=False)
    if result.returncode:
        return None
    return parse_version(tomllib.loads(result.stdout)["project"]["version"])


def changed(base: str) -> tuple[tuple[str, str], ...]:
    output = git("diff", "--no-renames", "--name-status", f"{base}...HEAD").stdout
    result = []
    for line in output.splitlines():
        status, path = line.split("\t", 1)
        result.append((status, path))
    return tuple(result)


def content_at(path: Path, revision: str) -> str | None:
    result = git("show", f"{revision}:{path.relative_to(ROOT).as_posix()}", check=False)
    return result.stdout if result.returncode == 0 else None


def relative(project: Project, path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def affected_projects(paths: set[str], items: tuple[Project, ...]) -> set[str]:
    affected = set()
    for project in items:
        if project.key == "registry":
            owned = any(
                path == "pyproject.toml"
                or path == "Dockerfile"
                or path.startswith(("src/", "migrations/", "web/"))
                for path in paths
            )
        else:
            prefix = relative(project, project.directory) + "/"
            excluded = {
                relative(project, project.changelog),
                relative(project, project.pyproject),
            }
            owned = any(
                path.startswith(prefix) and path not in excluded and "/.changes/" not in f"/{path}"
                for path in paths
            )
            if relative(project, project.pyproject) in paths:
                owned = True
        if owned:
            affected.add(project.key)
    return affected


def check(base: str | None) -> None:
    items = projects()
    problems = [problem for project in items for problem in validate_fragments(project)]
    if base is None:
        if problems:
            raise ReleaseError("\n".join(problems))
        return

    changes = changed(base)
    paths = {path for _status, path in changes}
    version_changed = {
        project.key
        for project in items
        if show_version(project, base) not in {None, project.version}
    }
    release_pr = bool(version_changed)
    if release_pr:
        allowed = {"pdm.lock"}
        prefixes = []
        for project in items:
            allowed.update(
                {relative(project, project.pyproject), relative(project, project.changelog)}
            )
            prefixes.append(relative(project, project.fragments) + "/")
        unexpected = sorted(
            path for path in paths if path not in allowed and not path.startswith(tuple(prefixes))
        )
        if unexpected:
            problems.append("release PR contains behavior changes: " + ", ".join(unexpected))
        for project in items:
            changelog_changed = relative(project, project.changelog) in paths
            if (project.key in version_changed) != changelog_changed:
                problems.append(f"{project.key}: version and changelog must change together")
    else:
        affected = affected_projects(paths, items)
        for project in items:
            prefix = relative(project, project.fragments) + "/"
            fragment_added = any(
                status in {"A", "M"} and path.startswith(prefix) and not path.endswith("/.gitkeep")
                for status, path in changes
            )
            if project.key in affected and not fragment_added:
                problems.append(f"{project.key}: behavior changed without a Towncrier fragment")
            if relative(project, project.changelog) in paths:
                marker = "<!-- towncrier release notes start -->"
                previous = content_at(project.changelog, base)
                adopting_towncrier = marker in project.changelog.read_text() and (
                    previous is None or marker not in previous
                )
                if not adopting_towncrier:
                    problems.append(f"{project.key}: feature PR cannot edit its changelog")
    if problems:
        raise ReleaseError("\n".join(problems))


def bump(project: Project) -> tuple[int, int, int]:
    kinds = []
    for path in fragments(project):
        match = FRAGMENT_PATTERN.fullmatch(path.name)
        if match is None:
            raise ReleaseError(f"{project.key}: invalid fragment name {path.name!r}")
        kinds.append(match.group(1))
    level = max((BUMPS[kind] for kind in kinds), key=BUMP_RANK.__getitem__)
    major, minor, patch = project.version
    if level == "major" and major == 0:
        level = "minor"
    if level == "major":
        return major + 1, 0, 0
    if level == "minor":
        return major, minor + 1, 0
    return major, minor, patch + 1


def replace_version(path: Path, version: tuple[int, int, int]) -> None:
    content = path.read_text()
    updated, count = re.subn(
        r'(?m)^(version = ")[^"]+("\s*)$',
        rf"\g<1>{'.'.join(map(str, version))}\g<2>",
        content,
        count=1,
    )
    if count != 1:
        raise ReleaseError(f"could not update {path}")
    path.write_text(updated)


def prepare() -> None:
    items = tuple(project for project in projects() if fragments(project))
    problems = [problem for project in items for problem in validate_fragments(project)]
    if problems:
        raise ReleaseError("\n".join(problems))
    for project in items:
        version = bump(project)
        run(
            [
                sys.executable,
                "-m",
                "towncrier",
                "build",
                "--config",
                str(ROOT / "towncrier.toml"),
                "--dir",
                str(project.directory),
                "--version",
                ".".join(map(str, version)),
                "--yes",
            ]
        )
        run(
            [
                "pnpm",
                "exec",
                "prettier",
                "--write",
                str(project.changelog.relative_to(ROOT)),
            ]
        )
        replace_version(project.pyproject, version)
    if items:
        run(["pdm", "lock", "--update-reuse"])
    print("\n".join(project.key for project in items))


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    check_parser = commands.add_parser("check")
    check_parser.add_argument("--base", default=os.environ.get("BASE_REVISION"))
    commands.add_parser("prepare")
    args = parser.parse_args()
    try:
        check(args.base) if args.command == "check" else prepare()
    except ReleaseError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
