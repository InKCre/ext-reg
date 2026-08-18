from __future__ import annotations

import io
import stat
import zipfile
from pathlib import Path

import httpx
import pytest
from inkcre_extension_toolkit.client import RegistryClient
from pydantic import ValidationError

from inkcre_extension_registry.contracts.models import (
    PrepareReleaseRequest,
    PythonEntryPoint,
    ReleaseRecord,
    normalize_project_name,
    validate_version,
)
from inkcre_extension_registry.service.app import create_app
from inkcre_extension_registry.service.module_federation import (
    inspect_module_federation_snapshot,
    validate_relative_asset_path,
)
from inkcre_extension_registry.service.python_distribution import inspect_wheel, semver_to_pep440
from inkcre_extension_registry.service.simple import SIMPLE_HTML, SIMPLE_JSON, negotiate_simple


@pytest.mark.parametrize("version", ["v1.2.3", "1.2", "01.2.3", "1.2.3+build"])
def test_product_version_rejects_noncanonical_semver(version: str) -> None:
    with pytest.raises(ValueError):
        validate_version(version)


@pytest.mark.parametrize(
    ("project", "normalized"),
    [
        ("inkcre-ext-twitter", "inkcre-ext-twitter"),
        ("InKCre.Ext_Twitter", "inkcre-ext-twitter"),
    ],
)
def test_python_project_normalization_matches_native_rules(project: str, normalized: str) -> None:
    assert normalize_project_name(project) == normalized


def test_prepare_contract_is_typed_strict_and_lossless_for_python_prereleases() -> None:
    payload = PrepareReleaseRequest.model_validate(
        {
            "nickname": "Twitter",
            "version": "1.2.3-rc.1",
            "python": {
                "project": "inkcre-ext-twitter",
                "host_sdk": "core-py",
                "host_sdk_version": ">=0.1.0 <0.2.0",
                "entry_point": {
                    "group": "inkcre.core.extensions",
                    "name": "twitter",
                    "object": "extensions.twitter:Extension",
                },
                "source_repository": "https://github.com/InKCre/core-py",
                "source_revision": "a" * 40,
            },
        }
    )
    assert payload.version == "1.2.3-rc.1"
    assert semver_to_pep440(payload.version) == "1.2.3rc1"

    with pytest.raises(ValidationError, match="lossless"):
        PrepareReleaseRequest.model_validate(
            payload.model_dump(mode="json") | {"version": "1.2.3-preview.1"}
        )
    with pytest.raises(ValidationError, match="at least one"):
        PrepareReleaseRequest(nickname="Twitter", version="1.2.3")
    with pytest.raises(ValidationError):
        PrepareReleaseRequest.model_validate(payload.model_dump(mode="json") | {"unexpected": True})

    assert payload.python is not None
    with pytest.raises(ValidationError, match="valid SemVer range"):
        PrepareReleaseRequest.model_validate(
            {
                **payload.model_dump(mode="json"),
                "python": {
                    **payload.python.model_dump(mode="json"),
                    "host_sdk_version": ">=0.1.0,<0.2.0",
                },
            }
        )


def test_canonical_name_and_semver_constraints_are_published_in_contracts() -> None:
    prepare_schema = PrepareReleaseRequest.model_json_schema(mode="serialization")
    release_schema = ReleaseRecord.model_json_schema(mode="serialization")
    assert prepare_schema["properties"]["version"] == {
        "maxLength": 128,
        "minLength": 5,
        "pattern": (
            r"^(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
            r"(?:-(?:(?:0|[1-9][0-9]*)|(?:[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*))"
            r"(?:\.(?:(?:0|[1-9][0-9]*)|(?:[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)))*)?$"
        ),
        "title": "Version",
        "type": "string",
    }
    assert release_schema["properties"]["name"]["maxLength"] == 129
    assert release_schema["properties"]["name"]["pattern"].startswith("^[a-z0-9]")

    openapi = create_app().openapi()
    release_get = openapi["paths"]["/v1/extensions/{namespace}/{name}/releases/{version}"]["get"]
    parameters = {parameter["name"]: parameter["schema"] for parameter in release_get["parameters"]}
    assert parameters["namespace"]["maxLength"] == 64
    assert parameters["namespace"]["pattern"].startswith("^[a-z0-9]")
    assert parameters["version"]["maxLength"] == 128
    assert parameters["version"]["pattern"].startswith("^(?:0|")


