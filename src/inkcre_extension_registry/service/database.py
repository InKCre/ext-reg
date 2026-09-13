"""PostgreSQL models. Checked-in Tortoise migrations own schema changes."""

from typing import ClassVar

from tortoise import fields
from tortoise.migrations.constraints import CheckConstraint
from tortoise.models import Model


class Namespace(Model):
    name = fields.CharField(max_length=64, primary_key=True)
    status = fields.CharField(max_length=16, default="active")
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta(Model.Meta):
        table = "namespaces"
        constraints: ClassVar = [
            CheckConstraint("status IN ('active', 'blocked')", "namespace_status")
        ]


class Credential(Model):
    token_hash = fields.CharField(max_length=64, primary_key=True)
    namespace: fields.ForeignKeyRelation[Namespace] = fields.ForeignKeyField(
        "models.Namespace", on_delete=fields.RESTRICT
    )
    label = fields.TextField()
    disabled = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta(Model.Meta):
        table = "credentials"
        constraints: ClassVar = [
            CheckConstraint("token_hash ~ '^[0-9a-f]{64}$'", "credential_hash")
        ]


class Extension(Model):
    name = fields.CharField(max_length=129, primary_key=True)
    namespace: fields.ForeignKeyRelation[Namespace] = fields.ForeignKeyField(
        "models.Namespace", on_delete=fields.RESTRICT
    )
    nickname = fields.TextField()
    publisher_metadata = fields.JSONField(default=dict)
    created_at = fields.DatetimeField(auto_now_add=True)
    releases: fields.ReverseRelation["Release"]

    class Meta(Model.Meta):
        table = "extensions"
        constraints: ClassVar = [
            CheckConstraint("name ~ '^[^/]+/[^/]+$'", "extension_name"),
            CheckConstraint(
                "jsonb_typeof(publisher_metadata) = 'object'", "publisher_metadata_object"
            ),
        ]


class Release(Model):
    id = fields.BigIntField(primary_key=True)
    extension: fields.ForeignKeyRelation[Extension] = fields.ForeignKeyField(
        "models.Extension",
        related_name="releases",
        on_delete=fields.RESTRICT,
    )
    version = fields.CharField(max_length=128)
    state = fields.CharField(max_length=16, default="preparing")
    yank_reason: str | None = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    published_at = fields.DatetimeField(null=True)
    updated_at = fields.DatetimeField(auto_now_add=True)
    python: fields.BackwardOneToOneRelation["PythonDistribution"] | None
    module_federation: fields.BackwardOneToOneRelation["ModuleFederationDistribution"] | None

    class Meta(Model.Meta):
        table = "releases"
        unique_together = (("extension_id", "version"),)
        indexes = (("extension_id", "state", "created_at"),)
        constraints: ClassVar = [
            CheckConstraint(
                "state IN ('preparing', 'published', 'yanked', 'blocked')", "release_state"
            )
        ]


class PythonDistribution(Model):
    id = fields.BigIntField(primary_key=True)
    release: fields.OneToOneRelation[Release] = fields.OneToOneField(
        "models.Release", related_name="python", on_delete=fields.RESTRICT
    )
    normalized_project = fields.CharField(max_length=256)
    project_version = fields.CharField(max_length=256)
    host_sdk = fields.CharField(max_length=32)
    host_sdk_range = fields.TextField()
    entry_group = fields.TextField()
    entry_name = fields.TextField()
    entry_object = fields.TextField()
    source_repository = fields.TextField()
    source_revision = fields.TextField()
    build_id = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    files: fields.ReverseRelation["PythonFile"]

    class Meta(Model.Meta):
        table = "python_distributions"
        unique_together = (("normalized_project", "project_version"),)
        constraints: ClassVar = [CheckConstraint("host_sdk = 'core-py'", "python_host_sdk")]


class PythonFile(Model):
    id = fields.BigIntField(primary_key=True)
    distribution: fields.ForeignKeyRelation[PythonDistribution] = fields.ForeignKeyField(
        "models.PythonDistribution", related_name="files", on_delete=fields.RESTRICT
    )
    filename = fields.TextField()
    sha256 = fields.CharField(max_length=64)
    size = fields.IntField()
    filetype = fields.CharField(max_length=32)
    requires_python = fields.TextField(null=True)
    core_metadata_sha256 = fields.CharField(max_length=64)
    r2_key = fields.CharField(max_length=1024, unique=True)
    metadata_r2_key = fields.CharField(max_length=1024, unique=True)
    uploaded_at = fields.DatetimeField(auto_now_add=True)

    class Meta(Model.Meta):
        table = "python_files"
        unique_together = (("distribution_id", "filename"),)
        constraints: ClassVar = [
            CheckConstraint(
                "position('/' in filename) = 0 AND position(chr(92) in filename) = 0",
                "python_filename",
            ),
            CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", "python_sha256"),
            CheckConstraint("size BETWEEN 0 AND 20971520", "python_size"),
            CheckConstraint("filetype = 'bdist_wheel'", "python_filetype"),
            CheckConstraint("core_metadata_sha256 ~ '^[0-9a-f]{64}$'", "python_metadata_sha256"),
        ]


class ModuleFederationDistribution(Model):
    id = fields.BigIntField(primary_key=True)
    release: fields.OneToOneRelation[Release] = fields.OneToOneField(
        "models.Release",
        related_name="module_federation",
        on_delete=fields.RESTRICT,
    )
    host_sdk = fields.CharField(max_length=32)
    host_sdk_range = fields.TextField()
    source_repository = fields.TextField()
    source_revision = fields.TextField()
    build_id = fields.TextField(null=True)
    manifest_r2_key = fields.TextField(null=True)
    asset_paths = fields.JSONField(null=True)
    internal_snapshot_hash = fields.CharField(max_length=64, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    uploaded_at = fields.DatetimeField(null=True)

    class Meta(Model.Meta):
        table = "module_federation_distributions"
        constraints: ClassVar = [
            CheckConstraint("host_sdk = '@inkcre/core'", "mf_host_sdk"),
            CheckConstraint(
                "asset_paths IS NULL OR jsonb_typeof(asset_paths) = 'array'", "mf_asset_paths"
            ),
            CheckConstraint(
                "internal_snapshot_hash IS NULL OR internal_snapshot_hash ~ '^[0-9a-f]{64}$'",
                "mf_snapshot_hash",
            ),
            CheckConstraint(
                "(manifest_r2_key IS NULL AND asset_paths IS NULL "
                "AND internal_snapshot_hash IS NULL AND uploaded_at IS NULL) OR "
                "(manifest_r2_key IS NOT NULL AND asset_paths IS NOT NULL "
                "AND internal_snapshot_hash IS NOT NULL AND uploaded_at IS NOT NULL)",
                "mf_complete_snapshot",
            ),
        ]
