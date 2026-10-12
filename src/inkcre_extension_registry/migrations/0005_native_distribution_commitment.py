"""Record publisher intent without inventing commitments for historical Releases."""

from tortoise import fields, migrations
from tortoise.migrations import operations as ops
from tortoise.migrations.constraints import CheckConstraint


class Migration(migrations.Migration):
    dependencies = [("models", "0004_documentation_ownership")]

    operations = [
        ops.AddField(
            model_name="Release",
            name="required_native_formats",
            field=fields.JSONField(null=True),
        ),
        ops.AddConstraint(
            model_name="Release",
            constraint=CheckConstraint(
                'required_native_formats IS NULL OR required_native_formats IN (\'["python"]\'::jsonb, \'["module_federation"]\'::jsonb, \'["python","module_federation"]\'::jsonb, \'["module_federation","python"]\'::jsonb)',
                "release_required_native_formats",
            ),
        ),
    ]
