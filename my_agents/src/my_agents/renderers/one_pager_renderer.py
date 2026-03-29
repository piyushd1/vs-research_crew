from __future__ import annotations

from html import escape

from my_agents.schemas import FindingsBundle


def _render_list(items: list[str]) -> str:
    if not items:
        return "<li>None recorded.</li>"
    return "".join(f"<li>{escape(item)}</li>" for item in items)


def render_one_pager(bundle: FindingsBundle) -> str:
    score_color = (
        "#1f7a1f"
        if bundle.scorecard.overall_score >= 75
        else "#9c7a00"
        if bundle.scorecard.overall_score >= 50
        else "#a32626"
    )

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(bundle.company_name)} One Pager</title>
  <style>
    :root {{
      --bg: #f4efe4;
      --ink: #182321;
      --card: #fffaf2;
      --accent: {score_color};
      --muted: #596964;
      --line: #d8cebf;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background: linear-gradient(180deg, #f6f1e6 0%, #efe4d2 100%);
      color: var(--ink);
      padding: 32px;
    }}
    .shell {{
      max-width: 1080px;
      margin: 0 auto;
      background: rgba(255,250,242,0.95);
      border: 1px solid var(--line);
      padding: 28px;
      box-shadow: 0 10px 35px rgba(24,35,33,0.08);
    }}
    .hero {{
      display: grid;
      grid-template-columns: 1.5fr 0.9fr;
      gap: 24px;
      align-items: start;
    }}
    .score {{
      border: 1px solid var(--line);
      padding: 20px;
      background: #fff;
    }}
    .score-number {{
      font-size: 56px;
      line-height: 1;
      color: var(--accent);
      font-weight: 700;
    }}
    .eyebrow {{
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-size: 12px;
      color: var(--muted);
    }}
    h1 {{
      font-size: 40px;
      margin: 8px 0 10px;
    }}
    h2 {{
      margin: 0 0 10px;
      font-size: 18px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .grid {{
      margin-top: 24px;
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 16px;
    }}
    .card {{
      border: 1px solid var(--line);
      background: var(--card);
      padding: 18px;
      min-height: 220px;
    }}
    ul {{ margin: 0; padding-left: 18px; }}
    p {{ margin: 0; line-height: 1.55; }}
    .footer {{
      margin-top: 24px;
      color: var(--muted);
      font-size: 13px;
    }}
    @media (max-width: 900px) {{
      body {{ padding: 16px; }}
      .hero, .grid {{ grid-template-columns: 1fr; }}
      h1 {{ font-size: 30px; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div>
        <div class="eyebrow">{escape(bundle.workflow.value)} / India-first VC workflow</div>
        <h1>{escape(bundle.company_name)}</h1>
        <p>{escape(bundle.sections.get("company_snapshot", bundle.summary))}</p>
      </div>
      <aside class="score">
        <div class="eyebrow">Overall score</div>
        <div class="score-number">{bundle.scorecard.overall_score:.0f}</div>
        <p>{escape(bundle.scorecard.recommendation)}</p>
      </aside>
    </section>

    <section class="grid">
      <article class="card">
        <h2>Signals</h2>
        <ul>{_render_list(bundle.top_signals)}</ul>
      </article>
      <article class="card">
        <h2>Risks</h2>
        <ul>{_render_list(bundle.top_risks)}</ul>
      </article>
      <article class="card">
        <h2>Open Questions</h2>
        <ul>{_render_list(bundle.open_questions)}</ul>
      </article>
    </section>

    <section class="grid">
      <article class="card">
        <h2>Recommendation</h2>
        <p>{escape(bundle.sections.get("investment_recommendation", "No recommendation drafted."))}</p>
      </article>
      <article class="card">
        <h2>Next Steps</h2>
        <p>{escape(bundle.sections.get("next_steps", "No next steps drafted."))}</p>
      </article>
      <article class="card">
        <h2>Evidence Gaps</h2>
        <ul>{_render_list(bundle.evidence_gaps)}</ul>
      </article>
    </section>
"""

    optional_sections = {
        "market_landscape": "Market Landscape",
        "financial_analysis": "Financial Analysis",
        "product_technology": "Product & Technology",
        "founder_assessment": "Founder Assessment",
        "gtm_momentum": "GTM Momentum",
        "regulatory_compliance": "Regulatory & Compliance",
        "portfolio_health": "Portfolio Health",
        "support_recommendations": "Support Recommendations",
    }

    extra_cards = []
    for key, title in optional_sections.items():
        if key in bundle.sections:
            extra_cards.append(
                f"""      <article class="card">
        <h2>{title}</h2>
        <p>{escape(bundle.sections[key])}</p>
      </article>"""
            )

    if extra_cards:
        # Group cards into chunks of 3 for the grid
        chunks = [extra_cards[i : i + 3] for i in range(0, len(extra_cards), 3)]
        for chunk in chunks:
            grid_html = "\n".join(chunk)
            html += f'\n    <section class="grid">\n{grid_html}\n    </section>\n'

    html += """
    <div class="footer">Rendered from a deterministic findings bundle with no external assets.</div>
  </main>
</body>
</html>
"""
    return html
