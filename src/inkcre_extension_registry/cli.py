from __future__ import annotations

import hashlib
import json
import mimetypes
import os
from pathlib import Path
from typing import Annotated

import typer

from .client import RegistryClient
from .contracts.models import (
    FileDescriptor,
    TargetAssociation,
    TargetManifest,
    TargetPublishConfig,
)

app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)


def _read_config(path: Path) -> TargetPublishConfig:
    return TargetPublishConfig.model_validate_json(path.read_text(encoding="utf-8"))


def build_target_manifest(config: TargetPublishConfig, directory: Path) -> TargetManifest:
    if not directory.is_dir():
        raise typer.BadParameter(f"artifact directory does not exist: {directory}")

    files: dict[str, FileDescriptor] = {}
    for path in sorted(candidate for candidate in directory.rglob("*") if candidate.is_file()):
        if path.is_symlink():
            raise typer.BadParameter(f"artifact files must not be symbolic links: {path}")
        relative = path.relative_to(directory).as_posix()
        content = path.read_bytes()
        files[relative] = FileDescriptor(
            sha256=hashlib.sha256(content).hexdigest(),
            size=len(content),
            media_type=mimetypes.guess_type(relative)[0] or "application/octet-stream",
        )

    return TargetManifest(
        artifact_format=config.artifact_format,
        entrypoint=config.entrypoint,
        conditions=config.conditions,
        files=files,
    )


@app.command("build-target")
def build_target(
    config_path: Annotated[Path, typer.Option("--config", exists=True, dir_okay=False)],
    directory: Annotated[Path, typer.Option("--directory", exists=True, file_okay=False)],
    output: Annotated[Path | None, typer.Option("--output")] = None,
) -> None:
    """Build one deterministic canonical target manifest without publishing it."""

    config = _read_config(config_path)
    manifest = build_target_manifest(config, directory)
    encoded = manifest.canonical_bytes() + b"\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(encoded)
    typer.echo(json.dumps({"target_digest": manifest.digest, "manifest": json.loads(encoded)}))


@app.command("publish-target")
def publish_target(
    registry_url: Annotated[
        str, typer.Option("--registry-url", envvar="INKCRE_EXTENSION_REGISTRY_URL")
    ],
    config_path: Annotated[Path, typer.Option("--config", exists=True, dir_okay=False)],
    directory: Annotated[Path, typer.Option("--directory", exists=True, file_okay=False)],
    source_repository: Annotated[str, typer.Option("--source-repository")],
    source_revision: Annotated[str, typer.Option("--source-revision")],
    token: Annotated[
        str | None,
        typer.Option("--token", envvar="INKCRE_EXTENSION_REGISTRY_TOKEN", hidden=True),
    ] = None,
    build_id: Annotated[str | None, typer.Option("--build-id")] = None,
    manifest_output: Annotated[Path | None, typer.Option("--manifest-output")] = None,
) -> None:
    """Upload one target's files, bind its immutable slot, and publish the version."""

    if not token:
        raise typer.BadParameter("publisher token is required")
    config = _read_config(config_path)
    manifest = build_target_manifest(config, directory)
    if manifest_output:
        manifest_output.parent.mkdir(parents=True, exist_ok=True)
        manifest_output.write_bytes(manifest.canonical_bytes() + b"\n")

    with RegistryClient(registry_url, token=token) as client:
        for relative, descriptor in sorted(manifest.files.items()):
            client.put_blob(
                f"sha256:{descriptor.sha256}",
                (directory / relative).read_bytes(),
                descriptor.media_type,
            )
        target = client.put_target(
            config.namespace,
            config.name,
            config.version,
            config.target_key,
            TargetAssociation(
                manifest=manifest,
                source_repository=source_repository,
                source_revision=source_revision,
                build_id=build_id,
            ),
        )
        release = client.publish(config.namespace, config.name, config.version)

    typer.echo(
        json.dumps(
            {
                "coordinate": config.coordinate,
                "version": config.version,
                "state": release.state,
                "target_key": target.target_key,
                "target_digest": target.target_digest,
                "source_revision": source_revision,
                "build_id": build_id or os.getenv("GITHUB_RUN_ID"),
            },
            separators=(",", ":"),
            sort_keys=True,
        )
    )


@app.command("show-release")
def show_release(
    registry_url: Annotated[
        str, typer.Option("--registry-url", envvar="INKCRE_EXTENSION_REGISTRY_URL")
    ],
    coordinate: Annotated[str, typer.Option("--coordinate")],
    version: Annotated[str, typer.Option("--version")],
) -> None:
    """Read one exact public Extension Version."""

    namespace, name = coordinate.split("/", 1)
    with RegistryClient(registry_url) as client:
        release = client.get_release(namespace, name, version)
    typer.echo(release.model_dump_json())
