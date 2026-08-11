INSERT INTO namespaces(name)
VALUES ('inkcre')
ON CONFLICT(name) DO NOTHING;

INSERT INTO credentials(token_hash, namespace, label)
VALUES (
  'ffaccbe65a4c673d628e5c0e3e4a519a2acabbf43f3fd6bbaccdf50d4118ce28',
  'inkcre',
  'local smoke'
)
ON CONFLICT(token_hash) DO NOTHING;
