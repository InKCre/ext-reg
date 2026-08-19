"""Installed-record discovery and standard-pip acquisition."""

from __future__ import annotations

import importlib
import importlib.metadata
import json
import os
import subprocess
import sys
import sysconfig
import tempfile
import typing
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pydantic
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version
from semantic_version import Version as SemVer

from .contracts import ExtensionReleaseDescriptor, InstalledExtensionRecord, PythonReleaseDescriptor
from .errors import (
    ExtensionAcquisitionError,
    ExtensionEntryPointError,
    ExtensionRestartRequiredError,
)
from .release import _validate_entry_point, _validate_host, simple_project_and_index_urls

INSTALLED_RECORD = "inkcre-extension.json"


def _python_project_version(release_version: str) -> str:
    try:
        parsed = SemVer(release_version)
    except ValueError as error:
        raise ExtensionEntryPointError("Extension Release version is invalid") from error
    base = f"{parsed.major}.{parsed.minor}.{parsed.patch}"
    if not parsed.prerelease:
        return base
    if (
        len(parsed.prerelease) != 2
        or parsed.prerelease[0] not in {"a", "b", "rc"}
        or not parsed.prerelease[1].isdigit()
    ):
        raise ExtensionEntryPointError("Extension prerelease has no lossless PEP 440 mapping")
    return f"{base}{parsed.prerelease[0]}{parsed.prerelease[1]}"


@dataclass(frozen=True)
class AcquiredDistribution:
    distribution: importlib.metadata.Distribution
    record: InstalledExtensionRecord
    entry_point: importlib.metadata.EntryPoint

    @classmethod
    def discover(
        cls,
        name: str,
        version: str,
        host_version: str,
        *,
        distributions: typing.Iterable[importlib.metadata.Distribution] | None = None,
    ) -> AcquiredDistribution | None:
        installed = tuple(
            importlib.metadata.distributions() if distributions is None else distributions
        )
        records: list[tuple[importlib.metadata.Distribution, InstalledExtensionRecord]] = []
        for distribution in installed:
            raw = distribution.read_text(INSTALLED_RECORD)
            if raw is None:
                continue
            try:
                record = InstalledExtensionRecord.model_validate_json(raw)
            except pydantic.ValidationError as error:
                raise ExtensionEntryPointError("Installed Extension record is invalid") from error
            if (record.name, record.version) != (name, version):
                continue
            records.append((distribution, record))
        if not records:
            return None
        projects = {canonicalize_name(record.python.project) for _, record in records}
        if len(projects) != 1:
            raise ExtensionEntryPointError("Multiple distributions own the exact Extension Release")
        project = projects.pop()
        owners = [
            distribution
            for distribution in installed
            if canonicalize_name(distribution.metadata["Name"] or "") == project
        ]
        if len(owners) != 1:
            raise ExtensionEntryPointError(
                "Core interpreter does not contain exactly one installed Project owner"
            )
        matching = [record for distribution, record in records if distribution is owners[0]]
        if len(matching) != 1:
            raise ExtensionEntryPointError("Installed record is not owned by its declared Project")
        return cls._validate(owners[0], matching[0], host_version)

    @classmethod
    def _validate(
        cls,
        distribution: importlib.metadata.Distribution,
        record: InstalledExtensionRecord,
        host_version: str,
    ) -> AcquiredDistribution:
        project = canonicalize_name(record.python.project)
        if canonicalize_name(distribution.metadata["Name"] or "") != project:
            raise ExtensionEntryPointError("Installed record Project differs from Core Metadata")
        try:
            versions_equal = Version(distribution.version) == Version(record.python.project_version)
        except InvalidVersion as error:
            raise ExtensionEntryPointError("Installed Project version is invalid") from error
        expected_project_version = _python_project_version(record.version)
        if not versions_equal or record.python.project_version != expected_project_version:
            raise ExtensionEntryPointError(
                "Installed Project version differs from Extension Release"
            )
        _validate_host(record.host_sdk.name, record.host_sdk.version, host_version)
        ep = record.python.entry_point
        _validate_entry_point(ep.group, ep.name, ep.object)
        candidates = [
            item
            for item in distribution.entry_points
            if (item.group, item.name, item.value) == (ep.group, ep.name, ep.object)
        ]
        if len(candidates) != 1:
            raise ExtensionEntryPointError("Installed entry point differs from installed record")
        if distribution.files is None:
            raise ExtensionEntryPointError("Installed Project does not expose a file record")
        return cls(distribution, record, candidates[0])


