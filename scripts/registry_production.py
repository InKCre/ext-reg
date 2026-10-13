"""Deploy a verified image to an already provisioned production app and database."""

import argparse
import os
from urllib.parse import unquote, urlsplit

import httpx
from registry_database import configure_runtime_login
from registry_preview import request, run, smoke


def require_stopped_web(heroku: httpx.Client, app: str) -> None:
    formation = request(heroku, "GET", f"apps/{app}/formation/web")
    if (
        formation["type"] != "web"
        or type(formation["quantity"]) is not int
        or formation["quantity"] != 0
    ):
        raise RuntimeError("Production web formation must be scaled to zero before deployment")
    dynos = request(heroku, "GET", f"apps/{app}/dynos", complete=True)
    if any(dyno["type"] == "web" and dyno["state"] not in {"down", "crashed"} for dyno in dynos):
        raise RuntimeError("Production web dynos have not stopped; deployment refused")


def deploy(heroku: httpx.Client, app: str, image: str, revision: str) -> None:
    owner_url = os.environ["MIGRATION_DATABASE_URL"]
    runtime = urlsplit(os.environ["DATABASE_URL"])
    if runtime.username != "registry_app" or not runtime.password:
        raise ValueError("Production DATABASE_URL must use registry_app")
    origin = "https://registry.inkcre.dev"
    phase = "stopped_web_check"
    print(f"production_deploy app={app} revision={revision} phase={phase} status=started")
    try:
        existing = request(heroku, "GET", f"apps/{app}")
        if existing["stack"]["name"] != "container":
            raise ValueError("Production app must already use the container stack")
        require_stopped_web(heroku, app)
        phase = "migration"
        print(f"production_deploy app={app} revision={revision} phase={phase} status=started")
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
        )
        phase = "runtime_config"
        print(f"production_deploy app={app} revision={revision} phase={phase} status=started")
        configure_runtime_login(owner_url, unquote(runtime.password))
        config = {
            key: os.environ[key]
            for key in (
                "DATABASE_URL",
                "S3_ENDPOINT_URL",
                "S3_BUCKET",
                "DOCUMENTATION_ORIGIN_TEMPLATE",
                "AWS_ACCESS_KEY_ID",
                "AWS_SECRET_ACCESS_KEY",
            )
        }
        config.update(
            PUBLIC_ORIGIN=origin,
            FORWARDED_ALLOW_IPS="*",
            REGISTRY_SOURCE_REVISION=None,
            MIGRATION_DATABASE_URL=None,
        )
        request(heroku, "PATCH", f"apps/{app}/config-vars", json=config)
        phase = "image_push"
        print(f"production_deploy app={app} revision={revision} phase={phase} status=started")
        run(
            "docker",
            "login",
            "--username",
            "_",
            "--password-stdin",
            "registry.heroku.com",
            input=os.environ["HEROKU_API_KEY"],
        )
        target = f"registry.heroku.com/{app}/web"
        run("docker", "tag", image, target)
        run("docker", "push", target)
        phase = "release"
        print(f"production_deploy app={app} revision={revision} phase={phase} status=started")
        run("heroku", "container:release", "web", "--app", app)
        phase = "start"
        print(f"production_deploy app={app} revision={revision} phase={phase} status=started")
        run("heroku", "ps:scale", "web=1:eco", "--app", app)
        phase = "smoke"
        print(f"production_deploy app={app} revision={revision} phase={phase} status=started")
        smoke(origin, revision)
        print(f"production_deploy app={app} revision={revision} phase=complete status=success")
    except Exception:
        print(f"production_deploy app={app} revision={revision} phase={phase} status=failed")
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    with httpx.Client(
        base_url="https://api.heroku.com/",
        timeout=60,
        headers={
            "Authorization": f"Bearer {os.environ['HEROKU_API_KEY']}",
            "Accept": "application/vnd.heroku+json; version=3",
        },
    ) as heroku:
        deploy(heroku, os.environ["HEROKU_APP_NAME"], args.image, os.environ["SOURCE_SHA"])


if __name__ == "__main__":
    main()