def _wheel_with_versions(filename_version: str, metadata_version: str) -> tuple[str, bytes]:
    filename = f"inkcre_ext_twitter-{filename_version}-py3-none-any.whl"
    dist_info = f"inkcre_ext_twitter-{filename_version}.dist-info"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            f"{dist_info}/METADATA",
            (f"Metadata-Version: 2.4\nName: inkcre-ext-twitter\nVersion: {metadata_version}\n\n"),
        )
        archive.writestr(
            f"{dist_info}/entry_points.txt",
            "[inkcre.core.extensions]\ntwitter = extensions.twitter:Extension\n",
        )
    return filename, buffer.getvalue()


@pytest.mark.parametrize(
    ("release_version", "filename_version", "metadata_version", "message"),
    [
        ("0.1.1", "0.1.1.0", "0.1.1", "wheel filename version"),
        ("0.1.1", "0.1.1", "0.1.1.0", "Core Metadata Version"),
        ("0.1.1-rc.1", "0.1.1rc01", "0.1.1rc1", "wheel filename version"),
        ("0.1.1-rc.1", "0.1.1rc1", "0.1.1rc01", "Core Metadata Version"),
    ],
)
def test_wheel_versions_require_exact_canonical_pep440_spelling(
    release_version: str,
    filename_version: str,
    metadata_version: str,
    message: str,
) -> None:
    filename, wheel = _wheel_with_versions(filename_version, metadata_version)
    with pytest.raises(ValueError, match=message):
        inspect_wheel(
            filename,
            wheel,
            expected_project="inkcre-ext-twitter",
            expected_release_version=release_version,
            expected_entry_point=PythonEntryPoint(
                group="inkcre.core.extensions",
                name="twitter",
                object="extensions.twitter:Extension",
            ),
        )


def test_entry_point_and_mf_paths_fail_closed() -> None:
    with pytest.raises(ValidationError, match="module or module:attribute"):
        PythonEntryPoint(
            group="inkcre.core.extensions",
            name="twitter",
            object="../extensions.twitter:Extension",
        )
    for path in ("../remoteEntry.js", "/remoteEntry.js", "https://evil.test/code.js"):
        with pytest.raises(ValueError):
            validate_relative_asset_path(path)


