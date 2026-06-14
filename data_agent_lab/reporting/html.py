"""HTML report renderer (Stretch)."""

from __future__ import annotations

import html


def render_html_report(markdown: str, title: str = "Data-Agent-Lab Report") -> str:
    body = html.escape(markdown)
    body = body.replace("\n", "<br>\n")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 960px; margin: 2rem auto; line-height: 1.5; }}
    pre {{ background: #f6f8fa; padding: 1rem; overflow-x: auto; }}
  </style>
</head>
<body>
  <pre>{body}</pre>
</body>
</html>
"""
