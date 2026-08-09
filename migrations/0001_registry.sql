PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS namespaces (
  namespace TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'blocked')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS credentials (
  id TEXT PRIMARY KEY,
  namespace TEXT NOT NULL REFERENCES namespaces(namespace) ON DELETE RESTRICT,
  token_sha256 TEXT NOT NULL UNIQUE CHECK (length(token_sha256) = 64),
  label TEXT NOT NULL,
  disabled INTEGER NOT NULL DEFAULT 0 CHECK (disabled IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS extensions (
  namespace TEXT NOT NULL REFERENCES namespaces(namespace) ON DELETE RESTRICT,
  name TEXT NOT NULL,
  display_name TEXT,
  description TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (namespace, name)
);

CREATE TABLE IF NOT EXISTS releases (
  namespace TEXT NOT NULL,
  name TEXT NOT NULL,
  version TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'preparing'
    CHECK (state IN ('preparing', 'published', 'yanked', 'blocked')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  published_at TEXT,
  PRIMARY KEY (namespace, name, version),
  FOREIGN KEY (namespace, name) REFERENCES extensions(namespace, name) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS targets (
  namespace TEXT NOT NULL,
  name TEXT NOT NULL,
  version TEXT NOT NULL,
  target_key TEXT NOT NULL,
  target_digest TEXT NOT NULL CHECK (target_digest GLOB 'sha256:*'),
  artifact_format TEXT NOT NULL,
  entrypoint TEXT NOT NULL,
  compatibility_json TEXT NOT NULL CHECK (json_valid(compatibility_json)),
  manifest_json TEXT NOT NULL CHECK (json_valid(manifest_json)),
  source_repository TEXT NOT NULL,
  source_revision TEXT NOT NULL,
  build_id TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (namespace, name, version, target_key),
  FOREIGN KEY (namespace, name, version)
    REFERENCES releases(namespace, name, version) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS releases_public_idx
  ON releases(namespace, name, state, created_at);
CREATE INDEX IF NOT EXISTS targets_digest_idx ON targets(target_digest);
