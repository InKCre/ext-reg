"""Import a read-only D1 SQLite snapshot into an empty migrated PostgreSQL database."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

from tortoise.context import TortoiseContext
from tortoise.transactions import in_transaction

from .service import database as db
from .service.settings import database_config

MODELS = (
    db.Namespace,
    db.Credential,
    db.Extension,
    db.Release,
    db.PythonDistribution,
    db.ModuleFederationDistribution,
    db.PythonFile,
)


def normalized(row: dict) -> dict:
    result = {}
    for key, value in row.items():
        if key.endswith("_json"):
            key, value = key.removesuffix("_json"), json.loads(value) if value else None
        if key.endswith("_at") and value is not None:
            date = datetime.fromisoformat(value) if isinstance(value, str) else value
            value = date.replace(tzinfo=date.tzinfo or UTC).astimezone(UTC).isoformat()
        if key == "disabled":
            value = bool(value)
        result[key] = value
    return result


def read_source(path: Path) -> dict[str, list[dict]]:
    with sqlite3.connect(f"file:{quote(str(path.resolve()))}?mode=ro", uri=True) as source:
        source.row_factory = sqlite3.Row
        if source.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("SQLite snapshot integrity check failed")
        if source.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("SQLite snapshot has broken references")
        # Table names are fixed model metadata, never user input. SQL exists only
        # at this legacy export boundary; all PostgreSQL reads/writes use ORM.
        return {
            model._meta.db_table: [
                normalized(dict(row))
                for row in source.execute(f'SELECT * FROM "{model._meta.db_table}"')
            ]
            for model in MODELS
        }


def fingerprints(data: dict[str, list[dict]]) -> dict:
    return {
        table: {
            "rows": len(rows),
            "sha256": hashlib.sha256(
                json.dumps(
                    sorted(json.dumps(row, sort_keys=True, ensure_ascii=False) for row in rows),
                    ensure_ascii=False,
                ).encode()
            ).hexdigest(),
        }
        for table, rows in data.items()
    }


async def target_snapshot() -> dict[str, list[dict]]:
    data = {model._meta.db_table: await model.all().values() for model in MODELS}
    releases = {row["id"]: (row["extension_id"], row["version"]) for row in data["releases"]}
    projects = {
        row["id"]: (row["normalized_project"], row["project_version"])
        for row in data["python_distributions"]
    }
    for table, rows in data.items():
        for row in rows:
            if "namespace_id" in row:
                row["namespace"] = row.pop("namespace_id")
            if table == "releases":
                row.pop("id")
                row["extension_name"] = row.pop("extension_id")
            if "release_id" in row:
                row.pop("id")
                row["extension_name"], row["release_version"] = releases[row.pop("release_id")]
            if table == "python_files":
                row.pop("id")
                row["normalized_project"], row["project_version"] = projects[
                    row.pop("distribution_id")
                ]
        data[table] = [normalized(row) for row in rows]
    return data


async def import_snapshot(source: dict[str, list[dict]]) -> dict:
    expected = fingerprints(source)
    async with in_transaction():
        for model in MODELS:
            if await model.exists():
                raise ValueError(
                    "Import requires an empty target; it never merges or overwrites data"
                )
        releases, projects = {}, {}
        for model in MODELS:
            for record in source[model._meta.db_table]:
                values = record.copy()
                if "namespace" in values:
                    values["namespace_id"] = values.pop("namespace")
                if model is db.Release:
                    values["extension_id"] = values.pop("extension_name")
                elif "extension_name" in values:
                    values["release_id"] = releases[
                        values.pop("extension_name"), values.pop("release_version")
                    ]
                if model is db.PythonFile:
                    values["distribution_id"] = projects[
                        values.pop("normalized_project"), values.pop("project_version")
                    ]
                row = await model.create(**values)
                if model is db.Release:
                    releases[record["extension_name"], record["version"]] = row.pk
                elif model is db.PythonDistribution:
                    projects[record["normalized_project"], record["project_version"]] = row.pk
        actual = fingerprints(await target_snapshot())
        if actual != expected:
            raise ValueError("Imported content differs from source; transaction rolled back")
    return actual


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    source = read_source(args.snapshot)
    url = os.environ.get("MIGRATION_DATABASE_URL") or os.environ["DATABASE_URL"]
    async with TortoiseContext() as context:
        await context.init(config=database_config(url))
        if args.verify_only:
            report = fingerprints(await target_snapshot())
            if report != fingerprints(source):
                raise ValueError("Target differs from the source snapshot")
        else:
            report = await import_snapshot(source)
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
