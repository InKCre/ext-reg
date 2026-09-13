"""Exercise the built Worker against disposable local D1/R2, without credentials.

Run after `pnpm worker:build`. Fixtures and injected database failure exist only
inside a TemporaryDirectory; this command cannot target a deployed Registry.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import secrets
import shutil
import signal
import socket
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path

import httpx
from sqlalchemy import DDL, create_engine, insert, select, update

from inkcre_extension_registry.service import database as db

ROOT = Path(__file__).resolve().parents[1]


def archive(files: dict[str, str]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as bundle:
        for name, content in files.items():
            bundle.writestr(name, content)
    return output.getvalue()


def journey(client: httpx.Client, engine, token: str, other_token: str) -> None:
    authorization = {"Authorization": f"Bearer {token}"}

    def request(method: str, path: str, expected: int = 200, *, private=False, **kwargs):
        response = client.request(method, path, headers=authorization if private else {}, **kwargs)
        assert response.status_code == expected, (
            f"{method} {path}: expected {expected}, got {response.status_code}: "
            f"{response.text[:800]}"
        )
        return response

    release_path = "/v1/extensions/check/extension/releases"
    version_path = release_path + "/1.0.0"
    source = {"source_repository": "https://example.invalid/check", "source_revision": "rev' ? --"}
    association = {
        "nickname": "Publisher's extension",
        "version": "1.0.0",
        "python": {
            **source,
            "project": "check-extension",
            "host_sdk": "core-py",
            "host_sdk_version": "^1.0.0",
            "entry_point": {
                "group": "inkcre.core.extensions",
                "name": "check",
                "object": "check:Extension",
            },
        },
        "module_federation": {**source, "host_sdk": "@inkcre/core", "host_sdk_version": "^1.0.0"},
    }
    assert request("GET", "/v1/extensions").json() == []
    request("GET", "/")
    request("GET", "/v1/publisher", 401)
    request("POST", "/v1/extensions/other/extension/releases", 403, private=True, json=association)
    request("POST", release_path, private=True, json=association)
    request("POST", release_path, private=True, json=association)
    request("POST", release_path, 409, private=True, json={**association, "nickname": "Changed"})
    request("GET", version_path, 404)
    request("POST", version_path + "/publish", 409, private=True)
    workspace = request("GET", "/v1/publisher", private=True).json()
    assert len(workspace["releases"]) == 1
    assert not workspace["releases"][0]["python_uploaded"]
    assert not workspace["releases"][0]["web_uploaded"]
    with engine.connect() as connection:
        row = connection.execute(select(db.python_distributions)).mappings().one()
        assert row["source_revision"] == source["source_revision"] and row["build_id"] is None

    metadata = "Metadata-Version: 2.3\nName: check-extension\nVersion: 1.0.0\n\n"
    wheel = archive(
        {
            "check.py": "class Extension: pass\n",
            "check_extension-1.0.0.dist-info/METADATA": metadata,
            "check_extension-1.0.0.dist-info/entry_points.txt": (
                "[inkcre.core.extensions]\ncheck = check:Extension\n"
            ),
            "check_extension-1.0.0.dist-info/WHEEL": (
                "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
            ),
            "check_extension-1.0.0.dist-info/RECORD": "",
        }
    )
    wheel_name = "check_extension-1.0.0-py3-none-any.whl"
    for _ in range(2):
        request(
            "POST",
            "/legacy/",
            private=True,
            data={
                ":action": "file_upload",
                "protocol_version": "1",
                "name": "check-extension",
                "version": "1.0.0",
                "filetype": "bdist_wheel",
                "metadata_version": "2.3",
                "sha256_digest": hashlib.sha256(wheel).hexdigest(),
            },
            files={"content": (wheel_name, wheel)},
        )
    snapshot = archive(
        {
            "mf-manifest.json": json.dumps(
                {
                    "metaData": {
                        "publicPath": "./",
                        "remoteEntry": {"name": "remoteEntry.js", "path": ""},
                    }
                }
            ),
            "remoteEntry.js": "export const check = true;",
        }
    )
    for _ in range(2):
        request(
            "POST",
            version_path + "/module-federation",
            private=True,
            files={"content": ("extension.zip", snapshot)},
        )
    uploaded = request("GET", "/v1/publisher", private=True).json()["releases"][0]
    assert uploaded["python_uploaded"] and uploaded["web_uploaded"]
    request("POST", version_path + "/publish", private=True)
    request("POST", version_path + "/publish", private=True)
    assert request("GET", "/v1/extensions").json()[0]["name"] == "check/extension"
    request("GET", "/explore/check/extension?version=1.0.0")
    request("GET", "/v1/extensions/check/extension")
    assert request("GET", version_path).json()["state"] == "published"
    request("GET", "/simple/")
    request("GET", "/simple/check-extension/")
    package_path = f"/packages/check-extension/1.0.0/{wheel_name}"
    web_path = "/extensions/check/extension/1.0.0/module-federation/remoteEntry.js"
    assert request("GET", package_path).content == wheel
    assert request("GET", package_path + ".metadata").text == metadata
    request("GET", web_path)
    request("GET", web_path.replace("remoteEntry.js", "mf-manifest.json"))

    reason = "Publisher's withdrawal ?"
    request("POST", version_path + "/yank", private=True, json={"reason": reason})
    assert request("GET", version_path).json()["state"] == "yanked"
    assert request("GET", "/v1/extensions").json() == []
    request("GET", package_path)
    simple = client.get(
        "/simple/check-extension/", headers={"Accept": "application/vnd.pypi.simple.v1+json"}
    )
    assert simple.json()["files"][0]["yanked"] == reason
    request("POST", version_path + "/unyank", private=True)
    assert request("GET", version_path).json()["state"] == "published"
    with engine.connect() as connection:
        row = connection.execute(select(db.releases)).mappings().one()
        assert row["yank_reason"] is None and row["published_at"] and row["updated_at"]

    # Exercise correlated readiness expressions and the private pagination boundary.
    for minor in range(1, 11):
        request(
            "POST",
            release_path,
            private=True,
            json={
                "nickname": association["nickname"],
                "version": f"1.{minor}.0",
                "module_federation": association["module_federation"],
            },
        )
    first = request("GET", "/v1/publisher", private=True).json()
    last = request("GET", "/v1/publisher?offset=10", private=True).json()
    assert len(first["releases"]) == 10 and first["next_offset"] == 10
    assert len(last["releases"]) == 1 and last["next_offset"] is None
    entries = first["releases"] + last["releases"]
    assert len({entry["version"] for entry in entries}) == 11
    assert sum(entry["python_uploaded"] for entry in entries) == 1
    assert sum(entry["web_uploaded"] for entry in entries) == 1
    other = client.get("/v1/publisher", headers={"Authorization": f"Bearer {other_token}"})
    assert other.status_code == 200 and other.json()["namespace"] == "other"
    assert other.json()["releases"] == []

    # Fail an association insert after extension and release inserts.
    # Native D1 batch must roll back both identities; HTTP cannot inject this failure.
    with engine.begin() as connection:
        connection.execute(
            DDL("""
            CREATE TRIGGER fail_association BEFORE INSERT ON python_distributions
            WHEN NEW.extension_name = 'check/atomic'
            BEGIN SELECT RAISE(ABORT, 'injected association failure'); END
        """)
        )
    request(
        "POST",
        "/v1/extensions/check/atomic/releases",
        409,
        private=True,
        json={**association, "version": "2.0.0"},
    )
    with engine.connect() as connection:
        assert (
            connection.execute(
                select(db.extensions).where(db.extensions.c.name == "check/atomic")
            ).first()
            is None
        )
        assert (
            connection.execute(
                select(db.releases).where(db.releases.c.extension_name == "check/atomic")
            ).first()
            is None
        )

    with engine.begin() as connection:
        connection.execute(
            update(db.releases).where(db.releases.c.version == "1.0.0").values(state="blocked")
        )
    request("GET", version_path, 451)
    request("GET", package_path, 451)
    request("GET", web_path, 451)
    assert "check-extension" not in request("GET", "/simple/").text
    with engine.begin() as connection:
        connection.execute(update(db.credentials).values(disabled=1))
    request("GET", "/v1/publisher", 401, private=True)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="registry-check-") as directory:
        root = Path(directory)
        shutil.copytree(ROOT / "dist/worker", root / "worker")
        shutil.move(root / "worker/python_modules", root / "python_modules")
        shutil.copytree(ROOT / "migrations", root / "migrations")
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        origin = f"http://127.0.0.1:{port}"
        config = json.loads((ROOT / ".github/preview/wrangler.json").read_text())
        config.update(
            name="registry-check",
            main="worker/worker.py",
            vars={"PUBLIC_ORIGIN": origin},
            d1_databases=[
                {
                    "binding": "DB",
                    "database_name": "registry-check",
                    "database_id": "local",
                    "migrations_dir": "migrations",
                }
            ],
            r2_buckets=[{"binding": "ARTIFACTS", "bucket_name": "registry-check"}],
        )
        config_path = root / "wrangler.json"
        config_path.write_text(json.dumps(config))
        state = root / "state"
        command = ["pnpm", "exec", "wrangler"]
        options = ["--config", str(config_path), "--persist-to", str(state)]
        subprocess.run(
            [*command, "d1", "migrations", "apply", "DB", "--local", *options],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        databases = [
            path for path in (state / "v3/d1").rglob("*.sqlite") if path.name != "metadata.sqlite"
        ]
        assert len(databases) == 1, "Expected exactly one disposable local D1 database"
        engine = create_engine(f"sqlite:///{databases[0]}")
        token = secrets.token_urlsafe(32)
        other_token = secrets.token_urlsafe(32)
        try:
            with engine.begin() as connection:
                connection.execute(insert(db.namespaces), [{"name": "check"}, {"name": "other"}])
                connection.execute(
                    insert(db.credentials).values(
                        token_hash=hashlib.sha256(token.encode()).hexdigest(),
                        namespace="check",
                        label="Disposable check",
                    )
                )
                connection.execute(
                    insert(db.credentials).values(
                        token_hash=hashlib.sha256(other_token.encode()).hexdigest(),
                        namespace="other",
                        label="Disposable isolation check",
                    )
                )
            with (root / "worker.log").open("w+") as log:
                process = subprocess.Popen(
                    [*command, "dev", "--ip", "127.0.0.1", "--port", str(port), *options],
                    cwd=ROOT,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                try:
                    with httpx.Client(base_url=origin, timeout=15) as client:
                        deadline = time.monotonic() + 60
                        while time.monotonic() < deadline:
                            if process.poll() is not None:
                                raise RuntimeError("Local Worker exited before becoming ready")
                            try:
                                if client.get("/livez", timeout=1).status_code == 200:
                                    break
                            except httpx.TransportError:
                                pass
                            time.sleep(0.5)
                        else:
                            raise RuntimeError("Local Worker did not become ready")
                        journey(client, engine, token, other_token)
                    print("Registry persistence checks passed against local Worker, D1 and R2.")
                except BaseException:
                    log.seek(0)
                    print(log.read()[-12000:])
                    raise
                finally:
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=15)
        finally:
            engine.dispose()


if __name__ == "__main__":
    main()
