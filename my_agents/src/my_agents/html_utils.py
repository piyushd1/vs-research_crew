from __future__ import annotations

import re
from html import escape


def _is_table_row(line: str) -> bool:
    """Check if a line looks like a markdown table row: | col | col |"""
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 3


def _is_separator_row(line: str) -> bool:
    """Check if a line is a table separator: | --- | --- |"""
    stripped = line.strip()
    return bool(re.match(r"^\|[\s\-:|]+\|$", stripped))


def _render_table(rows: list[str]) -> str:
    """Convert a block of markdown table rows into an HTML table."""
    html_parts: list[str] = ['<table>']
    for i, row in enumerate(rows):
        if _is_separator_row(row):
            continue
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        tag = "th" if i == 0 else "td"
        row_html = "".join(f"<{tag}>{escape(cell)}</{tag}>" for cell in cells)
        html_parts.append(f"<tr>{row_html}</tr>")
    html_parts.append("</table>")
    return "\n".join(html_parts)


def _render_inline(text: str) -> str:
    """Handle bold (**text**) inline formatting."""
    result = escape(text)
    result = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", result)
    return result


def markdownish_to_html_body(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    html_lines: list[str] = []
    in_list = False
    table_buffer: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Table handling: collect contiguous table rows
        if _is_table_row(stripped):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            table_buffer.append(stripped)
            i += 1
            continue
        elif table_buffer:
            html_lines.append(_render_table(table_buffer))
            table_buffer = []

        if not stripped:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            i += 1
            continue

        if stripped.startswith("# "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h1>{_render_inline(stripped[2:])}</h1>")
            i += 1
            continue

        if stripped.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h2>{_render_inline(stripped[3:])}</h2>")
            i += 1
            continue

        if stripped.startswith("### "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h3>{_render_inline(stripped[4:])}</h3>")
            i += 1
            continue

        if stripped.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{_render_inline(stripped[2:])}</li>")
            i += 1
            continue

        if in_list:
            html_lines.append("</ul>")
            in_list = False
        html_lines.append(f"<p>{_render_inline(stripped)}</p>")
        i += 1

    # Flush remaining
    if table_buffer:
        html_lines.append(_render_table(table_buffer))
    if in_list:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


def render_html_document(title: str, body_html: str) -> str:
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '  <meta charset="utf-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1">',
            f"  <title>{escape(title)}</title>",
            "  <style>",
            "    :root { --bg:#f5efe5; --ink:#182321; --card:#fffaf2; --line:#d8cebf; --muted:#5f6e68; --accent:#31574f; }",
            "    * { box-sizing: border-box; }",
            "    body { margin:0; background:linear-gradient(180deg,#f6f1e6 0%,#efe4d2 100%); color:var(--ink); font-family:Georgia,\"Times New Roman\",serif; }",
            "    main { max-width:980px; margin:32px auto; background:rgba(255,250,242,0.96); border:1px solid var(--line); box-shadow:0 12px 40px rgba(24,35,33,0.08); padding:32px; }",
            "    h1 { font-size:38px; margin:0 0 18px; }",
            "    h2 { font-size:20px; margin:28px 0 10px; padding-top:10px; border-top:1px solid var(--line); }",
            "    h3 { font-size:16px; margin:22px 0 8px; color:var(--accent); }",
            "    p, li { line-height:1.62; font-size:16px; }",
            "    ul { padding-left:22px; }",
            "    table { width:100%; border-collapse:collapse; margin:16px 0; font-size:15px; }",
            "    th, td { padding:10px 14px; text-align:left; border-bottom:1px solid var(--line); }",
            "    th { background:var(--accent); color:#fff; font-weight:600; font-size:13px; text-transform:uppercase; letter-spacing:0.04em; }",
            "    tr:nth-child(even) td { background:rgba(49,87,79,0.04); }",
            "    tr:hover td { background:rgba(49,87,79,0.08); }",
            "    strong { font-weight:700; }",
            "    .meta { color:var(--muted); font-size:13px; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:12px; }",
            "    .footer { margin-top:28px; color:var(--muted); font-size:13px; }",
            "    @media (max-width: 900px) { main { margin:16px; padding:20px; } h1 { font-size:30px; } table { font-size:13px; } th, td { padding:6px 8px; } }",
            "  </style>",
            "</head>",
            "<body>",
            "  <main>",
            '    <div class="meta">India-first VC research output</div>',
            body_html,
            '    <div class="footer">Rendered locally from deterministic run artifacts.</div>',
            "  </main>",
            "</body>",
            "</html>",
        ]
    )


def markdownish_to_html_document(markdown_text: str, title: str) -> str:
    return render_html_document(title, markdownish_to_html_body(markdown_text))
