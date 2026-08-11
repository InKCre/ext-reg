from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from .client import RegistryClient
from .contracts.models import PrepareReleaseRequest

app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)


def _client(registry_url: str, token: str | None) -> RegistryClient:
    if not token:
        raise typer.BadParameter("publisher token is required")
    return RegistryClient(registry_url, token=token)


@app.command("prepare-release")
def prepare_release(
    registry_url: Annotated[
        str, typer.Option("--registry-url", envvar="INKCRE_EXTENSION_REGISTRY_URL")
    ],
    namespace: Annotated[str, typer.Option("--namespace")],
    name: Annotated[str, typer.Option("--name")],
    request_path: Annotated[Path, typer.Option("--request", exists=True, dir_okay=False)],
    token: Annotated[
        str | None,
        typer.Option("--token", envvar="INKCRE_EXTENSION_REGISTRY_TOKEN", hidden=True),
    ] = None,
) -> None:
    """Prepare immutable typed native associations for one Extension Release."""

    payload = PrepareReleaseRequest.model_validate_json(request_path.read_text(encoding="utf-8"))
    with _client(registry_url, token) as client:
        release = client.prepare(namespace, name, payload)
    typer.echo(release.model_dump_json(exclude_none=True))


@app.command("upload-module-federation")
def upload_module_federation(
    registry_url: Annotated[
        str, typer.Option("--registry-url", envvar="INKCRE_EXTENSION_REGISTRY_URL")
    ],
    namespace: Annotated[str, typer.Option("--namespace")],
    name: Annotated[str, typer.Option("--name")],
    version: Annotated[str, typer.Option("--version")],
    archive: Annotated[Path, typer.Option("--archive", exists=True, dir_okay=False)],
    token: Annotated[
        str | None,
        typer.Option("--token", envvar="INKCRE_EXTENSION_REGISTRY_TOKEN", hidden=True),
    ] = None,
) -> None:
    """Validate and upload one immutable native Module Federation ZIP snapshot."""

    with _client(registry_url, token) as client:
        release = client.upload_module_federation(namespace, name, version, archive.read_bytes())
    typer.echo(release.model_dump_json(exclude_none=True))


@app.command("publish-release")
def publish_release(
    registry_url: Annotated[
        str, typer.Option("--registry-url", envvar="INKCRE_EXTENSION_REGISTRY_URL")
    ],
    namespace: Annotated[str, typer.Option("--namespace")],
    name: Annotated[str, typer.Option("--name")],
    version: Annotated[str, typer.Option("--version")],
    token: Annotated[
        str | None,
        typer.Option("--token", envvar="INKCRE_EXTENSION_REGISTRY_TOKEN", hidden=True),
    ] = None,
) -> None:
    """Publish a Release after at least one native Distribution is ready."""

    with _client(registry_url, token) as client:
        release = client.publish(namespace, name, version)
    typer.echo(release.model_dump_json(exclude_none=True))


@app.command("yank-release")
def yank_release(
    registry_url: Annotated[
        str, typer.Option("--registry-url", envvar="INKCRE_EXTENSION_REGISTRY_URL")
    ],
    namespace: Annotated[str, typer.Option("--namespace")],
    name: Annotated[str, typer.Option("--name")],
    version: Annotated[str, typer.Option("--version")],
    reason: Annotated[str, typer.Option("--reason")],
    token: Annotated[
        str | None,
        typer.Option("--token", envvar="INKCRE_EXTENSION_REGISTRY_TOKEN", hidden=True),
    ] = None,
) -> None:
    """Yank a Release while retaining exact descriptor and native bytes."""

    with _client(registry_url, token) as client:
        release = client.yank(namespace, name, version, reason)
    typer.echo(release.model_dump_json(exclude_none=True))


@app.command("unyank-release")
def unyank_release(
    registry_url: Annotated[
        str, typer.Option("--registry-url", envvar="INKCRE_EXTENSION_REGISTRY_URL")
    ],
    namespace: Annotated[str, typer.Option("--namespace")],
    name: Annotated[str, typer.Option("--name")],
    version: Annotated[str, typer.Option("--version")],
    token: Annotated[
        str | None,
        typer.Option("--token", envvar="INKCRE_EXTENSION_REGISTRY_TOKEN", hidden=True),
    ] = None,
) -> None:
    """Restore a yanked Release to normal discovery."""

    with _client(registry_url, token) as client:
        release = client.unyank(namespace, name, version)
    typer.echo(release.model_dump_json(exclude_none=True))


@app.command("show-release")
def show_release(
    registry_url: Annotated[
        str, typer.Option("--registry-url", envvar="INKCRE_EXTENSION_REGISTRY_URL")
    ],
    coordinate: Annotated[str, typer.Option("--coordinate")],
    version: Annotated[str, typer.Option("--version")],
) -> None:
    """Read one exact public Extension Release, including a yanked Release."""

    namespace, name = coordinate.split("/", 1)
    with RegistryClient(registry_url) as client:
        release = client.get_release(namespace, name, version)
    typer.echo(json.dumps(release.model_dump(mode="json", exclude_none=True), sort_keys=True))
