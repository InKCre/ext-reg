from __future__ import annotations

from collections.abc import Sequence
from html import escape

from ..contracts.models import ExtensionSummary


def extension_catalog_html(extensions: Sequence[ExtensionSummary]) -> str:
    cards = "".join(
        (
            '<li><a class="extension" href="/v1/extensions/'
            f'{escape(extension.name, quote=True)}">'
            f'<span class="nickname">{escape(extension.nickname)}</span>'
            f'<span class="name">{escape(extension.name)}</span>'
            "</a></li>"
        )
        for extension in extensions
    )
    catalog = (
        f'<ul class="catalog" aria-label="Published Extensions">{cards}</ul>'
        if cards
        else (
            '<div class="empty">'
            "<p>No Extensions published yet.</p>"
            "<span>Published Releases will appear here.</span>"
            "</div>"
        )
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Public InKCre Extension catalog">
  <title>InKCre Extension Registry</title>
  <style>
    :root {{ color-scheme: light dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      color: #191919;
      background: #f5f4f0;
    }}
    main {{ width: min(920px, calc(100% - 40px)); margin: 0 auto; padding: 72px 0 96px; }}
    header {{ border-bottom: 1px solid #d8d6cf; padding-bottom: 32px; }}
    .eyebrow {{ margin: 0 0 12px; color: #64615a; font-size: 0.75rem; font-weight: 700;
      letter-spacing: 0.12em; text-transform: uppercase; }}
    h1 {{ margin: 0; max-width: 700px; font-size: clamp(2.4rem, 7vw, 5.2rem);
      font-weight: 650; letter-spacing: -0.055em; line-height: 0.94; }}
    .intro {{ max-width: 620px; margin: 24px 0 0; color: #5c5952; font-size: 1.05rem;
      line-height: 1.65; }}
    h2 {{ margin: 44px 0 18px; font-size: 0.82rem; letter-spacing: 0.08em;
      text-transform: uppercase; }}
    .catalog {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 12px; margin: 0; padding: 0; list-style: none; }}
    .extension {{ display: flex; min-height: 132px; flex-direction: column;
      justify-content: flex-end;
      gap: 8px; padding: 22px; color: inherit; background: #fff; border: 1px solid #dedcd5;
      border-radius: 18px; text-decoration: none;
      transition: border-color 140ms, transform 140ms; }}
    .extension:hover {{ border-color: #8e8a80; transform: translateY(-2px); }}
    .extension:focus-visible {{ outline: 3px solid #5a67d8; outline-offset: 3px; }}
    .nickname {{ font-size: 1.3rem; font-weight: 650; }}
    .name {{ color: #706d65; font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 0.82rem; }}
    .empty {{ padding: 34px; color: #605d55; border: 1px dashed #bbb7ad; border-radius: 18px; }}
    .empty p {{ margin: 0 0 6px; color: #262522; font-size: 1.1rem; font-weight: 650; }}
    .empty span {{ font-size: 0.92rem; }}
    footer {{ margin-top: 48px; color: #747168; font-size: 0.78rem; }}
    footer a {{ color: inherit; }}
    @media (prefers-color-scheme: dark) {{
      body {{ color: #efeee9; background: #171715; }}
      header {{ border-color: #3b3a36; }}
      .eyebrow, .intro, .name, footer {{ color: #aaa79e; }}
      .extension {{ background: #22221f; border-color: #3d3c37; }}
      .extension:hover {{ border-color: #77746c; }}
      .empty {{ color: #aaa79e; border-color: #4a4943; }}
      .empty p {{ color: #efeee9; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <p class="eyebrow">InKCre · Public Registry</p>
      <h1>Extensions</h1>
      <p class="intro">Published Extensions for InKCre peers, distributed through native
        Python and Module Federation package surfaces.</p>
    </header>
    <section aria-labelledby="catalog-heading">
      <h2 id="catalog-heading">Available now</h2>
      {catalog}
    </section>
    <footer>Machine-readable catalog: <a href="/v1/extensions">/v1/extensions</a></footer>
  </main>
</body>
</html>
"""
