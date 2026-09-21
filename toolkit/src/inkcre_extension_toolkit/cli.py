from __future__ import annotations

import json
import secrets
from pathlib import Path
from typing import Annotated

import typer

from .client import RegistryClient
from .contracts import PrepareReleaseRequest
from .documentation import DocumentationCandidate, inspect_documentation, pack_documentation
from .preview import build_preview_registry
from .python_distribution import finalize_wheel

app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)
preview_app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)
python_app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)
wheel_app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)
docs_app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)
app.add_typer(docs_app, name="docs")
app.add_typer(preview_app, name="preview")
app.add_typer(python_app, name="python")
python_app.add_typer(wheel_app, name="wheel")


@docs_app.command("address")
def docs_address(
    registry_url: Annotated[
        str, typer.Option("--registry-url", envvar="INKCRE_EXTENSION_REGISTRY_URL")
    ],
) -> None:
    """Choose an unbound snapshot address before a build that needs an absolute origin."""
    with RegistryClient(registry_url) as client:
        hosting = client.documentation_hosting()
    snapshot_id = secrets.token_hex(16)
    typer.echo(
        json.dumps(
            {
                "snapshot_id": snapshot_id,
                "origin": hosting.origin_template.replace("{snapshot}", snapshot_id),
            }
        )
    )


@docs_app.command("pack")
def docs_pack(
    site: Annotated[Path, typer.Option("--site", exists=True, file_okay=False)],
    output: Annotated[Path, typer.Option("--output", file_okay=False)],
    name: Annotated[str, typer.Option("--name")],
    version: Annotated[str, typer.Option("--version")],
    scope: Annotated[str, typer.Option("--scope")],
    source_repository: Annotated[str, typer.Option("--source-repository")],
    source_revision: Annotated[str, typer.Option("--source-revision")],
    entry: Annotated[str, typer.Option("--entry")] = "index.html",
    snapshot_id: Annotated[str | None, typer.Option("--snapshot-id")] = None,
    expected_etag: Annotated[str | None, typer.Option("--if-match")] = None,
    build_id: Annotated[str | None, typer.Option("--build-id")] = None,
) -> None:
    """Save one complete candidate; omit --if-match only when creating an absent set."""
    archive = pack_documentation(site, entry)
    inspected = inspect_documentation(archive, entry)
    candidate = DocumentationCandidate.model_validate(
        {
            "name": name,
            "version": version,
            "scope": scope,
            "expected_etag": expected_etag,
            "metadata": {
                "snapshot_id": snapshot_id or secrets.token_hex(16),
                "content_sha256": inspected.digest,
                "entry": entry,
                "source_repository": source_repository,
                "source_revision": source_revision,
                "build_id": build_id,
            },
        }
    )
    output.mkdir(parents=True, exist_ok=False)
    (output / "documentation.zip").write_bytes(archive)
    (output / "candidate.json").write_text(
        candidate.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    typer.echo(output / "candidate.json")


@docs_app.command("publish")
def docs_publish(
    registry_url: Annotated[
        str, typer.Option("--registry-url", envvar="INKCRE_EXTENSION_REGISTRY_URL")
    ],
    candidate: Annotated[Path, typer.Option("--candidate", exists=True, file_okay=False)],
    token: Annotated[
        str | None, typer.Option("--token", envvar="INKCRE_EXTENSION_REGISTRY_TOKEN", hidden=True)
    ] = None,
) -> None:
    """Upload saved bytes with their saved precondition and recover the same candidate."""
    saved = DocumentationCandidate.model_validate_json(
        (candidate / "candidate.json").read_text(encoding="utf-8")
    )
    namespace, name = saved.name.split("/", 1)
    archive = (candidate / "documentation.zip").read_bytes()
    with _client(registry_url, token) as client:
        result = client.upload_documentation(
            namespace,
            name,
            saved.version,
            saved.scope,
            saved.metadata,
            archive,
            expected_etag=saved.expected_etag,
        )
    typer.echo(result.model_dump_json())


@docs_app.command("show")
def docs_show(
    registry_url: Annotated[
        str, typer.Option("--registry-url", envvar="INKCRE_EXTENSION_REGISTRY_URL")
    ],
    name: Annotated[str, typer.Option("--name")],
    version: Annotated[str, typer.Option("--version")],
    private: Annotated[bool, typer.Option("--private")] = False,
    token: Annotated[
        str | None, typer.Option("--token", envvar="INKCRE_EXTENSION_REGISTRY_TOKEN", hidden=True)
    ] = None,
) -> None:
    """Read exact scopes and replacement ETags; --private includes preparing Releases."""
    from .semantic import validate_extension_name, validate_version

    namespace, extension = validate_extension_name(name).split("/", 1)
    validate_version(version)
    with _client(registry_url, token) if private else RegistryClient(registry_url) as client:
        result = client.get_documentation(namespace, extension, version, private=private)
    typer.echo(result.model_dump_json())


@wheel_app.command("finalize")
def python_wheel_finalize(
    project: Annotated[Path, typer.Option("--project", exists=True, dir_okay=False)],
    wheel: Annotated[Path, typer.Option("--wheel", exists=True, dir_okay=False)],
    output_dir: Annotated[Path, typer.Option("--output-dir", file_okay=False)],
) -> None:
    """Finalize an already-built Core Extension wheel with installed metadata."""

    finalized = finalize_wheel(project, wheel, output_dir)
    typer.echo(finalized)


def _client(registry_url: str, token: str | None) -> RegistryClient:
    if not token:
        raise typer.BadParameter("publisher token is required")
    return RegistryClient(registry_url, token=token)


@preview_app.command("build")
def preview_build(
    inventory: Annotated[Path, typer.Option("--inventory", exists=True, dir_okay=False)],
    public_origin: Annotated[str, typer.Option("--public-origin")],
    output: Annotated[Path, typer.Option("--output", file_okay=False)],
) -> None:
    """Build a multi-Extension static preview Registry facade."""

    result = build_preview_registry(inventory, public_origin, output)
    typer.echo(result.model_dump_json())


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
