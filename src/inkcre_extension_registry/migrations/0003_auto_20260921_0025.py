import functools
from json import dumps, loads

from tortoise import fields, migrations
from tortoise.fields.base import OnDelete
from tortoise.migrations import operations as ops
from tortoise.migrations.constraints import CheckConstraint


class Migration(migrations.Migration):
    dependencies = [("models", "0002_runtime_access")]

    initial = False

    operations = [
        ops.CreateModel(
            name="DocumentationSnapshot",
            fields=[
                (
                    "id",
                    fields.CharField(primary_key=True, unique=True, db_index=True, max_length=32),
                ),
                (
                    "release",
                    fields.ForeignKeyField(
                        "models.Release",
                        source_field="release_id",
                        db_constraint=True,
                        to_field="id",
                        on_delete=OnDelete.RESTRICT,
                    ),
                ),
                ("scope", fields.CharField(max_length=32)),
                ("content_sha256", fields.CharField(max_length=64)),
                ("entry", fields.TextField(unique=False)),
                ("source_repository", fields.TextField(unique=False)),
                ("source_revision", fields.TextField(unique=False)),
                ("build_id", fields.TextField(null=True, unique=False)),
                (
                    "files",
                    fields.JSONField(
                        encoder=functools.partial(dumps, separators=(",", ":")), decoder=loads
                    ),
                ),
                ("etag", fields.CharField(max_length=64)),
                ("created_at", fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={
                "table": "documentation_snapshots",
                "app": "models",
                "constraints": [
                    CheckConstraint(check="id ~ '^[0-9a-f]{32}$'", name="docs_snapshot_id"),
                    CheckConstraint(
                        check="scope IN ('global', 'python', 'module-federation')",
                        name="docs_snapshot_scope",
                    ),
                    CheckConstraint(
                        check="content_sha256 ~ '^[0-9a-f]{64}$' AND etag ~ '^[0-9a-f]{64}$'",
                        name="docs_snapshot_hash",
                    ),
                    CheckConstraint(
                        check="jsonb_typeof(files) = 'object'", name="docs_snapshot_files"
                    ),
                ],
                "pk_attr": "id",
            },
            bases=["Model"],
        ),
        ops.CreateModel(
            name="DocumentationSet",
            fields=[
                (
                    "id",
                    fields.BigIntField(
                        generated=True, primary_key=True, unique=True, db_index=True
                    ),
                ),
                (
                    "release",
                    fields.ForeignKeyField(
                        "models.Release",
                        source_field="release_id",
                        db_constraint=True,
                        to_field="id",
                        on_delete=OnDelete.RESTRICT,
                    ),
                ),
                ("scope", fields.CharField(max_length=32)),
                (
                    "snapshot",
                    fields.ForeignKeyField(
                        "models.DocumentationSnapshot",
                        source_field="snapshot_id",
                        db_constraint=True,
                        to_field="id",
                        on_delete=OnDelete.RESTRICT,
                    ),
                ),
                ("updated_at", fields.DatetimeField(auto_now=True, auto_now_add=False)),
            ],
            options={
                "table": "documentation_sets",
                "app": "models",
                "unique_together": (("release_id", "scope"),),
                "constraints": [
                    CheckConstraint(
                        check="scope IN ('global', 'python', 'module-federation')",
                        name="docs_set_scope",
                    )
                ],
                "pk_attr": "id",
            },
            bases=["Model"],
        ),
        ops.AddConstraint(
            model_name="DocumentationSnapshot",
            constraint=CheckConstraint("id ~ '^[0-9a-f]{32}$'", "docs_snapshot_id"),
        ),
        ops.AddConstraint(
            model_name="DocumentationSnapshot",
            constraint=CheckConstraint(
                "scope IN ('global', 'python', 'module-federation')", "docs_snapshot_scope"
            ),
        ),
        ops.AddConstraint(
            model_name="DocumentationSnapshot",
            constraint=CheckConstraint(
                "content_sha256 ~ '^[0-9a-f]{64}$' AND etag ~ '^[0-9a-f]{64}$'",
                "docs_snapshot_hash",
            ),
        ),
        ops.AddConstraint(
            model_name="DocumentationSnapshot",
            constraint=CheckConstraint("jsonb_typeof(files) = 'object'", "docs_snapshot_files"),
        ),
        ops.AddConstraint(
            model_name="DocumentationSet",
            constraint=CheckConstraint(
                "scope IN ('global', 'python', 'module-federation')", "docs_set_scope"
            ),
        ),
        ops.RunSQL(
            "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE documentation_snapshots, documentation_sets TO registry_app"
        ),
        ops.RunSQL("GRANT USAGE ON SEQUENCE documentation_sets_id_seq TO registry_app"),
    ]
