from tortoise import fields, migrations
from tortoise.fields.base import OnDelete
from tortoise.migrations import operations as ops
from tortoise.migrations.constraints import CheckConstraint, UniqueConstraint


class Migration(migrations.Migration):
    dependencies = [("models", "0005_auto_20261013_1904")]

    initial = False

    operations = [
        ops.AlterField(
            model_name="DocumentationSet",
            name="release",
            field=fields.ForeignKeyField(
                "models.Release",
                source_field="release_id",
                null=True,
                db_constraint=True,
                to_field="id",
                on_delete=OnDelete.RESTRICT,
            ),
        ),
        ops.AddField(
            model_name="DocumentationSet",
            name="native_release",
            field=fields.ForeignKeyField(
                "models.NativeRelease",
                source_field="native_release_id",
                null=True,
                db_constraint=True,
                to_field="id",
                on_delete=OnDelete.RESTRICT,
            ),
        ),
        ops.AddConstraint(
            model_name="DocumentationSet",
            constraint=UniqueConstraint(fields=("native_release_id", "scope"), name=None),
        ),
        ops.AddConstraint(
            model_name="DocumentationSet",
            constraint=CheckConstraint(
                check="(release_id IS NULL) <> (native_release_id IS NULL)",
                name="docs_set_one_owner",
            ),
        ),
        ops.AlterField(
            model_name="DocumentationSnapshot",
            name="release",
            field=fields.ForeignKeyField(
                "models.Release",
                source_field="release_id",
                null=True,
                db_constraint=True,
                to_field="id",
                on_delete=OnDelete.RESTRICT,
            ),
        ),
        ops.AddField(
            model_name="DocumentationSnapshot",
            name="native_release",
            field=fields.ForeignKeyField(
                "models.NativeRelease",
                source_field="native_release_id",
                null=True,
                db_constraint=True,
                to_field="id",
                on_delete=OnDelete.RESTRICT,
            ),
        ),
        ops.AddConstraint(
            model_name="DocumentationSnapshot",
            constraint=UniqueConstraint(
                fields=("id", "native_release_id", "scope"), name="native_docs_snapshot_owner"
            ),
        ),
        ops.AddConstraint(
            model_name="DocumentationSnapshot",
            constraint=CheckConstraint(
                check="(release_id IS NULL) <> (native_release_id IS NULL)",
                name="docs_snapshot_one_owner",
            ),
        ),
        ops.RunSQL(
            "ALTER TABLE documentation_sets ADD CONSTRAINT native_docs_set_snapshot_owner FOREIGN KEY (snapshot_id,native_release_id,scope) REFERENCES documentation_snapshots (id,native_release_id,scope) ON DELETE RESTRICT"
        ),
    ]
