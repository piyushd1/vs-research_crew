from __future__ import annotations

from html import escape


def markdownish_to_html_body(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    html_lines: list[str] = []
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
            "    .meta { color:var(--muted); font-size:13px; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:12px; }",
            "    .footer { margin-top:28px; color:var(--muted); font-size:13px; }",
            "    @media (max-width: 900px) { main { margin:16px; padding:20px; } h1 { font-size:30px; } }",
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
