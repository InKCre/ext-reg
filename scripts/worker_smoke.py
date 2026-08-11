from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import zipfile
from importlib.metadata import distributions
from pathlib import Path

import httpx

from inkcre_extension_registry.client import RegistryClient
from inkcre_extension_registry.contracts.models import PrepareReleaseRequest


def _snapshot() -> bytes:
    manifest = {
        "id": "blackbox",
        "name": "blackbox",
        "metaData": {
            "publicPath": "./",
            "remoteEntry": {"path": "", "name": "remoteEntry.js", "type": "module"},
        },
        "shared": [],
        "exposes": [
            {
                "name": "./extension",
                "assets": {
                    "js": {"sync": ["extension.js"], "async": []},
                    "css": {"sync": [], "async": []},
                },
            }
        ],
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("mf-manifest.json", json.dumps(manifest))
        archive.writestr("remoteEntry.js", "export default {};\n")
        archive.writestr("extension.js", "export const extension = {};\n")
    return buffer.getvalue()


def _wheel() -> tuple[str, bytes, bytes]:
    filename = "inkcre_ext_blackbox-0.2.0-py3-none-any.whl"
    dist_info = "inkcre_ext_blackbox-0.2.0.dist-info"
    metadata = (
        b"Metadata-Version: 2.4\n"
        b"Name: inkcre-ext-blackbox\n"
        b"Version: 0.2.0\n"
        b"Requires-Python: >=3.12,<3.14\n\n"
    )
    files = {
        "extensions/blackbox.py": b"class Extension: pass\n",
        f"{dist_info}/METADATA": metadata,
        f"{dist_info}/WHEEL": b"Wheel-Version: 1.0\nGenerator: ext-reg-smoke\nTag: py3-none-any\n",
        f"{dist_info}/entry_points.txt": (
            b"[inkcre.core.extensions]\nblackbox = extensions.blackbox:Extension\n"
        ),
    }
    record_rows: list[str] = []
    for path, content in files.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=").decode()
        record_rows.append(f"{path},sha256={digest},{len(content)}")
    record_path = f"{dist_info}/RECORD"
    files[record_path] = ("\n".join(record_rows) + f"\n{record_path},,\n").encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, content in files.items():
            archive.writestr(path, content)
    return filename, buffer.getvalue(), metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry-url", default="http://127.0.0.1:8791")
    parser.add_argument("--token", required=True)
    arguments = parser.parse_args()
    python_payload = PrepareReleaseRequest.model_validate(
        {
            "nickname": "Python Blackbox",
            "version": "0.2.0",
            "python": {
                "project": "inkcre-ext-blackbox",
                "host_sdk": "core-py",
                "host_sdk_version": ">=0.1.0 <0.2.0",
                "entry_point": {
                    "group": "inkcre.core.extensions",
                    "name": "blackbox",
                    "object": "extensions.blackbox:Extension",
                },
                "source_repository": "https://github.com/InKCre/ext-reg",
                "source_revision": "0" * 40,
                "build_id": "worker-smoke",
            },
        }
    )
    payload = PrepareReleaseRequest.model_validate(
        {
            "nickname": "Blackbox",
            "version": "0.2.0",
            "module_federation": {
                "host_sdk": "@inkcre/core",
                "host_sdk_version": ">=0.1.0 <0.2.0",
                "source_repository": "https://github.com/InKCre/ext-reg",
                "source_revision": "0" * 40,
                "build_id": "worker-smoke",
            },
        }
    )
    filename, wheel, metadata = _wheel()
    with RegistryClient(arguments.registry_url, token=arguments.token) as publisher:
        publisher.prepare("inkcre", "python-blackbox", python_payload)
        publisher.prepare("inkcre", "blackbox", payload)
        publisher.upload_module_federation("inkcre", "blackbox", "0.2.0", _snapshot())
        publisher.publish("inkcre", "blackbox", "0.2.0")

    with tempfile.TemporaryDirectory(prefix="inkcre-registry-smoke-") as directory:
        wheel_path = Path(directory) / filename
        wheel_path.write_bytes(wheel)
        subprocess.run(
            [
                "uv",
                "publish",
                "--publish-url",
                arguments.registry_url.rstrip("/") + "/legacy/",
                "--username",
                "__token__",
                "--password",
                arguments.token,
                "--no-attestations",
                "--no-progress",
                str(wheel_path),
            ],
            check=True,
        )

    with RegistryClient(arguments.registry_url, token=arguments.token) as publisher:
        publisher.publish("inkcre", "python-blackbox", "0.2.0")

    with RegistryClient(arguments.registry_url) as consumer:
        release = consumer.get_release("inkcre", "blackbox", "0.2.0")
        assert release.state == "published"
        assert release.module_federation is not None
        manifest_url = arguments.registry_url.rstrip("/") + release.module_federation.manifest_url

    manifest_response = httpx.get(manifest_url)
    manifest_response.raise_for_status()
    assert manifest_response.headers["access-control-allow-origin"] == "*"
    assert manifest_response.headers["cache-control"].endswith("immutable")
    public_path = manifest_response.json()["metaData"]["publicPath"]
    assert public_path.startswith(arguments.registry_url.rstrip("/") + "/extensions/")
    remote_response = httpx.get(public_path + "remoteEntry.js")
    remote_response.raise_for_status()
    assert remote_response.text == "export default {};\n"

    simple_response = httpx.get(
        arguments.registry_url.rstrip("/") + "/simple/inkcre-ext-blackbox/",
        headers={"Accept": "application/vnd.pypi.simple.v1+json"},
    )
    simple_response.raise_for_status()
    file_record = simple_response.json()["files"][0]
    assert file_record["filename"] == filename
    assert file_record["hashes"]["sha256"] == hashlib.sha256(wheel).hexdigest()
    package_url = arguments.registry_url.rstrip("/") + file_record["url"]
    package_response = httpx.get(package_url)
    package_response.raise_for_status()
    assert package_response.content == wheel
    metadata_response = httpx.get(package_url + ".metadata")
    metadata_response.raise_for_status()
    assert metadata_response.content == metadata

    missing_package = httpx.get(
        arguments.registry_url.rstrip("/") + "/packages/missing/0.0.0/missing.whl"
    )
    assert missing_package.status_code == 404
    assert missing_package.headers["cache-control"] == "no-store"
    missing_mf_asset = httpx.get(
        arguments.registry_url.rstrip("/")
        + "/extensions/inkcre/missing/0.0.0/module-federation/missing.js"
    )
    assert missing_mf_asset.status_code == 404
    assert missing_mf_asset.headers["cache-control"] == "no-store"

    with tempfile.TemporaryDirectory(prefix="inkcre-registry-install-") as directory:
        site_packages = Path(directory) / "site-packages"
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--target",
                str(site_packages),
                "--index-url",
                arguments.registry_url.rstrip("/") + "/simple/",
                "--no-deps",
                "inkcre-ext-blackbox==0.2.0",
            ],
            check=True,
        )
        sys.path.insert(0, str(site_packages))
        try:
            installed = next(
                distribution
                for distribution in distributions(path=[str(site_packages)])
                if distribution.metadata["Name"] == "inkcre-ext-blackbox"
            )
            entry_point = next(
                entry
                for entry in installed.entry_points
                if entry.group == "inkcre.core.extensions" and entry.name == "blackbox"
            )
            assert entry_point.load().__name__ == "Extension"
        finally:
            sys.path.remove(str(site_packages))


if __name__ == "__main__":
    main()
