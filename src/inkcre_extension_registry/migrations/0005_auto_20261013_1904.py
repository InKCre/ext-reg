from tortoise import fields, migrations
from tortoise.fields.base import OnDelete
from tortoise.indexes import Index
from tortoise.migrations import operations as ops
from tortoise.migrations.constraints import CheckConstraint


class Migration(migrations.Migration):
    dependencies = [("models", "0004_documentation_ownership")]

    initial = False

    operations = [
        ops.AddField(
            model_name="Release",
            name="visible_distributions",
            field=fields.JSONField(default=list, null=True),
        ),
        ops.CreateModel(
            name="NativeRelease",
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
                        related_name="native_releases",
                        on_delete=OnDelete.RESTRICT,
                    ),
                ),
                ("distribution", fields.CharField(max_length=32)),
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
                "table": "native_releases",
                "app": "models",
                "unique_together": (("extension_id", "distribution", "version"),),
                "constraints": [
                    CheckConstraint(
                        check="distribution IN ('python', 'module_federation')",
                        name="native_distribution",
                    ),
                    CheckConstraint(
                        check="state IN ('preparing', 'published', 'yanked', 'blocked')",
                        name="native_release_state",
                    ),
                ],
                "indexes": [Index(fields=["extension_id", "distribution", "state", "created_at"])],
                "pk_attr": "id",
            },
            bases=["Model"],
        ),
        ops.AddField(
            model_name="PythonDistribution",
            name="legacy_release",
            field=fields.OneToOneField(
                "models.Release",
                source_field="legacy_release_id",
                to_field="id",
                related_name=False,
                null=True,
                on_delete=OnDelete.RESTRICT,
            ),
        ),
        ops.RunSQL("UPDATE python_distributions SET legacy_release_id=release_id"),
        ops.RemoveField(model_name="PythonDistribution", name="release"),
        ops.AlterField(
            model_name="PythonDistribution",
            name="legacy_release",
            field=fields.OneToOneField(
                "models.Release",
                source_field="legacy_release_id",
                to_field="id",
                related_name="python",
                null=True,
                on_delete=OnDelete.RESTRICT,
            ),
        ),
        ops.AddField(
            model_name="PythonDistribution",
            name="release",
            field=fields.OneToOneField(
                "models.NativeRelease",
                source_field="release_id",
                to_field="id",
                related_name="python",
                null=True,
                on_delete=OnDelete.RESTRICT,
            ),
        ),
        ops.RunSQL("""
            INSERT INTO native_releases (extension_id,distribution,version,state,yank_reason,created_at,published_at,updated_at)
            SELECT r.extension_id,'python',r.version,
                   CASE WHEN r.state IN ('published','yanked') AND NOT (EXISTS (SELECT 1 FROM python_files f WHERE f.distribution_id=d.id)) THEN 'preparing' ELSE r.state END,
                   r.yank_reason,r.created_at,r.published_at,r.updated_at
            FROM python_distributions d JOIN releases r ON r.id=d.legacy_release_id;
            UPDATE python_distributions d SET release_id=n.id
            FROM releases r,native_releases n
            WHERE r.id=d.legacy_release_id AND n.extension_id=r.extension_id
              AND n.version=r.version AND n.distribution='python';
        """),
        ops.AlterField(
            model_name="PythonDistribution",
            name="release",
            field=fields.OneToOneField(
                "models.NativeRelease",
                source_field="release_id",
                to_field="id",
                related_name="python",
                on_delete=OnDelete.RESTRICT,
            ),
        ),
        ops.AddField(
            model_name="ModuleFederationDistribution",
            name="legacy_release",
            field=fields.OneToOneField(
                "models.Release",
                source_field="legacy_release_id",
                to_field="id",
                related_name=False,
                null=True,
                on_delete=OnDelete.RESTRICT,
            ),
        ),
        ops.RunSQL("UPDATE module_federation_distributions SET legacy_release_id=release_id"),
        ops.RemoveField(model_name="ModuleFederationDistribution", name="release"),
        ops.AlterField(
            model_name="ModuleFederationDistribution",
            name="legacy_release",
            field=fields.OneToOneField(
                "models.Release",
                source_field="legacy_release_id",
                to_field="id",
                related_name="module_federation",
                null=True,
                on_delete=OnDelete.RESTRICT,
            ),
        ),
        ops.AddField(
            model_name="ModuleFederationDistribution",
            name="release",
            field=fields.OneToOneField(
                "models.NativeRelease",
                source_field="release_id",
                to_field="id",
                related_name="module_federation",
                null=True,
                on_delete=OnDelete.RESTRICT,
            ),
        ),
        ops.RunSQL("""
            INSERT INTO native_releases (extension_id,distribution,version,state,yank_reason,created_at,published_at,updated_at)
            SELECT r.extension_id,'module_federation',r.version,
                   CASE WHEN r.state IN ('published','yanked') AND NOT (d.manifest_r2_key IS NOT NULL) THEN 'preparing' ELSE r.state END,
                   r.yank_reason,r.created_at,r.published_at,r.updated_at
            FROM module_federation_distributions d JOIN releases r ON r.id=d.legacy_release_id;
            UPDATE module_federation_distributions d SET release_id=n.id
            FROM releases r,native_releases n
            WHERE r.id=d.legacy_release_id AND n.extension_id=r.extension_id
              AND n.version=r.version AND n.distribution='module_federation';
        """),
        ops.AlterField(
            model_name="ModuleFederationDistribution",
            name="release",
            field=fields.OneToOneField(
                "models.NativeRelease",
                source_field="release_id",
                to_field="id",
                related_name="module_federation",
                on_delete=OnDelete.RESTRICT,
            ),
        ),
        ops.RunSQL("""UPDATE releases r SET visible_distributions =
          (CASE WHEN EXISTS (SELECT 1 FROM python_distributions p JOIN python_files f ON f.distribution_id=p.id WHERE p.legacy_release_id=r.id) THEN '["python"]'::jsonb ELSE '[]'::jsonb END) ||
          (CASE WHEN EXISTS (SELECT 1 FROM module_federation_distributions m WHERE m.legacy_release_id=r.id AND m.manifest_r2_key IS NOT NULL) THEN '["module_federation"]'::jsonb ELSE '[]'::jsonb END)
        """),
        ops.AlterField(
            model_name="Release", name="visible_distributions", field=fields.JSONField(default=list)
        ),
        ops.RunSQL(
            "GRANT SELECT, INSERT, UPDATE, DELETE ON native_releases TO registry_app; GRANT USAGE ON SEQUENCE native_releases_id_seq TO registry_app;"
        ),
    ]
