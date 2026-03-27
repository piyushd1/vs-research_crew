from __future__ import annotations

from html import escape
from pathlib import Path


def _markdownish_to_html(markdown_text: str, title: str) -> str:
    lines = markdown_text.splitlines()
    html_lines = [
        "<html><head><meta charset='utf-8'>",
        f"<title>{escape(title)}</title>",
        "<style>body{font-family:Arial,sans-serif;margin:40px;color:#111;} h1,h2,h3{margin-top:24px;} ul{padding-left:20px;} p{line-height:1.5;}</style>",
        "</head><body>",
    ]
    in_list = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            continue
        if stripped.startswith("# "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h1>{escape(stripped[2:])}</h1>")
            continue
        if stripped.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h2>{escape(stripped[3:])}</h2>")
            continue
        if stripped.startswith("### "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h3>{escape(stripped[4:])}</h3>")
            continue
        if stripped.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{escape(stripped[2:])}</li>")
            continue
        if in_list:
            html_lines.append("</ul>")
            in_list = False
        html_lines.append(f"<p>{escape(stripped)}</p>")

    if in_list:
        html_lines.append("</ul>")
    html_lines.append("</body></html>")
    return "\n".join(html_lines)


def export_pdf(markdown_text: str, output_path: Path, title: str) -> None:
    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise RuntimeError(
            "WeasyPrint is not installed. Run your dependency sync to enable PDF export."
        ) from exc

    html = _markdownish_to_html(markdown_text, title)
    HTML(string=html).write_pdf(str(output_path))
