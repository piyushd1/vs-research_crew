from __future__ import annotations

from pathlib import Path

from my_agents.html_utils import markdownish_to_html_document


def export_pdf(markdown_text: str, output_path: Path, title: str) -> None:
    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise RuntimeError(
            "WeasyPrint is not installed. Run your dependency sync to enable PDF export."
        ) from exc

    html = markdownish_to_html_document(markdown_text, title)
    HTML(string=html).write_pdf(str(output_path))
