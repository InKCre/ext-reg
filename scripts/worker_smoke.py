from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import httpx

from inkcre_extension_registry.cli import build_target_manifest
from inkcre_extension_registry.client import RegistryClient
from inkcre_extension_registry.contracts.models import TargetAssociation, TargetPublishConfig

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry-url", default="http://127.0.0.1:8791")
    parser.add_argument("--token", required=True)
    arguments = parser.parse_args()

    config_path = ROOT / "tests/fixtures/web-target.json"
    artifact_directory = ROOT / "tests/fixtures/web-target"
    config = TargetPublishConfig.model_validate_json(config_path.read_text(encoding="utf-8"))
    manifest = build_target_manifest(config, artifact_directory)
    association = TargetAssociation(
        manifest=manifest,
        source_repository="https://github.com/InKCre/ext-reg",
        source_revision="0" * 40,
        build_id="worker-smoke",
    )

    with RegistryClient(arguments.registry_url, token=arguments.token) as publisher:
        for relative_path, descriptor in manifest.files.items():
            publisher.put_blob(
                f"sha256:{descriptor.sha256}",
                (artifact_directory / relative_path).read_bytes(),
                descriptor.media_type,
            )
        target = publisher.put_target(
            config.namespace,
            config.name,
            config.version,
            config.target_key,
            association,
        )
        publisher.publish(config.namespace, config.name, config.version)

    with RegistryClient(arguments.registry_url) as consumer:
        release = consumer.get_release(config.namespace, config.name, config.version)
        assert release.state == "published"
        assert release.targets == (target,)
        manifest_url = consumer.artifact_manifest_url(target.target_digest)
        file_url = consumer.artifact_file_url(target.target_digest, manifest.entrypoint)

    manifest_response = httpx.get(manifest_url)
    manifest_response.raise_for_status()
    assert manifest_response.headers["cache-control"].endswith("immutable")
    assert manifest_response.json() == manifest.model_dump(mode="json")

    file_response = httpx.get(file_url)
    file_response.raise_for_status()
    descriptor = manifest.files[manifest.entrypoint]
    assert hashlib.sha256(file_response.content).hexdigest() == descriptor.sha256
    assert file_response.headers["access-control-allow-origin"] == "*"
    assert file_response.headers["cache-control"].endswith("immutable")


if __name__ == "__main__":
    main()