class PipDistributionConsumer:
    _restart_required_reason: typing.ClassVar[str | None] = None

    def __init__(
        self,
        origin: str,
        runner: typing.Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        self.origin = origin
        self._runner = runner or self._run

    @staticmethod
    def _installed_versions() -> dict[str, str]:
        return {
            canonicalize_name(distribution.metadata["Name"] or ""): distribution.version
            for distribution in importlib.metadata.distributions()
            if distribution.metadata["Name"]
        }

    @classmethod
    def _preflight_report(
        cls, report_path: Path, extension_project: str
    ) -> list[dict[str, typing.Any]]:
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ExtensionAcquisitionError("pip dependency report is invalid") from error
        installs = report.get("install") if isinstance(report, dict) else None
        if not isinstance(installs, list) or any(not isinstance(item, dict) for item in installs):
            raise ExtensionAcquisitionError("pip produced an invalid install plan")
        installed = cls._installed_versions()
        planned_projects: set[str] = set()
        for item in installs:
            metadata = item.get("metadata")
            if not isinstance(metadata, dict):
                raise ExtensionAcquisitionError("pip install plan omits Core Metadata")
            name, version = metadata.get("name"), metadata.get("version")
            if not isinstance(name, str) or not isinstance(version, str):
                raise ExtensionAcquisitionError("pip install plan has invalid Core Metadata")
            project = canonicalize_name(name)
            planned_projects.add(project)
            current = installed.get(project)
            if (
                current is not None
                and Version(current) != Version(version)
                and project != extension_project
            ):
                raise ExtensionAcquisitionError(
                    f"pip plan would replace loaded Distribution {name} {current} with {version}"
                )
        if extension_project not in planned_projects:
            raise ExtensionAcquisitionError("pip did not plan the exact Extension Project")
        return typing.cast(list[dict[str, typing.Any]], installs)

    @staticmethod
    def _run(arguments: list[str]) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.update(
            {
                "PIP_CONFIG_FILE": os.devnull,
                "PIP_DISABLE_PIP_VERSION_CHECK": "1",
                "PIP_NO_INPUT": "1",
                "PYTHONNOUSERSITE": "1",
            }
        )
        return subprocess.run(
            [sys.executable, "-m", "pip", *arguments],
            text=True,
            capture_output=True,
            check=False,
            env=environment,
        )

    @staticmethod
    def _require_success(result: subprocess.CompletedProcess[str], operation: str) -> None:
        if result.returncode:
            raise ExtensionAcquisitionError(f"pip {operation} failed")

    @staticmethod
    def _validate_wheel(
        wheel: Path,
        release: ExtensionReleaseDescriptor,
        association: PythonReleaseDescriptor,
        host_version: str,
    ) -> None:
        package = association.entry_point.object.partition(":")[0].split(".")[:2]
        if len(package) != 2 or package != ["extensions", association.entry_point.name]:
            raise ExtensionAcquisitionError(
                "Extension entry point does not own one extensions.<name> package"
            )
        try:
            with zipfile.ZipFile(wheel) as archive:
                names = archive.namelist()
                records = [
                    name
                    for name in names
                    if name.endswith(".dist-info/inkcre-extension.json") and name.count("/") == 1
                ]
                if len(records) != 1:
                    raise ExtensionAcquisitionError(
                        "Wheel does not contain exactly one installed Extension record"
                    )
                record = InstalledExtensionRecord.model_validate_json(archive.read(records[0]))
                expected = (
                    release.name,
                    release.version,
                    canonicalize_name(association.project),
                    association.entry_point.group,
                    association.entry_point.name,
                    association.entry_point.object,
                )
                actual = (
                    record.name,
                    record.version,
                    canonicalize_name(record.python.project),
                    record.python.entry_point.group,
                    record.python.entry_point.name,
                    record.python.entry_point.object,
                )
                if actual != expected or record.python.project_version != _python_project_version(
                    release.version
                ):
                    raise ExtensionAcquisitionError(
                        "Wheel installed record differs from the exact Registry association"
                    )
                _validate_host(record.host_sdk.name, record.host_sdk.version, host_version)
                prefix = "/".join(package) + "/"
                dist_info = records[0].split("/", 1)[0] + "/"
                files = [name for name in names if not name.endswith("/")]
                if any(
                    "\\" in name or name.startswith("/") or ".." in Path(name).parts
                    for name in names
                ):
                    raise ExtensionAcquisitionError("Wheel contains a non-canonical path")
                if any(
                    not (
                        name == prefix.removesuffix("/")
                        or name.startswith(prefix)
                        or name == dist_info.removesuffix("/")
                        or name.startswith(dist_info)
                    )
                    for name in names
                ):
                    raise ExtensionAcquisitionError(
                        "Wheel writes outside its package and dist-info"
                    )
                if any(name.endswith(".pth") or ".data/" in name for name in files):
                    raise ExtensionAcquisitionError(
                        "Wheel contains an executable or redirected path"
                    )
        except (OSError, zipfile.BadZipFile, pydantic.ValidationError) as error:
            raise ExtensionAcquisitionError("Extension wheel is invalid") from error

        purelib = Path(sysconfig.get_path("purelib")).resolve()
        owners = {
            Path(str(distribution.locate_file(file))).resolve()
            for distribution in importlib.metadata.distributions()
            if canonicalize_name(distribution.metadata["Name"] or "")
            != canonicalize_name(association.project)
            for file in (distribution.files or ())
        }
        if any((purelib / name).resolve() in owners for name in files):
            raise ExtensionAcquisitionError("Wheel would overwrite another Distribution's file")

    def acquire(
        self,
        release: ExtensionReleaseDescriptor,
        association: PythonReleaseDescriptor,
        host_version: str,
    ) -> AcquiredDistribution:
        if self._restart_required_reason is not None:
            raise ExtensionRestartRequiredError(self._restart_required_reason)
        _, index_url = simple_project_and_index_urls(self.origin, association)
        project = canonicalize_name(association.project)
        installed_before = self._installed_versions().get(project)
        with tempfile.TemporaryDirectory(prefix="inkcre-extension-") as temporary:
            wheel_dir = Path(temporary)
            report_path = wheel_dir / "pip-report.json"
            download = self._runner(
                [
                    "download",
                    "--only-binary=:all:",
                    "--dest",
                    str(wheel_dir),
                    "--index-url",
                    index_url,
                    f"{association.project}=={_python_project_version(release.version)}",
                ]
            )
            self._require_success(download, "wheel acquisition")
            wheels = list(wheel_dir.glob("*.whl"))
            extension_wheels: list[Path] = []
            for wheel in wheels:
                try:
                    with zipfile.ZipFile(wheel) as archive:
                        if any(
                            name.endswith(".dist-info/inkcre-extension.json")
                            for name in archive.namelist()
                        ):
                            extension_wheels.append(wheel)
                except zipfile.BadZipFile as error:
                    raise ExtensionAcquisitionError(
                        "Downloaded dependency wheel is invalid"
                    ) from error
            if len(extension_wheels) != 1:
                raise ExtensionAcquisitionError(
                    "Registry did not yield exactly one Extension wheel"
                )
            extension_wheel = extension_wheels[0]
            self._validate_wheel(extension_wheel, release, association, host_version)
            plan = self._runner(
                [
                    "install",
                    "--dry-run",
                    "--report",
                    str(report_path),
                    "--only-binary=:all:",
                    "--no-index",
                    "--find-links",
                    str(wheel_dir),
                    str(extension_wheel),
                ]
            )
            self._require_success(plan, "dependency preflight")
            self._preflight_report(report_path, project)
            self.__class__._restart_required_reason = (
                "Core site-packages mutation began; restart Core before loading Extensions"
            )
            install = self._runner(
                [
                    "install",
                    "--no-compile",
                    "--only-binary=:all:",
                    "--no-index",
                    "--find-links",
                    str(wheel_dir),
                    str(extension_wheel),
                ]
            )
            self._require_success(install, "installation")
        importlib.invalidate_caches()
        acquired = AcquiredDistribution.discover(release.name, release.version, host_version)
        if acquired is None:
            raise ExtensionAcquisitionError("Acquired Distribution has no exact installed record")
        if installed_before is not None:
            raise ExtensionRestartRequiredError(
                f"{association.project} was replaced; restart Core before loading it"
            )
        self.__class__._restart_required_reason = None
        return acquired
