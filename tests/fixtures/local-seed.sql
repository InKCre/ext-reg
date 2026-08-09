INSERT INTO namespaces(namespace, display_name)
VALUES ('inkcre', 'InKCre')
ON CONFLICT(namespace) DO NOTHING;

INSERT INTO credentials(id, namespace, token_sha256, label)
VALUES (
  'local-smoke',
  'inkcre',
  'ffaccbe65a4c673d628e5c0e3e4a519a2acabbf43f3fd6bbaccdf50d4118ce28',
  'local smoke'
)
ON CONFLICT(id) DO NOTHING;
