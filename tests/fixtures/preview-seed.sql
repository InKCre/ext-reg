INSERT INTO namespaces(name)
VALUES ('inkcre')
ON CONFLICT(name) DO NOTHING;

INSERT INTO extensions(name, namespace, nickname)
VALUES ('inkcre/preview', 'inkcre', 'Preview Extension')
ON CONFLICT(name) DO UPDATE SET nickname = excluded.nickname;

INSERT INTO releases(extension_name, version, state, published_at)
VALUES ('inkcre/preview', '0.0.0-preview.1', 'published', CURRENT_TIMESTAMP)
ON CONFLICT(extension_name, version) DO UPDATE SET
  state = excluded.state,
  published_at = excluded.published_at;
