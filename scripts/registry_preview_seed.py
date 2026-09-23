"""Publish one pinned, installable Release into an isolated Registry preview."""

from __future__ import annotations

import argparse
import hashlib
import os

import httpx

VERSION = "0.2.1"
WHEEL_NAME = "inkcre_ext_rss-0.2.1-py3-none-any.whl"
WHEEL_SHA256 = "190ff7d15b11a341c2367b87b2348832e7fe7d8042da512f2996926645a6d275"
WHEEL_URL = f"https://registry.inkcre.dev/packages/inkcre-ext-rss/{VERSION}/{WHEEL_NAME}"
RELEASE_PATH = f"/v1/extensions/inkcre/rss/releases/{VERSION}"
PACKAGE_PATH = f"/packages/inkcre-ext-rss/{VERSION}/{WHEEL_NAME}"


def seed(origin: str, token: str) -> None:
    with httpx.Client(
        base_url=origin, headers={"Authorization": f"Bearer {token}"}, timeout=60
    ) as registry:
        current = registry.get(RELEASE_PATH)
        if current.status_code == 404:
            wheel_response = httpx.get(WHEEL_URL, timeout=60)
            wheel_response.raise_for_status()
            wheel = wheel_response.content
            if hashlib.sha256(wheel).hexdigest() != WHEEL_SHA256:
                raise RuntimeError("Pinned RSS preview wheel digest changed")

            prepared = registry.post(
                "/v1/extensions/inkcre/rss/releases",
                json={
                    "nickname": "RSS/Atom Feeds",
                    "version": VERSION,
                    "python": {
                        "project": "inkcre-ext-rss",
                        "host_sdk": "core-py",
                        "host_sdk_version": ">=0.2.0 <0.4.0",
                        "entry_point": {
                            "group": "inkcre.core.extensions",
                            "name": "rss",
                            "object": "extensions.rss:Extension",
                        },
                        "source_repository": "https://github.com/InKCre/core-py",
                        "source_revision": "8f7a17343c13f6c4af19e5ea9b58ceb6b13654c2",
                        "build_id": "35591185410",
                    },
                },
            )
            prepared.raise_for_status()
            uploaded = registry.post(
                "/legacy/",
                data={
                    ":action": "file_upload",
                    "protocol_version": "1",
                    "name": "inkcre-ext-rss",
                    "version": VERSION,
                    "filetype": "bdist_wheel",
                    "metadata_version": "2.4",
                    "sha256_digest": WHEEL_SHA256,
                },
                files={"content": (WHEEL_NAME, wheel, "application/octet-stream")},
            )
            uploaded.raise_for_status()
            published = registry.post(RELEASE_PATH + "/publish")
            published.raise_for_status()
        else:
            current.raise_for_status()

        release = registry.get(RELEASE_PATH)
        release.raise_for_status()
        record = release.json()
        if (
            record["name"] != "inkcre/rss"
            or record["version"] != VERSION
            or record["state"] != "published"
            or record["nickname"] != "RSS/Atom Feeds"
            or record["python"]["project"] != "inkcre-ext-rss"
            or record["python"]["host_sdk"] != "core-py"
            or record["python"]["host_sdk_version"] != ">=0.2.0 <0.4.0"
            or record["python"]["entry_point"]
            != {
                "group": "inkcre.core.extensions",
                "name": "rss",
                "object": "extensions.rss:Extension",
            }
            or record["module_federation"] is not None
        ):
            raise RuntimeError("Preview RSS Release conflicts with the pinned fixture")
        package = registry.head(PACKAGE_PATH)
        package.raise_for_status()
        if package.headers.get("etag") != f'"{WHEEL_SHA256}"':
            raise RuntimeError("Preview RSS wheel does not match the pinned fixture")
        catalog = registry.get("/v1/extensions")
        catalog.raise_for_status()
        if not any(item["name"] == "inkcre/rss" for item in catalog.json()):
            raise RuntimeError("Preview RSS Release is missing from the catalog")
        registry.get(f"/explore/inkcre/rss?version={VERSION}").raise_for_status()
    print(f"Preview fixture ready: inkcre/rss {VERSION}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True)
    args = parser.parse_args()
    seed(args.origin, os.environ["INKCRE_PREVIEW_SEED_TOKEN"])
