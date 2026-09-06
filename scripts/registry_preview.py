"""Deploy/retire one isolated PR using built Python modules and native Wrangler.

Run from the trusted controller checkout; candidate code is uploaded, never
executed here. Credentials belong only to this process, not the Worker.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import secrets
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
WRANGLER = ["pnpm", "exec", "wrangler"]


def wrangler(*args: str) -> str:
    result = subprocess.run([*WRANGLER, *args], cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"Wrangler failed: {result.stderr}")
    return result.stdout


def api(client: httpx.Client, method: str, path: str, **kwargs):
    response = client.request(method, path, **kwargs)
    response.raise_for_status()
    body = response.json()
    if not body["success"]:
        raise RuntimeError(f"Cloudflare {method} {path}: {body['errors']}")
    return body.get("result")


def database(client: httpx.Client, name: str):
    matches = api(client, "GET", "d1/database", params={"name": name, "per_page": 100})
    return next((item for item in matches if item["name"] == name), None)


def bucket_exists(client: httpx.Client, name: str) -> bool:
    response = client.get(f"r2/buckets/{name}")
    if response.status_code == 404:
        return False
    response.raise_for_status()
    if not response.json()["success"]:
        raise RuntimeError("Cannot resolve preview bucket")
    return True


def wait_for(origin: str, path: str, expected: int = 200, **kwargs) -> httpx.Response:
    for _attempt in range(12):
        try:
            response = httpx.request("GET", origin + path, timeout=15, **kwargs)
            if response.status_code == expected:
                return response
        except httpx.TransportError:
            pass
        time.sleep(2)
    raise RuntimeError(f"Preview did not become ready: {origin}{path}")


def seed(origin: str, token: str) -> None:
    """Small real releases, admitted through the same public publisher API."""
    snapshot = io.BytesIO()
    with zipfile.ZipFile(snapshot, "w") as archive:
        archive.writestr(
            "mf-manifest.json",
            json.dumps(
                {
                    "id": "registry-sample",
                    "name": "registry-sample",
                    "metaData": {
                        "publicPath": "./",
                        "remoteEntry": {"name": "remoteEntry.js", "path": "", "type": "module"},
                    },
                    "exposes": [],
                    "shared": [],
                }
            ),
        )
        archive.writestr(
            "remoteEntry.js", "export const get = () => {}; export const init = () => {};"
        )
    with httpx.Client(
        base_url=origin, headers={"Authorization": f"Bearer {token}"}, timeout=60
    ) as publisher:
        for slug, nickname in [
            ("github", "GitHub"),
            ("rss", "RSS / Atom Feeds"),
            ("memos", "Memos"),
        ]:
            for version in ["1.0.0", "1.10.0", "2.0.0-rc.1"] if slug == "github" else ["1.0.0"]:
                base = f"/v1/extensions/demo/{slug}/releases"
                # Preserve reviewer edits on redeploy; only seed absent releases.
                existing = publisher.get(base + "/" + version)
                if existing.status_code == 200:
                    continue
                if existing.status_code != 404:
                    existing.raise_for_status()
                response = publisher.post(
                    base,
                    json={
                        "nickname": nickname,
                        "version": version,
                        "module_federation": {
                            "host_sdk": "@inkcre/core",
                            "host_sdk_version": "^0.1.0",
                            "source_repository": "https://github.com/InKCre/ext-reg",
                            "source_revision": "registry-preview-fixture-v1",
                        },
                    },
                )
                response.raise_for_status()
                response = publisher.post(
                    base + f"/{version}/module-federation",
                    files={"content": ("snapshot.zip", snapshot.getvalue(), "application/zip")},
                )
                response.raise_for_status()
                publisher.post(base + f"/{version}/publish").raise_for_status()


def deploy(client: httpx.Client, name: str, origin: str, artifact: Path, revision: str) -> None:
    token = os.environ["REGISTRY_PREVIEW_PUBLISHER_TOKEN"]
    if len(token) < 32:
        raise ValueError("Use a dedicated random preview publisher token of at least 32 characters")
    db = database(client, name) or api(client, "POST", "d1/database", json={"name": name})
    if not bucket_exists(client, name):
        api(client, "POST", "r2/buckets", json={"name": name})
    config = json.loads((ROOT / ".github/preview/wrangler.json").read_text())
    config.update(
        name=name,
        main="src/worker.py",
        vars={"PUBLIC_ORIGIN": origin},
        d1_databases=[
            {
                "binding": "DB",
                "database_name": name,
                "database_id": db["uuid"],
                "migrations_dir": "migrations",
            }
        ],
        r2_buckets=[{"binding": "ARTIFACTS", "bucket_name": name}],
    )
    config_path = artifact / "wrangler.json"
    config_path.write_text(json.dumps(config))
    wrangler("d1", "migrations", "apply", "DB", "--remote", "--config", str(config_path))
    for sql, params in [
        ("INSERT OR IGNORE INTO namespaces(name) VALUES ('demo')", []),
        ("DELETE FROM credentials WHERE namespace = 'demo' AND label = 'PR reviewer'", []),
        (
            "INSERT INTO credentials(token_hash, namespace, label) "
            "VALUES (?, 'demo', 'PR reviewer')",
            [hashlib.sha256(token.encode()).hexdigest()],
        ),
    ]:
        api(client, "POST", f"d1/database/{db['uuid']}/query", json={"sql": sql, "params": params})
    print(
        wrangler(
            "deploy",
            "--config",
            str(config_path),
            "--message",
            f"Registry PR at {revision}",
            "--strict",
        )
    )
    assert wait_for(origin, "/livez").json()["status"] == "ok"
    wait_for(origin, "/v1/extensions")
    seed(origin, token)
    assert "Extension Registry" in wait_for(origin, "/").text
    wait_for(origin, "/explore/demo/github")
    wait_for(origin, "/publish")
    wait_for(origin, "/v1/publisher", expected=401)
    wait_for(origin, "/simple/")
    manifest = wait_for(origin, "/extensions/demo/github/1.10.0/module-federation/mf-manifest.json")
    assert origin in manifest.text
    print(f"Preview: {origin}\nSource: {revision}\nD1/R2/Worker: {name}")
    if os.environ.get("GITHUB_OUTPUT"):
        with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
            output.write(f"url={origin}\n")


def retire(client: httpx.Client, name: str, origin: str) -> None:
    # Stop new application writes before emptying R2. Wrangler has no object-list
    # command; a temporary replacement uses the native list/delete binding API.
    if bucket_exists(client, name):
        token = secrets.token_urlsafe(32)
        with tempfile.TemporaryDirectory() as temporary:
            config_path = Path(temporary) / "wrangler.json"
            config_path.write_text(
                json.dumps(
                    {
                        "name": name,
                        "main": str(ROOT / ".github/preview/retire.js"),
                        "compatibility_date": "2026-07-28",
                        "workers_dev": True,
                        "preview_urls": False,
                        "observability": {"enabled": True},
                        "vars": {"RETIRE_TOKEN": token},
                        "r2_buckets": [{"binding": "ARTIFACTS", "bucket_name": name}],
                    }
                )
            )
            wrangler("deploy", "--config", str(config_path), "--message", "Retire closed PR")
            wait_for(origin, "/", expected=410)
            # Allow pre-replacement requests (including uploads) to finish.
            time.sleep(30)
            with httpx.Client(
                base_url=origin, headers={"Authorization": f"Bearer {token}"}, timeout=60
            ) as drain:
                while True:
                    response = drain.post("/")
                    response.raise_for_status()
                    if response.json()["deleted"] == 0:
                        break
        api(client, "DELETE", f"r2/buckets/{name}")
    response = client.delete(f"workers/scripts/{name}")
    if response.status_code != 404:
        response.raise_for_status()
        if not response.json()["success"]:
            raise RuntimeError("Could not delete preview Worker")
    db = database(client, name)
    if db:
        api(client, "DELETE", f"d1/database/{db['uuid']}")
    print(f"Retired Worker, D1 and R2: {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["deploy", "retire"])
    parser.add_argument("--pull-number", type=int, required=True)
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--source-sha")
    args = parser.parse_args()
    if args.pull_number < 1:
        parser.error("pull-number must be positive")
    if args.operation == "deploy" and (
        args.artifact is None or not re.fullmatch(r"[0-9a-f]{40}", args.source_sha or "")
    ):
        parser.error("deploy requires artifact and exact source-sha")
    name = f"inkcre-ext-reg-pr-{args.pull_number}"
    account = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    token = (
        os.environ.get("CLOUDFLARE_API_TOKEN")
        or json.loads(wrangler("auth", "token", "--json"))["token"]
    )
    with httpx.Client(
        base_url=f"https://api.cloudflare.com/client/v4/accounts/{account}/",
        headers={"Authorization": f"Bearer {token}"},
        timeout=120,
    ) as client:
        subdomain = api(client, "GET", "workers/subdomain")["subdomain"]
        origin = f"https://{name}.{subdomain}.workers.dev"
        if args.operation == "deploy":
            deploy(client, name, origin, args.artifact.resolve(), args.source_sha)
        else:
            retire(client, name, origin)


if __name__ == "__main__":
    main()
