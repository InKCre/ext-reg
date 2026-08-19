from __future__ import annotations

import configparser
import hashlib
import io
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
from typing import Protocol

from packaging.utils import InvalidWheelFilename, parse_wheel_filename
from packaging.version import InvalidVersion
from packaging.version import Version as Pep440Version

from .contracts import (
    InstalledExtension,
    InstalledHostSdk,
    PythonEntryPoint,
    normalize_project_name,
    python_project_version,
    validate_host_sdk_range,
)

MAX_ARCHIVE_FILES = 4096
MAX_EXPANDED_BYTES = 100 * 1024 * 1024
MAX_MEMBER_BYTES = 50 * 1024 * 1024
MAX_COMPRESSION_RATIO = 200


class DistributionValidationError(ValueError):
    pass


class EntryPointDescriptor(Protocol):
    group: str
    name: str
    object: str


@dataclass(frozen=True)
class InspectedWheel:
    project: str
    project_version: str
    filename: str
    metadata_version: str
    requires_python: str | None
    metadata: bytes

    @property
    def sha256(self) -> str:
        raise AttributeError("the archive digest belongs to the uploaded bytes")


def semver_to_pep440(version: str) -> str:
    try:
        return python_project_version(version)
    except ValueError as error:
        raise DistributionValidationError(str(error)) from error


def _safe_members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    infos = archive.infolist()
    if len(infos) > MAX_ARCHIVE_FILES:
        raise DistributionValidationError("wheel contains too many archive members")
    names: set[str] = set()
    expanded = 0
    safe: list[zipfile.ZipInfo] = []
    for info in infos:
        name = info.filename
        if not name or "\\" in name or "\x00" in name:
            raise DistributionValidationError("wheel contains an unsafe archive path")
        canonical_name = name.removesuffix("/") if info.is_dir() else name
        path = PurePosixPath(canonical_name)
        normalized_name = path.as_posix()
        if normalized_name in names:
            raise DistributionValidationError("wheel contains a duplicated archive path")
        if (
            path.is_absolute()
            or any(part in {"", ".", ".."} for part in path.parts)
            or normalized_name != canonical_name
        ):
            raise DistributionValidationError("wheel contains an unsafe archive path")
        names.add(normalized_name)
        mode = info.external_attr >> 16
        if mode and stat.S_ISLNK(mode):
            raise DistributionValidationError("wheel contains a symbolic link")
        if info.flag_bits & 0x1:
            raise DistributionValidationError("encrypted wheel members are not supported")
        if info.is_dir():
            continue
        if info.file_size > MAX_MEMBER_BYTES:
            raise DistributionValidationError("wheel member exceeds the expansion limit")
        expanded += info.file_size
        if expanded > MAX_EXPANDED_BYTES:
            raise DistributionValidationError("wheel exceeds the total expansion limit")
        if (
            info.file_size > 1024 * 1024
            and info.compress_size > 0
            and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO
        ):
            raise DistributionValidationError("wheel member has an unsafe compression ratio")
        safe.append(info)
    return safe


