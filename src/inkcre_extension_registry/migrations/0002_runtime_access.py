"""Separate application DML from migration ownership.

Roles and grants are PostgreSQL authorization DDL, outside ORM model state.
New business tables must grant their required access in their own migration.
"""

from tortoise import migrations
from tortoise.migrations import operations as ops


class Migration(migrations.Migration):
    dependencies = [("models", "0001_initial")]

    operations = [
        ops.RunSQL("CREATE ROLE registry_app NOLOGIN"),
        ops.RunSQL("REVOKE CREATE ON SCHEMA public FROM PUBLIC"),
        ops.RunSQL("GRANT USAGE ON SCHEMA public TO registry_app"),
        ops.RunSQL(
            "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE "
            "namespaces, credentials, extensions, releases, "
            "python_distributions, python_files, module_federation_distributions "
            "TO registry_app"
        ),
        ops.RunSQL(
            "GRANT USAGE ON SEQUENCE releases_id_seq, python_distributions_id_seq, "
            "python_files_id_seq, module_federation_distributions_id_seq TO registry_app"
        ),
    ]
