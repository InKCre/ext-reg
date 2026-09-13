"""Deploy a verified image to an already provisioned production app and database."""

import argparse
import os

import httpx
from registry_preview import request, run, smoke


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    app = os.environ["HEROKU_APP_NAME"]
    origin = "https://registry.inkcre.dev"
    with httpx.Client(
        base_url="https://api.heroku.com/",
        timeout=60,
        headers={
            "Authorization": f"Bearer {os.environ['HEROKU_API_KEY']}",
            "Accept": "application/vnd.heroku+json; version=3",
        },
    ) as heroku:
        existing = request(heroku, "GET", f"apps/{app}")
        if existing["stack"]["name"] != "container":
            raise ValueError("Production app must already use the container stack")
        run(
            "docker",
            "run",
            "--rm",
            "--env",
            "DATABASE_URL",
            args.image,
            "tortoise",
            "-c",
            "inkcre_extension_registry.migration_config.TORTOISE_ORM",
            "upgrade",
        )
        config = {
            key: os.environ[key]
            for key in (
                "DATABASE_URL",
                "S3_ENDPOINT_URL",
                "S3_BUCKET",
                "AWS_ACCESS_KEY_ID",
                "AWS_SECRET_ACCESS_KEY",
            )
        }
        config.update(PUBLIC_ORIGIN=origin, REGISTRY_SOURCE_REVISION=None)
        request(heroku, "PATCH", f"apps/{app}/config-vars", json=config)
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
        run("docker", "tag", args.image, target)
        run("docker", "push", target)
        run("heroku", "container:release", "web", "--app", app)
        run("heroku", "ps:scale", "web=1:basic", "--app", app)
        # This origin proves the new app before an independently authorized DNS cutover.
        smoke(existing["web_url"].rstrip("/"), os.environ["SOURCE_SHA"])
        print(f"Production app released: {app}; canonical origin: {origin}")


if __name__ == "__main__":
    main()
