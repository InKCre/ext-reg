# Tortoise 1.1 CreateModel does not emit Meta.constraints. Apply them with
# native AddConstraint operations so initial schemas enforce the same model rules.
import functools
from json import dumps, loads

from tortoise import fields, migrations
from tortoise.fields.base import OnDelete
from tortoise.indexes import Index
from tortoise.migrations import operations as ops
from tortoise.migrations.constraints import CheckConstraint


class Migration(migrations.Migration):
    initial = True

    operations = [
        ops.CreateModel(
            name="Namespace",
            fields=[
                (
                    "name",
                    fields.CharField(primary_key=True, unique=True, db_index=True, max_length=64),
                ),
                ("status", fields.CharField(default="active", max_length=16)),
                ("created_at", fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={"table": "namespaces", "app": "models", "pk_attr": "name"},
            bases=["Model"],
        ),
        ops.CreateModel(
            name="Credential",
            fields=[
                (
                    "token_hash",
                    fields.CharField(primary_key=True, unique=True, db_index=True, max_length=64),
                ),
                (
                    "namespace",
                    fields.ForeignKeyField(
                        "models.Namespace",
                        source_field="namespace_id",
                        db_constraint=True,
                        to_field="name",
                        on_delete=OnDelete.RESTRICT,
                    ),
                ),
                ("label", fields.TextField(unique=False)),
                ("disabled", fields.BooleanField(default=False)),
                ("created_at", fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={"table": "credentials", "app": "models", "pk_attr": "token_hash"},
            bases=["Model"],
        ),
        ops.CreateModel(
            name="Extension",
            fields=[
                (
                    "name",
                    fields.CharField(primary_key=True, unique=True, db_index=True, max_length=129),
                ),
                (
                    "namespace",
                    fields.ForeignKeyField(
                        "models.Namespace",
                        source_field="namespace_id",
                        db_constraint=True,
                        to_field="name",
                        on_delete=OnDelete.RESTRICT,
                    ),
                ),
                ("nickname", fields.TextField(unique=False)),
                (
                    "publisher_metadata",
                    fields.JSONField(
                        default=dict,
                        encoder=functools.partial(dumps, separators=(",", ":")),
                        decoder=loads,
                    ),
                ),
                ("created_at", fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={"table": "extensions", "app": "models", "pk_attr": "name"},
            bases=["Model"],
        ),
        ops.CreateModel(
            name="Release",
            fields=[
                (
                    "id",
                    fields.BigIntField(
                        generated=True, primary_key=True, unique=True, db_index=True
                    ),
                ),
                (
                    "extension",
                    fields.ForeignKeyField(
                        "models.Extension",
                        source_field="extension_id",
                        db_constraint=True,
                        to_field="name",
                        related_name="releases",
                        on_delete=OnDelete.RESTRICT,
                    ),
                ),
                ("version", fields.CharField(max_length=128)),
                ("state", fields.CharField(default="preparing", max_length=16)),
                ("yank_reason", fields.TextField(null=True, unique=False)),
                ("created_at", fields.DatetimeField(auto_now=False, auto_now_add=True)),
                (
                    "published_at",
                    fields.DatetimeField(null=True, auto_now=False, auto_now_add=False),
                ),
                ("updated_at", fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={
                "table": "releases",
                "app": "models",
                "unique_together": (("extension_id", "version"),),
                "indexes": [Index(fields=["extension_id", "state", "created_at"])],
                "pk_attr": "id",
            },
            bases=["Model"],
        ),
        ops.CreateModel(
            name="ModuleFederationDistribution",
            fields=[
                (
                    "id",
                    fields.BigIntField(
                        generated=True, primary_key=True, unique=True, db_index=True
                    ),
                ),
                (
                    "release",
                    fields.OneToOneField(
                        "models.Release",
                        source_field="release_id",
                        db_constraint=True,
                        to_field="id",
                        related_name="module_federation",
                        on_delete=OnDelete.RESTRICT,
                    ),
                ),
                ("host_sdk", fields.CharField(max_length=32)),
                ("host_sdk_range", fields.TextField(unique=False)),
                ("source_repository", fields.TextField(unique=False)),
                ("source_revision", fields.TextField(unique=False)),
                ("build_id", fields.TextField(null=True, unique=False)),
                ("manifest_r2_key", fields.TextField(null=True, unique=False)),
                (
                    "asset_paths",
                    fields.JSONField(
                        null=True,
                        encoder=functools.partial(dumps, separators=(",", ":")),
                        decoder=loads,
                    ),
                ),
                ("internal_snapshot_hash", fields.CharField(null=True, max_length=64)),
                ("created_at", fields.DatetimeField(auto_now=False, auto_now_add=True)),
                (
                    "uploaded_at",
                    fields.DatetimeField(null=True, auto_now=False, auto_now_add=False),
                ),
            ],
            options={"table": "module_federation_distributions", "app": "models", "pk_attr": "id"},
            bases=["Model"],
        ),
        ops.CreateModel(
            name="PythonDistribution",
            fields=[
                (
                    "id",
                    fields.BigIntField(
                        generated=True, primary_key=True, unique=True, db_index=True
                    ),
                ),
                (
                    "release",
                    fields.OneToOneField(
                        "models.Release",
                        source_field="release_id",
                        db_constraint=True,
                        to_field="id",
                        related_name="python",
                        on_delete=OnDelete.RESTRICT,
                    ),
                ),
                ("normalized_project", fields.CharField(max_length=256)),
                ("project_version", fields.CharField(max_length=256)),
                ("host_sdk", fields.CharField(max_length=32)),
                ("host_sdk_range", fields.TextField(unique=False)),
                ("entry_group", fields.TextField(unique=False)),
                ("entry_name", fields.TextField(unique=False)),
                ("entry_object", fields.TextField(unique=False)),
                ("source_repository", fields.TextField(unique=False)),
                ("source_revision", fields.TextField(unique=False)),
                ("build_id", fields.TextField(null=True, unique=False)),
                ("created_at", fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={
                "table": "python_distributions",
                "app": "models",
                "unique_together": (("normalized_project", "project_version"),),
                "pk_attr": "id",
            },
            bases=["Model"],
        ),
        ops.CreateModel(
            name="PythonFile",
            fields=[
                (
                    "id",
                    fields.BigIntField(
                        generated=True, primary_key=True, unique=True, db_index=True
                    ),
                ),
                (
                    "distribution",
                    fields.ForeignKeyField(
                        "models.PythonDistribution",
                        source_field="distribution_id",
                        db_constraint=True,
                        to_field="id",
                        related_name="files",
                        on_delete=OnDelete.RESTRICT,
                    ),
                ),
                ("filename", fields.TextField(unique=False)),
                ("sha256", fields.CharField(max_length=64)),
                ("size", fields.IntField()),
                ("filetype", fields.CharField(max_length=32)),
                ("requires_python", fields.TextField(null=True, unique=False)),
                ("core_metadata_sha256", fields.CharField(max_length=64)),
                ("r2_key", fields.CharField(unique=True, max_length=1024)),
                ("metadata_r2_key", fields.CharField(unique=True, max_length=1024)),
                ("uploaded_at", fields.DatetimeField(auto_now=False, auto_now_add=True)),
            ],
            options={
                "table": "python_files",
                "app": "models",
                "unique_together": (("distribution_id", "filename"),),
                "pk_attr": "id",
            },
            bases=["Model"],
        ),
        ops.AddConstraint(
            model_name="Namespace",
            constraint=CheckConstraint(
                check="status IN ('active', 'blocked')", name="namespace_status"
            ),
        ),
        ops.AddConstraint(
            model_name="Credential",
            constraint=CheckConstraint(
                check="token_hash ~ '^[0-9a-f]{64}$'", name="credential_hash"
            ),
        ),
        ops.AddConstraint(
            model_name="Extension",
            constraint=CheckConstraint(check="name ~ '^[^/]+/[^/]+$'", name="extension_name"),
        ),
        ops.AddConstraint(
            model_name="Extension",
            constraint=CheckConstraint(
                check="jsonb_typeof(publisher_metadata) = 'object'",
                name="publisher_metadata_object",
            ),
        ),
        ops.AddConstraint(
            model_name="Release",
            constraint=CheckConstraint(
                check="state IN ('preparing', 'published', 'yanked', 'blocked')",
                name="release_state",
            ),
        ),
        ops.AddConstraint(
            model_name="ModuleFederationDistribution",
            constraint=CheckConstraint(check="host_sdk = '@inkcre/core'", name="mf_host_sdk"),
        ),
        ops.AddConstraint(
            model_name="ModuleFederationDistribution",
            constraint=CheckConstraint(
                check="asset_paths IS NULL OR jsonb_typeof(asset_paths) = 'array'",
                name="mf_asset_paths",
            ),
        ),
        ops.AddConstraint(
            model_name="ModuleFederationDistribution",
            constraint=CheckConstraint(
                check="internal_snapshot_hash IS NULL OR internal_snapshot_hash ~ '^[0-9a-f]{64}$'",
                name="mf_snapshot_hash",
            ),
        ),
        ops.AddConstraint(
            model_name="ModuleFederationDistribution",
            constraint=CheckConstraint(
                check="(manifest_r2_key IS NULL AND asset_paths IS NULL AND internal_snapshot_hash IS NULL AND uploaded_at IS NULL) OR (manifest_r2_key IS NOT NULL AND asset_paths IS NOT NULL AND internal_snapshot_hash IS NOT NULL AND uploaded_at IS NOT NULL)",
                name="mf_complete_snapshot",
            ),
        ),
        ops.AddConstraint(
            model_name="PythonDistribution",
            constraint=CheckConstraint(check="host_sdk = 'core-py'", name="python_host_sdk"),
        ),
        ops.AddConstraint(
            model_name="PythonFile",
            constraint=CheckConstraint(
                check="position('/' in filename) = 0 AND position(chr(92) in filename) = 0",
                name="python_filename",
            ),
        ),
        ops.AddConstraint(
            model_name="PythonFile",
            constraint=CheckConstraint(check="sha256 ~ '^[0-9a-f]{64}$'", name="python_sha256"),
        ),
        ops.AddConstraint(
            model_name="PythonFile",
            constraint=CheckConstraint(check="size BETWEEN 0 AND 20971520", name="python_size"),
        ),
        ops.AddConstraint(
            model_name="PythonFile",
            constraint=CheckConstraint(check="filetype = 'bdist_wheel'", name="python_filetype"),
        ),
        ops.AddConstraint(
            model_name="PythonFile",
            constraint=CheckConstraint(
                check="core_metadata_sha256 ~ '^[0-9a-f]{64}$'", name="python_metadata_sha256"
            ),
        ),
    ]