def inspect_wheel(
    filename: str,
    content: bytes,
    *,
    expected_project: str,
    expected_release_version: str,
    expected_entry_point: EntryPointDescriptor,
) -> InspectedWheel:
    if PurePosixPath(filename).name != filename or "\\" in filename:
        raise DistributionValidationError("upload filename must not contain a path")
    try:
        wheel_project, wheel_version, _build, _tags = parse_wheel_filename(filename)
    except InvalidWheelFilename as error:
        raise DistributionValidationError("only valid wheel files are accepted") from error
    expected_pep440_literal = semver_to_pep440(expected_release_version)
    expected_pep440 = Pep440Version(expected_pep440_literal)
    filename_version = filename.removesuffix(".whl").split("-", 2)[1]
    if filename_version != expected_pep440_literal:
        raise DistributionValidationError(
            "wheel filename version must use the Release's canonical PEP 440 spelling"
        )
    if wheel_version != expected_pep440:
        raise DistributionValidationError("wheel filename version does not match the Release")
    normalized_expected = normalize_project_name(expected_project)
    if normalize_project_name(str(wheel_project)) != normalized_expected:
        raise DistributionValidationError("wheel filename Project does not match the association")

    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as error:
        raise DistributionValidationError("wheel is not a valid ZIP archive") from error
    with archive:
        safe = _safe_members(archive)
        metadata_members = [info for info in safe if info.filename.endswith(".dist-info/METADATA")]
        entry_members = [
            info for info in safe if info.filename.endswith(".dist-info/entry_points.txt")
        ]
        if len(metadata_members) != 1:
            raise DistributionValidationError("wheel must contain exactly one dist-info/METADATA")
        dist_info = metadata_members[0].filename.removesuffix("METADATA")
        matching_entries = [
            info for info in entry_members if info.filename == dist_info + "entry_points.txt"
        ]
        if len(entry_members) != 1 or len(matching_entries) != 1:
            raise DistributionValidationError(
                "wheel must contain exactly one matching dist-info/entry_points.txt"
            )
        try:
            metadata = archive.read(metadata_members[0])
            entry_points = archive.read(matching_entries[0]).decode("utf-8")
        except (KeyError, UnicodeDecodeError, RuntimeError, zipfile.BadZipFile) as error:
            raise DistributionValidationError("wheel metadata cannot be read safely") from error

    message = BytesParser(policy=policy.default).parsebytes(metadata)
    metadata_name = message.get("Name")
    metadata_version = message.get("Version")
    metadata_version_header = message.get("Metadata-Version")
    if not metadata_name or not metadata_version or not metadata_version_header:
        raise DistributionValidationError("wheel Core Metadata is incomplete")
    if normalize_project_name(str(metadata_name)) != normalized_expected:
        raise DistributionValidationError("Core Metadata Project does not match the association")
    metadata_version_literal = str(metadata_version)
    try:
        parsed_metadata_version = Pep440Version(metadata_version_literal)
    except InvalidVersion as error:
        raise DistributionValidationError("Core Metadata version is not valid PEP 440") from error
    if metadata_version_literal != expected_pep440_literal:
        raise DistributionValidationError(
            "Core Metadata Version must use the Release's canonical PEP 440 spelling"
        )
    if parsed_metadata_version != expected_pep440 or parsed_metadata_version != wheel_version:
        raise DistributionValidationError("Core Metadata version does not match the Release")

    parser = configparser.ConfigParser(interpolation=None, strict=True)
    parser.optionxform = lambda optionstr: optionstr
    try:
        parser.read_string(entry_points)
    except configparser.Error as error:
        raise DistributionValidationError("entry_points.txt is invalid") from error
    if not parser.has_section(expected_entry_point.group):
        raise DistributionValidationError("declared entry-point group is missing")
    if not parser.has_option(expected_entry_point.group, expected_entry_point.name):
        raise DistributionValidationError("declared entry-point name is missing")
    actual_object = parser.get(expected_entry_point.group, expected_entry_point.name).strip()
    if actual_object != expected_entry_point.object:
        raise DistributionValidationError("declared entry-point object does not match the wheel")

    return InspectedWheel(
        project=normalized_expected,
        project_version=expected_pep440_literal,
        filename=filename,
        metadata_version=str(metadata_version_header),
        requires_python=(
            str(message.get("Requires-Python")) if message.get("Requires-Python") else None
        ),
        metadata=metadata,
    )


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _producer_metadata(project_path: Path) -> InstalledExtension:
    try:
        document = tomllib.loads(project_path.read_text(encoding="utf-8"))
        project = document["project"]
        extension = document["tool"]["inkcre-extension"]
        entry_points = project["entry-points"]["inkcre.core.extensions"]
    except (OSError, tomllib.TOMLDecodeError, KeyError, TypeError) as error:
        raise DistributionValidationError("producer pyproject metadata is incomplete") from error
    if not isinstance(entry_points, dict) or len(entry_points) != 1:
        raise DistributionValidationError("producer must declare exactly one Core entry point")
    entry_name, entry_object = next(iter(entry_points.items()))
    try:
        release_version = str(project["version"])
        project_version = python_project_version(release_version)
        host_sdk_name = str(extension["host-sdk"])
        host_sdk_version = validate_host_sdk_range(str(extension["host-sdk-version"]))
        if host_sdk_name != "core-py":
            raise ValueError("host SDK must be core-py")
        return InstalledExtension.model_validate(
            {
                "schema_version": 1,
                "name": extension["name"],
                "version": release_version,
                "host_sdk": InstalledHostSdk(name="core-py", version=host_sdk_version),
                "python": {
                    "project": normalize_project_name(str(project["name"])),
                    "project_version": project_version,
                    "entry_point": PythonEntryPoint(
                        group="inkcre.core.extensions",
                        name=str(entry_name),
                        object=str(entry_object),
                    ).model_dump(mode="json"),
                },
            }
        )
    except (KeyError, TypeError, ValueError) as error:
        raise DistributionValidationError(f"producer metadata is invalid: {error}") from error


