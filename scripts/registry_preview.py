"""Trusted controller for one PR's Heroku app, Neon branch and private R2 bucket.

The candidate image receives database and bucket credentials only. Provider
control tokens stay on this runner. Docker and Heroku own image delivery;
provider REST calls configure the resources and credentials that the app needs.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import secrets
import subprocess
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import unquote, urlsplit

import boto3
import httpx
from botocore.config import Config
from registry_database import configure_runtime_login


def request(client: httpx.Client, method: str, path: str, *, missing=False, **kwargs):
    response = client.request(method, path, **kwargs)
    if missing and response.status_code == 404:
        return None
    response.raise_for_status()
    if not response.content:
        return None
    body = response.json()
    if isinstance(body, dict) and "success" in body:
        if not body["success"]:
            raise RuntimeError(f"Provider rejected {method} {path}")
        return body["result"]
    return body


def run(*args: str, input: str | None = None, env: dict | None = None) -> str:
    result = subprocess.run(args, input=input, env=env, capture_output=True, text=True)
    if result.returncode:
        # Candidate programs may print their credentials. Never forward their
        # output into a trusted deployment log.
        raise RuntimeError(f"{args[0]} command failed (exit {result.returncode})")
    return result.stdout


def wait_operations(neon: httpx.Client, result: dict) -> None:
    for operation in result.get("operations", []):
        for _ in range(90):
            state = request(neon, "GET", f"operations/{operation['id']}")["operation"]["status"]
            if state in {"finished", "skipped"}:
                break
            if state in {"failed", "error", "cancelled"}:
                raise RuntimeError("Neon operation failed")
            time.sleep(2)
        else:
            raise TimeoutError("Neon operation did not finish")


def find_branch(neon: httpx.Client, name: str):
    result = request(neon, "GET", "branches", params={"search": name, "limit": 10000})
    if result.get("pagination", {}).get("next"):
        raise RuntimeError("Neon branch search was truncated")
    matches = [branch for branch in result["branches"] if branch["name"] == name]
    if len(matches) > 1:
        raise RuntimeError("Ambiguous Neon preview branch")
    return matches[0] if matches else None


def smoke(origin: str, revision: str) -> None:
    for _ in range(30):
        try:
            with httpx.Client(base_url=origin, timeout=20) as client:
                assert client.get("/livez").json() == {"status": "ok", "revision": revision}
                for path in ("/", "/publish", "/v1/extensions", "/simple/"):
                    client.get(path).raise_for_status()
                assert client.get("/v1/publisher").status_code == 401
            return
        except (httpx.HTTPError, AssertionError, ValueError):
            time.sleep(2)
    raise RuntimeError("Deployed Registry did not pass anonymous smoke checks")


def deploy(heroku, neon, cloudflare, name: str, branch_name: str, image: str, revision: str):
    app = request(heroku, "GET", f"apps/{name}", missing=True)
    if app is None:
        app = request(
            heroku, "POST", "apps", json={"name": name, "region": "us", "stack": "container"}
        )
    if app["stack"]["name"] != "container":
        raise ValueError("Preview app must use the container stack")
    origin = app["web_url"].rstrip("/")
    config = request(heroku, "GET", f"apps/{name}/config-vars")
    if config.get("S3_BUCKET") not in {None, name}:
        raise ValueError("Existing app bucket does not belong to this PR")
    branch = find_branch(neon, branch_name)
    if branch is None:
        result = request(
            neon,
            "POST",
            "branches",
            json={
                "branch": {
                    "name": branch_name,
                    "parent_id": os.environ["NEON_PREVIEW_PARENT_BRANCH_ID"],
                },
                "endpoints": [
                    {
                        "type": "read_write",
                        "autoscaling_limit_min_cu": 0.25,
                        "autoscaling_limit_max_cu": 0.25,
                    }
                ],
            },
        )
        wait_operations(neon, result)
        branch = result["branch"]
    if branch["default"] or branch["protected"]:
        raise ValueError("A default or protected branch cannot be a PR preview")
    # A newly inherited role password must never be handed to candidate code.
    if config.get("REGISTRY_NEON_BRANCH_ID") != branch["id"]:
        wait_operations(
            neon,
            request(neon, "POST", f"branches/{branch['id']}/roles/registry_owner/reset_password"),
        )
    expiry = (datetime.now(UTC) + timedelta(days=7)).isoformat()
    wait_operations(
        neon,
        request(neon, "PATCH", f"branches/{branch['id']}", json={"branch": {"expires_at": expiry}}),
    )
    owner_url = request(
        neon,
        "GET",
        "connection_uri",
        params={
            "branch_id": branch["id"],
            "database_name": "registry",
            "role_name": "registry_owner",
            "pooled": "false",
        },
    )["uri"]
    database_env = {**os.environ, "MIGRATION_DATABASE_URL": owner_url}
    run(
        "docker",
        "run",
        "--rm",
        "--env",
        "MIGRATION_DATABASE_URL",
        image,
        "tortoise",
        "-c",
        "inkcre_extension_registry.migration_config.TORTOISE_ORM",
        "upgrade",
        env=database_env,
    )
    previous = urlsplit(config.get("DATABASE_URL", ""))
    password = (
        unquote(previous.password)
        if previous.username == "registry_app"
        and previous.password
        and config.get("REGISTRY_NEON_BRANCH_ID") == branch["id"]
        else secrets.token_urlsafe(32)
    )
    runtime_url = configure_runtime_login(owner_url, password)
    config.update(
        DATABASE_URL=runtime_url,
        MIGRATION_DATABASE_URL=None,
        REGISTRY_NEON_BRANCH_ID=branch["id"],
    )
    if request(cloudflare, "GET", f"r2/buckets/{name}", missing=True) is None:
        request(cloudflare, "POST", "r2/buckets", json={"name": name})
    if not config.get("AWS_SECRET_ACCESS_KEY"):
        groups = request(cloudflare, "GET", "tokens/permission_groups")
        group = next(g for g in groups if g["name"] == "Workers R2 Storage Bucket Item Write")
        account = os.environ["CLOUDFLARE_ACCOUNT_ID"]
        token = request(
            cloudflare,
            "POST",
            "tokens",
            json={
                "name": f"{name}-objects",
                "policies": [
                    {
                        "effect": "allow",
                        "resources": {
                            f"com.cloudflare.edge.r2.bucket.{account}_default_{name}": "*"
                        },
                        "permission_groups": [{"id": group["id"]}],
                    }
                ],
            },
        )
        config.update(
            AWS_ACCESS_KEY_ID=token["id"],
            AWS_SECRET_ACCESS_KEY=hashlib.sha256(token["value"].encode()).hexdigest(),
        )
    config.update(
        PUBLIC_ORIGIN=origin,
        S3_BUCKET=name,
        S3_ENDPOINT_URL=f"https://{os.environ['CLOUDFLARE_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        # The image owns revision; a config change must not relabel an old process.
        REGISTRY_SOURCE_REVISION=None,
    )
    request(heroku, "PATCH", f"apps/{name}/config-vars", json=config)
    database_env = {**os.environ, "DATABASE_URL": runtime_url}
    run(
        "docker",
        "run",
        "--rm",
        "-i",
        "--env",
        "DATABASE_URL",
        image,
        "python",
        "-m",
        "inkcre_extension_registry.admin",
        "grant",
        "reviewer",
        "--label",
        "PR reviewer",
        env=database_env,
        input=os.environ["REGISTRY_PREVIEW_PUBLISHER_TOKEN"] + "\n",
    )
    run(
        "docker",
        "login",
        "--username",
        "_",
        "--password-stdin",
        "registry.heroku.com",
        input=os.environ["HEROKU_API_KEY"],
    )
    target = f"registry.heroku.com/{name}/web"
    run("docker", "tag", image, target)
    run("docker", "push", target)
    run("heroku", "container:release", "web", "--app", name)
    run("heroku", "ps:scale", "web=1:eco", "--app", name)
    smoke(origin, revision)
    print(f"Preview: {origin}\nSource: {revision}\nNeon branch: {branch['id']}")
    if os.environ.get("GITHUB_OUTPUT"):
        with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
            output.write(f"url={origin}\n")


def retire(heroku, neon, cloudflare, name: str, branch_name: str):
    config = request(heroku, "GET", f"apps/{name}/config-vars", missing=True)
    if config is not None:
        if config.get("S3_BUCKET") not in {None, name}:
            raise ValueError("Preview bucket does not match the closed PR")
        formation = request(heroku, "GET", f"apps/{name}/formation")
        if any(process["type"] == "web" for process in formation):
            run("heroku", "ps:scale", "web=0", "--app", name)
    bucket = request(cloudflare, "GET", f"r2/buckets/{name}", missing=True)
    if bucket is not None:
        if config and config.get("AWS_SECRET_ACCESS_KEY"):
            s3 = boto3.client(
                "s3",
                endpoint_url=config["S3_ENDPOINT_URL"],
                region_name="auto",
                aws_access_key_id=config["AWS_ACCESS_KEY_ID"],
                aws_secret_access_key=config["AWS_SECRET_ACCESS_KEY"],
                config=Config(s3={"addressing_style": "path"}),
            )
            try:
                for page in s3.get_paginator("list_objects_v2").paginate(Bucket=name):
                    if page.get("Contents"):
                        result = s3.delete_objects(
                            Bucket=name,
                            Delete={"Objects": [{"Key": item["Key"]} for item in page["Contents"]]},
                        )
                        if result.get("Errors"):
                            raise RuntimeError("Preview object cleanup failed")
            finally:
                s3.close()
        # An interrupted bootstrap can leave an empty bucket without credentials.
        # The provider refuses deletion if it still contains objects.
        request(cloudflare, "DELETE", f"r2/buckets/{name}", missing=True)
    if config and config.get("AWS_ACCESS_KEY_ID"):
        request(cloudflare, "DELETE", f"tokens/{config['AWS_ACCESS_KEY_ID']}", missing=True)
    branch = find_branch(neon, branch_name)
    if branch:
        if branch["default"] or branch["protected"]:
            raise ValueError("Cannot retire a default or protected Neon branch")
        wait_operations(neon, request(neon, "DELETE", f"branches/{branch['id']}"))
    request(heroku, "DELETE", f"apps/{name}", missing=True)
    print(f"Retired {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("deploy", "retire"))
    parser.add_argument("--pull-number", type=int, required=True)
    parser.add_argument("--source-sha")
    parser.add_argument("--image")
    args = parser.parse_args()
    if args.pull_number < 1:
        parser.error("A positive PR number is required")
    if args.operation == "deploy" and (
        not args.image or not re.fullmatch(r"[a-f0-9]{40}", args.source_sha or "")
    ):
        parser.error("Deployment requires an image and exact source SHA")
    name, branch = f"inkcre-ext-reg-pr-{args.pull_number}", f"preview/ext-reg/pr-{args.pull_number}"
    with (
        httpx.Client(
            base_url="https://api.heroku.com/",
            timeout=60,
            headers={
                "Authorization": f"Bearer {os.environ['HEROKU_API_KEY']}",
                "Accept": "application/vnd.heroku+json; version=3",
            },
        ) as heroku,
        httpx.Client(
            base_url=f"https://console.neon.tech/api/v2/projects/{os.environ['NEON_PROJECT_ID']}/",
            timeout=60,
            headers={"Authorization": f"Bearer {os.environ['NEON_API_KEY']}"},
        ) as neon,
        httpx.Client(
            base_url=f"https://api.cloudflare.com/client/v4/accounts/{os.environ['CLOUDFLARE_ACCOUNT_ID']}/",
            timeout=60,
            headers={"Authorization": f"Bearer {os.environ['CLOUDFLARE_PREVIEW_API_TOKEN']}"},
        ) as cloudflare,
    ):
        if args.operation == "deploy":
            deploy(heroku, neon, cloudflare, name, branch, args.image, args.source_sha)
        else:
            retire(heroku, neon, cloudflare, name, branch)


if __name__ == "__main__":
    main()
