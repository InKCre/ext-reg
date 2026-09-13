"""SQLAlchemy mappings for the existing D1 schema and its binding compiler.

Migrations own DDL. These tables describe the columns and joins used by the
Registry; they are never used to create or alter a database at runtime.
"""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Integer, MetaData, Table, Text
from sqlalchemy.dialects.sqlite import dialect
from sqlalchemy.sql import ClauseElement
from sqlalchemy.sql.compiler import SQLCompiler

metadata = MetaData()
namespaces = Table(
    "namespaces",
    metadata,
    Column("name", Text, primary_key=True),
    Column("status", Text),
    Column("created_at", Text),
)
credentials = Table(
    "credentials",
    metadata,
    Column("token_hash", Text, primary_key=True),
    Column("namespace", Text, ForeignKey("namespaces.name")),
    Column("label", Text),
    Column("disabled", Integer),
    Column("created_at", Text),
)
extensions = Table(
    "extensions",
    metadata,
    Column("name", Text, primary_key=True),
    Column("namespace", Text, ForeignKey("namespaces.name")),
    Column("nickname", Text),
    Column("publisher_metadata_json", Text),
    Column("created_at", Text),
)
releases = Table(
    "releases",
    metadata,
    Column("extension_name", Text, ForeignKey("extensions.name"), primary_key=True),
    Column("version", Text, primary_key=True),
    Column("state", Text),
    Column("yank_reason", Text),
    Column("created_at", Text),
    Column("published_at", Text),
    Column("updated_at", Text),
)
python_distributions = Table(
    "python_distributions",
    metadata,
    Column("extension_name", Text, primary_key=True),
    Column("release_version", Text, primary_key=True),
    Column("normalized_project", Text),
    Column("project_version", Text),
    Column("host_sdk", Text),
    Column("host_sdk_range", Text),
    Column("entry_group", Text),
    Column("entry_name", Text),
    Column("entry_object", Text),
    Column("source_repository", Text),
    Column("source_revision", Text),
    Column("build_id", Text),
    Column("created_at", Text),
    ForeignKeyConstraint(
        ["extension_name", "release_version"], ["releases.extension_name", "releases.version"]
    ),
)
python_files = Table(
    "python_files",
    metadata,
    Column("normalized_project", Text, primary_key=True),
    Column("project_version", Text, primary_key=True),
    Column("filename", Text, primary_key=True),
    Column("sha256", Text),
    Column("size", Integer),
    Column("filetype", Text),
    Column("requires_python", Text),
    Column("core_metadata_sha256", Text),
    Column("r2_key", Text),
    Column("metadata_r2_key", Text),
    Column("uploaded_at", Text),
    ForeignKeyConstraint(
        ["normalized_project", "project_version"],
        ["python_distributions.normalized_project", "python_distributions.project_version"],
    ),
)
module_federation_distributions = Table(
    "module_federation_distributions",
    metadata,
    Column("extension_name", Text, primary_key=True),
    Column("release_version", Text, primary_key=True),
    Column("host_sdk", Text),
    Column("host_sdk_range", Text),
    Column("source_repository", Text),
    Column("source_revision", Text),
    Column("build_id", Text),
    Column("manifest_r2_key", Text),
    Column("asset_paths_json", Text),
    Column("internal_snapshot_hash", Text),
    Column("created_at", Text),
    Column("uploaded_at", Text),
    ForeignKeyConstraint(
        ["extension_name", "release_version"], ["releases.extension_name", "releases.version"]
    ),
)

_DIALECT = dialect(paramstyle="qmark")


def compile_d1(statement: ClauseElement) -> tuple[str, list[object]]:
    """Compile bound parameters in SQLite order, including expanded IN lists."""
    compiled = statement.compile(dialect=_DIALECT, compile_kwargs={"render_postcompile": True})
    assert isinstance(compiled, SQLCompiler)
    assert compiled.positiontup is not None and compiled.params is not None
    return str(compiled), [compiled.params[name] for name in compiled.positiontup]
