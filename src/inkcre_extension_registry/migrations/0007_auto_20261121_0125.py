import functools
from json import dumps, loads

from tortoise import fields, migrations
from tortoise.migrations import operations as ops
from tortoise.migrations.constraints import CheckConstraint


class Migration(migrations.Migration):
    dependencies = [("models", "0006_auto_20261013_1914")]

    initial = False

    operations = [
        # The historical CreateModel serialized checks but some Tortoise versions
        # did not emit them. Restore the declared old check before altering it.
        ops.RunSQL(
            """DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='native_releases'::regclass AND conname='native_distribution') THEN
                ALTER TABLE native_releases ADD CONSTRAINT native_distribution
                CHECK(distribution IN ('python','module_federation'));
            END IF; END $$""",
            reverse_sql="SELECT 1",
        ),
        ops.RemoveConstraint(
            model_name="NativeRelease",
            name="native_distribution",
            fields=None,
        ),
        ops.AddField(
            model_name="NativeRelease",
            name="rust_stdio",
            field=fields.JSONField(
                null=True, encoder=functools.partial(dumps, separators=(",", ":")), decoder=loads
            ),
        ),
        ops.AddConstraint(
            model_name="NativeRelease",
            constraint=CheckConstraint(
                check="distribution IN ('python', 'module_federation', 'rust_stdio')",
                name="native_distribution",
            ),
        ),
    ]
