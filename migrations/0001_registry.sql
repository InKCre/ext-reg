PRAGMA foreign_keys = ON;

CREATE TABLE namespaces (
  name TEXT PRIMARY KEY,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'blocked')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
) STRICT;

CREATE TABLE credentials (
  token_hash TEXT PRIMARY KEY
    CHECK (length(token_hash) = 64 AND token_hash NOT GLOB '*[^0-9a-f]*'),
  namespace TEXT NOT NULL REFERENCES namespaces(name) ON DELETE RESTRICT,
  label TEXT NOT NULL,
  disabled INTEGER NOT NULL DEFAULT 0 CHECK (disabled IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
) STRICT;

CREATE TABLE extensions (
  name TEXT PRIMARY KEY CHECK (instr(name, '/') > 1),
  namespace TEXT NOT NULL REFERENCES namespaces(name) ON DELETE RESTRICT,
  nickname TEXT NOT NULL,
  publisher_metadata_json TEXT NOT NULL DEFAULT '{}'
    CHECK (json_valid(publisher_metadata_json) AND json_type(publisher_metadata_json) = 'object'),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
) STRICT;

CREATE TABLE releases (
  extension_name TEXT NOT NULL REFERENCES extensions(name) ON DELETE RESTRICT,
  version TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'preparing'
    CHECK (state IN ('preparing', 'published', 'yanked', 'blocked')),
  yank_reason TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  published_at TEXT,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (extension_name, version)
) STRICT;

CREATE TABLE python_distributions (
  extension_name TEXT NOT NULL,
  release_version TEXT NOT NULL,
  normalized_project TEXT NOT NULL,
  project_version TEXT NOT NULL,
  host_sdk TEXT NOT NULL CHECK (host_sdk = 'core-py'),
  host_sdk_range TEXT NOT NULL,
  entry_group TEXT NOT NULL,
  entry_name TEXT NOT NULL,
  entry_object TEXT NOT NULL,
  source_repository TEXT NOT NULL,
  source_revision TEXT NOT NULL,
  build_id TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (extension_name, release_version),
  UNIQUE (normalized_project, project_version),
  FOREIGN KEY (extension_name, release_version)
    REFERENCES releases(extension_name, version) ON DELETE RESTRICT
) STRICT;

CREATE TABLE python_files (
  normalized_project TEXT NOT NULL,
  project_version TEXT NOT NULL,
  filename TEXT NOT NULL CHECK (instr(filename, '/') = 0 AND instr(filename, '\\') = 0),
  sha256 TEXT NOT NULL CHECK (length(sha256) = 64 AND sha256 NOT GLOB '*[^0-9a-f]*'),
  size INTEGER NOT NULL CHECK (size >= 0 AND size <= 20971520),
  filetype TEXT NOT NULL CHECK (filetype = 'bdist_wheel'),
  requires_python TEXT,
  core_metadata_sha256 TEXT NOT NULL
    CHECK (
      length(core_metadata_sha256) = 64
      AND core_metadata_sha256 NOT GLOB '*[^0-9a-f]*'
    ),
  r2_key TEXT NOT NULL UNIQUE,
  metadata_r2_key TEXT NOT NULL UNIQUE,
  uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (normalized_project, project_version, filename),
  FOREIGN KEY (normalized_project, project_version)
    REFERENCES python_distributions(normalized_project, project_version) ON DELETE RESTRICT
) STRICT;

CREATE TABLE module_federation_distributions (
  extension_name TEXT NOT NULL,
  release_version TEXT NOT NULL,
  host_sdk TEXT NOT NULL CHECK (host_sdk = '@inkcre/core'),
  host_sdk_range TEXT NOT NULL,
  source_repository TEXT NOT NULL,
  source_revision TEXT NOT NULL,
  build_id TEXT,
  manifest_r2_key TEXT,
  asset_paths_json TEXT
    CHECK (
      asset_paths_json IS NULL
      OR (
        json_valid(asset_paths_json)
        AND json_type(asset_paths_json) = 'array'
      )
    ),
  internal_snapshot_hash TEXT
    CHECK (
      internal_snapshot_hash IS NULL
      OR (
        length(internal_snapshot_hash) = 64
        AND internal_snapshot_hash NOT GLOB '*[^0-9a-f]*'
      )
    ),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  uploaded_at TEXT,
  PRIMARY KEY (extension_name, release_version),
  FOREIGN KEY (extension_name, release_version)
    REFERENCES releases(extension_name, version) ON DELETE RESTRICT,
  CHECK (
    (
      manifest_r2_key IS NULL
      AND asset_paths_json IS NULL
      AND internal_snapshot_hash IS NULL
      AND uploaded_at IS NULL
    )
    OR
    (
      manifest_r2_key IS NOT NULL
      AND asset_paths_json IS NOT NULL
      AND internal_snapshot_hash IS NOT NULL
      AND uploaded_at IS NOT NULL
    )
  )
) STRICT;

CREATE INDEX releases_public_idx
  ON releases(extension_name, state, created_at);
CREATE INDEX python_files_project_idx
  ON python_files(normalized_project, uploaded_at);
