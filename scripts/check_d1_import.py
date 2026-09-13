"""Verify the legacy schema conversion in the existing disposable database check."""

import copy
import sqlite3
import tempfile
from pathlib import Path

from tortoise.exceptions import IntegrityError

from inkcre_extension_registry.import_d1 import (
    fingerprints,
    import_snapshot,
    read_source,
    target_snapshot,
)
from inkcre_extension_registry.service import database as db


async def check_import() -> None:
    date = "2026-01-02 03:04:05"
    with tempfile.TemporaryDirectory(prefix="registry-d1-import-") as directory:
        path = Path(directory) / "snapshot.sqlite"
        with sqlite3.connect(path) as source:
            source.executescript(
                (Path(__file__).resolve().parents[1] / "migrations/0001_registry.sql").read_text()
            )
            rows = {
                "namespaces": [{"name": "migration", "created_at": date}],
                "credentials": [
                    {
                        "token_hash": "a" * 64,
                        "namespace": "migration",
                        "label": "撤销 ' ? --",
                        "disabled": 1,
                        "created_at": date,
                    }
                ],
                "extensions": [
                    {
                        "name": "migration/extension",
                        "namespace": "migration",
                        "nickname": "迁移",
                        "publisher_metadata_json": '{"owner": "保留", "nested": {"a": [1, true]}}',
                        "created_at": date,
                    }
                ],
                "releases": [
                    {
                        "extension_name": "migration/extension",
                        "version": f"1.{i}.0",
                        "state": state,
                        "yank_reason": "保留撤回原因" if state == "yanked" else None,
                        "created_at": date,
                        "published_at": None if state == "preparing" else date,
                        "updated_at": date,
                    }
                    for i, state in enumerate(("preparing", "published", "yanked", "blocked"))
                ],
                "python_distributions": [
                    {
                        "extension_name": "migration/extension",
                        "release_version": "1.2.0",
                        "normalized_project": "migration-extension",
                        "project_version": "1.2.0",
                        "host_sdk": "core-py",
                        "host_sdk_range": "^1.0.0",
                        "entry_group": "extensions",
                        "entry_name": "migration",
                        "entry_object": "migration:Extension",
                        "source_repository": "https://example.invalid/repo",
                        "source_revision": "' ? --",
                        "build_id": None,
                        "created_at": date,
                    }
                ],
                "module_federation_distributions": [
                    {
                        "extension_name": "migration/extension",
                        "release_version": "1.2.0",
                        "host_sdk": "@inkcre/core",
                        "host_sdk_range": "^1.0.0",
                        "source_repository": "https://example.invalid/repo",
                        "source_revision": "abcdef",
                        "build_id": "build-1",
                        "manifest_r2_key": "unchanged/mf-manifest.json",
                        "asset_paths_json": '["mf-manifest.json", "assets/remoteEntry.js"]',
                        "internal_snapshot_hash": "b" * 64,
                        "created_at": date,
                        "uploaded_at": date,
                    }
                ],
                "python_files": [
                    {
                        "normalized_project": "migration-extension",
                        "project_version": "1.2.0",
                        "filename": "migration_extension-1.2.0-py3-none-any.whl",
                        "sha256": "c" * 64,
                        "size": 123,
                        "filetype": "bdist_wheel",
                        "requires_python": ">=3.12",
                        "core_metadata_sha256": "d" * 64,
                        "r2_key": "unchanged/wheel",
                        "metadata_r2_key": "unchanged/metadata",
                        "uploaded_at": date,
                    }
                ],
            }
            for table, records in rows.items():
                for row in records:
                    columns = ", ".join(row)
                    placeholders = ", ".join("?" for _ in row)
                    source.execute(
                        f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
                        tuple(row.values()),
                    )
        expected = read_source(path)
        invalid = copy.deepcopy(expected)
        invalid["python_files"][0]["size"] = -1
        try:
            await import_snapshot(invalid)
        except IntegrityError:
            pass
        else:
            raise AssertionError("Invalid file metadata must fail the import")
        assert not await db.Namespace.exists(), "Failed import left partial identities"
        assert await import_snapshot(expected) == fingerprints(expected)
        assert await db.Release.all().count() == 4
        assert (await db.Credential.get()).disabled
        assert (await db.PythonFile.get()).r2_key == "unchanged/wheel"
        try:
            await import_snapshot(expected)
        except ValueError as error:
            assert "empty target" in str(error)
        else:
            raise AssertionError("Import must refuse an occupied target")
        assert fingerprints(await target_snapshot()) == fingerprints(expected)
        print("D1 import preserved every field, reference, timestamp, credential and state.")
