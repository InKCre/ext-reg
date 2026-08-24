"""Installed-record discovery and standard-pip acquisition."""

from __future__ import annotations

import importlib
import importlib.metadata
import logging
import os
import subprocess
import sys
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
from .errors import ExtensionAcquisitionError, ExtensionEntryPointError
from .release import _validate_entry_point, _validate_host, simple_project_and_index_urls

INSTALLED_RECORD = "inkcre-extension.json"
LOGGER = logging.getLogger(__name__)


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
    def __init__(
        self,
        origin: str,
        runner: typing.Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        self.origin = origin
        self._runner = runner or self._run

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
            stdout = result.stdout or ""
            stderr = result.stderr or ""
            LOGGER.error(
                "pip %s failed with exit code %s\nstdout:\n%s\nstderr:\n%s",
                operation,
                result.returncode,
                stdout,
                stderr,
            )
            raise ExtensionAcquisitionError(
                f"pip {operation} failed with exit code {result.returncode}"
            )

    @staticmethod
    def _validate_wheel(
        wheel: Path,
        release: ExtensionReleaseDescriptor,
        association: PythonReleaseDescriptor,
        host_version: str,
    ) -> None:
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
        except (OSError, zipfile.BadZipFile, pydantic.ValidationError) as error:
            raise ExtensionAcquisitionError("Extension wheel is invalid") from error

    def acquire(
        self,
        release: ExtensionReleaseDescriptor,
        association: PythonReleaseDescriptor,
        host_version: str,
    ) -> AcquiredDistribution:
        _, index_url = simple_project_and_index_urls(self.origin, association)
        with tempfile.TemporaryDirectory(prefix="inkcre-extension-") as temporary:
            wheel_dir = Path(temporary)
            download = self._runner(
                [
                    "download",
                    "--no-deps",
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
                    raise ExtensionAcquisitionError("Downloaded wheel is invalid") from error
            if len(extension_wheels) != 1:
                raise ExtensionAcquisitionError(
                    "Registry did not yield exactly one Extension wheel"
                )
            extension_wheel = extension_wheels[0]
            self._validate_wheel(extension_wheel, release, association, host_version)
            install = self._runner(
                [
                    "install",
                    "--no-compile",
                    str(extension_wheel),
                ]
            )
            self._require_success(install, "installation")
        importlib.invalidate_caches()
        acquired = AcquiredDistribution.discover(release.name, release.version, host_version)
        if acquired is None:
            raise ExtensionAcquisitionError("Acquired Distribution has no exact installed record")
        return acquired