def inspect_installed_extension(filename: str, content: bytes) -> InstalledExtension:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            safe = _safe_members(archive)
            records = [
                info for info in safe if info.filename.endswith(".dist-info/inkcre-extension.json")
            ]
            if len(records) != 1:
                raise DistributionValidationError(
                    "wheel must contain exactly one dist-info/inkcre-extension.json"
                )
            payload = archive.read(records[0])
    except (zipfile.BadZipFile, KeyError, RuntimeError) as error:
        raise DistributionValidationError("installed Extension record cannot be read") from error
    try:
        record = InstalledExtension.model_validate_json(payload)
    except ValueError as error:
        raise DistributionValidationError("installed Extension record is invalid") from error
    inspected = inspect_wheel(
        filename,
        content,
        expected_project=record.python.project,
        expected_release_version=record.version,
        expected_entry_point=PythonEntryPoint.model_validate(
            record.python.entry_point.model_dump(mode="json")
        ),
    )
    if inspected.project_version != record.python.project_version:
        raise DistributionValidationError(
            "installed Extension Project version does not match wheel metadata"
        )
    return record


def finalize_wheel(project_path: Path, wheel_path: Path, output_dir: Path) -> Path:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise DistributionValidationError("output directory must be empty")
    if not wheel_path.is_file():
        raise DistributionValidationError("input wheel does not exist")
    record = _producer_metadata(project_path)
    original = wheel_path.read_bytes()
    inspect_wheel(
        wheel_path.name,
        original,
        expected_project=record.python.project,
        expected_release_version=record.version,
        expected_entry_point=PythonEntryPoint.model_validate(
            record.python.entry_point.model_dump(mode="json")
        ),
    )

    with tempfile.TemporaryDirectory() as temporary_directory:
        temporary = Path(temporary_directory)
        unpacked_root = temporary / "unpacked"
        packed_root = temporary / "packed"
        unpacked_root.mkdir()
        packed_root.mkdir()
        subprocess.run(
            [
                sys.executable,
                "-m",
                "wheel",
                "unpack",
                "--dest",
                str(unpacked_root),
                str(wheel_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        unpacked = list(unpacked_root.iterdir())
        if len(unpacked) != 1 or not unpacked[0].is_dir():
            raise DistributionValidationError("wheel unpack did not produce one wheel tree")
        dist_info = list(unpacked[0].glob("*.dist-info"))
        if len(dist_info) != 1:
            raise DistributionValidationError("wheel must contain exactly one dist-info directory")
        (dist_info[0] / "inkcre-extension.json").write_text(
            record.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
        subprocess.run(
            [
                sys.executable,
                "-m",
                "wheel",
                "pack",
                "--dest-dir",
                str(packed_root),
                str(unpacked[0]),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        packed = list(packed_root.glob("*.whl"))
        if len(packed) != 1:
            raise DistributionValidationError("wheel pack did not produce one wheel")
        finalized_content = packed[0].read_bytes()
        finalized_record = inspect_installed_extension(packed[0].name, finalized_content)
        if finalized_record != record:
            raise DistributionValidationError("finalized wheel record changed during packing")
        output_dir.mkdir(parents=True, exist_ok=True)
        destination = output_dir / packed[0].name
        shutil.copy2(packed[0], destination)
        return destination