def test_native_archives_reject_traversal_symlinks_duplicates_and_zip_bombs() -> None:
    traversal_buffer = io.BytesIO()
    with zipfile.ZipFile(traversal_buffer, "w") as archive:
        archive.writestr("../remoteEntry.js", "bad")
    with pytest.raises(ValueError, match="unsafe archive path"):
        inspect_wheel(
            "inkcre_ext_twitter-0.1.1-py3-none-any.whl",
            traversal_buffer.getvalue(),
            expected_project="inkcre-ext-twitter",
            expected_release_version="0.1.1",
            expected_entry_point=PythonEntryPoint(
                group="inkcre.core.extensions",
                name="twitter",
                object="extensions.twitter:Extension",
            ),
        )

    for member in (
        "inkcre_ext_twitter-0.1.1.dist-info//METADATA",
        "./inkcre_ext_twitter-0.1.1.dist-info/METADATA",
    ):
        noncanonical_buffer = io.BytesIO()
        with zipfile.ZipFile(noncanonical_buffer, "w") as archive:
            archive.writestr(member, "bad")
        with pytest.raises(ValueError, match="unsafe archive path"):
            inspect_wheel(
                "inkcre_ext_twitter-0.1.1-py3-none-any.whl",
                noncanonical_buffer.getvalue(),
                expected_project="inkcre-ext-twitter",
                expected_release_version="0.1.1",
                expected_entry_point=PythonEntryPoint(
                    group="inkcre.core.extensions",
                    name="twitter",
                    object="extensions.twitter:Extension",
                ),
            )

    normalized_duplicate_buffer = io.BytesIO()
    with zipfile.ZipFile(normalized_duplicate_buffer, "w") as archive:
        archive.writestr("package/module.py", "canonical")
        archive.writestr("package//module.py", "alias")
    with pytest.raises(ValueError, match="duplicated archive path"):
        inspect_wheel(
            "inkcre_ext_twitter-0.1.1-py3-none-any.whl",
            normalized_duplicate_buffer.getvalue(),
            expected_project="inkcre-ext-twitter",
            expected_release_version="0.1.1",
            expected_entry_point=PythonEntryPoint(
                group="inkcre.core.extensions",
                name="twitter",
                object="extensions.twitter:Extension",
            ),
        )

    symlink_buffer = io.BytesIO()
    with zipfile.ZipFile(symlink_buffer, "w") as archive:
        symlink = zipfile.ZipInfo("remoteEntry.js")
        symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(symlink, "target.js")
    with pytest.raises(ValueError, match="symbolic link"):
        inspect_module_federation_snapshot(
            symlink_buffer.getvalue(), public_prefix="https://registry.test/extensions/example/"
        )

    duplicate_buffer = io.BytesIO()
    with zipfile.ZipFile(duplicate_buffer, "w") as archive:
        archive.writestr("remoteEntry.js", "first")
        with pytest.warns(UserWarning, match="Duplicate name"):
            archive.writestr("remoteEntry.js", "second")
    with pytest.raises(ValueError, match="duplicated archive path"):
        inspect_module_federation_snapshot(
            duplicate_buffer.getvalue(), public_prefix="https://registry.test/extensions/example/"
        )

    bomb_buffer = io.BytesIO()
    with zipfile.ZipFile(bomb_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("bomb.js", b"0" * (2 * 1024 * 1024))
    with pytest.raises(ValueError, match="compression ratio"):
        inspect_module_federation_snapshot(
            bomb_buffer.getvalue(), public_prefix="https://registry.test/extensions/example/"
        )


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity", "1e999"])
def test_module_federation_manifest_rejects_non_finite_json_numbers(constant: str) -> None:
    manifest = (
        '{"metaData":{"publicPath":"./","remoteEntry":{"path":"",'
        '"name":"remoteEntry.js"}},"shared":[],"exposes":[],"invalid":' + constant + "}"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("mf-manifest.json", manifest)
        archive.writestr("remoteEntry.js", "export default {};\n")
    with pytest.raises(ValueError, match="non-finite"):
        inspect_module_federation_snapshot(
            buffer.getvalue(), public_prefix="https://registry.test/extensions/example/"
        )


def test_production_delivery_is_exact_and_does_not_provision_or_delete_resources() -> None:
    workflow = Path(".github/workflows/production.yml").read_text(encoding="utf-8")
    assert "source_sha" in workflow
    assert "operation:" in workflow
    assert "- verify" in workflow
    assert "- deploy" in workflow
    assert "git ls-remote origin refs/heads/main" in workflow
    assert "CLOUDFLARE_API_TOKEN" in workflow
    assert "Verify Cloudflare production authority and resource identity" in workflow
    assert "if: inputs.operation == 'deploy'" in workflow
    assert "wrangler d1 migrations apply DB --remote" in workflow
    assert "pywrangler deploy" in workflow
    assert "https://registry.inkcre.dev" in workflow
    assert "wrangler d1 create" not in workflow
    assert "wrangler d1 delete" not in workflow
    assert "wrangler r2 bucket create" not in workflow
    assert "wrangler r2 bucket delete" not in workflow
    assert "inkcre-extension-registry-production-v2" in workflow


def test_pr_candidate_checks_are_secret_free_and_publish_one_static_document() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "name: ext-reg checks" in workflow
    assert "pull_request_target:" not in workflow
    assert "CLOUDFLARE_API_TOKEN" not in workflow
    assert "REGISTRY_PREVIEW_D1" not in workflow
    assert "REGISTRY_PREVIEW_R2" not in workflow
    assert "scripts/build_ui_preview.py" in workflow
    assert "ext-reg-ui-preview-${{ github.event.pull_request.head.sha }}" in workflow
    assert "retention-days: 1" in workflow
    assert "tests/fixtures/preview-seed.sql" not in workflow


def test_pages_preview_uses_the_trusted_controller_and_dedicated_authority() -> None:
    workflow = Path(".github/workflows/pages-preview.yml").read_text(encoding="utf-8")

    assert "workflow_run:" in workflow
    assert "run.path !== '.github/workflows/ci.yml'" in workflow
    assert "run.head_repository?.full_name" in workflow
    assert "eligible.length !== 1" in workflow
    assert "pull.head.sha !== process.env.PREVIEW_HEAD_SHA" in workflow
    assert "ref: ${{ github.workflow_sha }}" in workflow
    assert "environment:" in workflow
    assert "name: preview" in workflow
    assert "CLOUDFLARE_PAGES_API_TOKEN" in workflow
    assert "REGISTRY_UI_PREVIEW_PAGES_PROJECT" in workflow
    assert "pages-preview-ext-reg-${{ needs.identity.outputs.pull_number }}" in workflow
    assert "index.html" in workflow
    assert "preview.json" in workflow
    assert "_headers" in workflow
    assert "parse HTML" not in workflow
    assert "createDeployment" not in workflow
    assert "pywrangler deploy" not in workflow
    assert "wrangler d1" not in workflow
    assert "wrangler r2" not in workflow


def test_pages_preview_cleanup_is_trusted_exact_and_tombstoned() -> None:
    workflow = Path(".github/workflows/pages-preview-cleanup.yml").read_text(encoding="utf-8")

    assert "pull_request_target:" in workflow
    assert "pull.state !== 'closed'" in workflow
    assert "pull.head.repo?.full_name" in workflow
    assert "ref: ${{ github.workflow_sha }}" in workflow
    assert "pages-preview-ext-reg-${{" in workflow
    assert "pages-preview-closed" in workflow
    assert "pages deployment list" in workflow
    assert ".Branch == $branch" in workflow
    assert ".Id != $keep" in workflow
    assert "pages deployment delete" in workflow
    assert "for attempt in {1..12}" in workflow
    assert "This pull-request preview is no longer active." in workflow
    assert 'test "$verified" -eq 1' in workflow
    assert "actions/checkout" in workflow
    assert "github.event.pull_request.head.sha" not in workflow
    assert "createDeployment" not in workflow


def test_simple_content_negotiation_is_v1_1_and_fail_closed() -> None:
    assert negotiate_simple(None) == SIMPLE_HTML
    assert negotiate_simple("application/vnd.pypi.simple.v1+json") == SIMPLE_JSON
    assert negotiate_simple("text/html;q=0.5, application/json;q=1") == SIMPLE_JSON
    assert negotiate_simple("application/xml") is None


def test_native_client_accepts_exact_yanked_release_for_cold_restore() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/extensions/inkcre/twitter/releases/0.1.1"
        return httpx.Response(
            200,
            json={
                "name": "inkcre/twitter",
                "nickname": "Twitter",
                "version": "0.1.1",
                "state": "yanked",
                "python": {
                    "project": "inkcre-ext-twitter",
                    "simple_url": "/simple/inkcre-ext-twitter/",
                    "host_sdk": "core-py",
                    "host_sdk_version": ">=0.1.0 <0.2.0",
                    "entry_point": {
                        "group": "inkcre.core.extensions",
                        "name": "twitter",
                        "object": "extensions.twitter:Extension",
                    },
                },
                "module_federation": None,
            },
        )

    with RegistryClient("https://registry.test", transport=httpx.MockTransport(handler)) as client:
        release = client.get_release("inkcre", "twitter", "0.1.1")
    assert isinstance(release, ReleaseRecord)
    assert release.state == "yanked"
