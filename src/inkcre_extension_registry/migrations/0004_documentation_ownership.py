"""Keep the current pointer attached to its snapshot's exact Release and scope."""

from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise.migrations.constraints import UniqueConstraint


class Migration(migrations.Migration):
    dependencies = [("models", "0003_auto_20260921_0025")]

    operations = [
        ops.AddConstraint(
            model_name="DocumentationSnapshot",
            constraint=UniqueConstraint(("id", "release_id", "scope"), "docs_snapshot_owner"),
        ),
        # Tortoise relations model single-column FKs; PostgreSQL owns this
        # cross-row invariant in addition to the ORM's navigable snapshot FK.
        ops.RunSQL(
            "ALTER TABLE documentation_sets ADD CONSTRAINT docs_set_snapshot_owner "
            "FOREIGN KEY (snapshot_id, release_id, scope) "
            "REFERENCES documentation_snapshots (id, release_id, scope) ON DELETE RESTRICT",
            "ALTER TABLE documentation_sets DROP CONSTRAINT docs_set_snapshot_owner",
        ),
    ]
