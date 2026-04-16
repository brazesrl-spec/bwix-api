"""BWIX — PDF report generation via WeasyPrint."""

import base64
import io
from datetime import datetime

from weasyprint import HTML


def _fmt_eur(v):
    if v is None:
        return "N/A"
    return f"{round(v):,}".replace(",", "\u202f") + "\u202f\u20ac"


def _fmt_pct(v):
    if v is None:
        return "N/A"
    return f"{v * 100:.1f}\u202f%"


def _badge_style(badge_color):
    colors = {
        "vert": ("#00c896", "#e6faf4"),
        "jaune": ("#b8860b", "#fef9e7"),
        "rouge": ("#c0392b", "#fdecec"),
        "gris": ("#666", "#f0f0f0"),
    }
    fg, bg = colors.get(badge_color, ("#666", "#f0f0f0"))
    return f"background:{bg};color:{fg};padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600"


def _badge_label(badge_color):
    return {"vert": "Bon", "jaune": "Correct", "rouge": "Faible", "gris": "N/A"}.get(badge_color, "N/A")


def _score_svg(score):
    """Generate an SVG gauge for the health score."""
    color = "#00c896" if score >= 70 else "#ffb432" if score >= 50 else "#ff8c00" if score >= 30 else "#ef4444"
    offset = 327 - (score / 100) * 327
    return f"""<svg width="100" height="100" viewBox="0 0 120 120">
      <circle cx="60" cy="60" r="52" fill="none" stroke="#e0e0e0" stroke-width="8"/>
      <circle cx="60" cy="60" r="52" fill="none" stroke="{color}" stroke-width="8"
        stroke-dasharray="327" stroke-dashoffset="{offset}" stroke-linecap="round"
        transform="rotate(-90 60 60)"/>
      <text x="60" y="55" text-anchor="middle" font-size="28" font-weight="700" fill="#1a1a1a">{score}</text>
      <text x="60" y="72" text-anchor="middle" font-size="12" fill="#888">/100</text>
    </svg>"""


def _score_label(score):
    if score < 30:
        return "Situation critique"
    if score < 50:
        return "Situation fragile"
    if score < 70:
        return "Situation correcte"
    return "Bonne sant\u00e9"


def _ratio_rows(data):
    """Build ratio table rows from analysis data."""
    ratios = data.get("ratios", {})
    badges = ratios.get("badges", {})
    rent = ratios.get("rentabilite", {})
    struct = ratios.get("structure", {})
    liq = ratios.get("liquidite", {})

    rows_def = [
        ("EBITDA", _fmt_eur(rent.get("ebitda")), None, None),
        ("Marge EBITDA", _fmt_pct(rent.get("marge_ebitda")), None, None),
        ("Marge nette", _fmt_pct(rent.get("marge_nette")), None, None),
        ("ROE", _fmt_pct(rent.get("roe")), badges.get("roe", {}), None),
        ("ROA", _fmt_pct(rent.get("roa")), None, None),
        ("Solvabilit\u00e9", _fmt_pct(struct.get("solvabilite")), badges.get("solvabilite", {}), None),
        ("Liquidit\u00e9 g\u00e9n\u00e9rale", f"{struct.get('liquidite_generale', liq.get('liquidite_generale', 'N/A'))}" if isinstance(liq.get("liquidite_generale"), (int, float)) else "N/A", badges.get("liquidite", {}), None),
        ("Gearing", f"{struct.get('gearing', 'N/A')}" if isinstance(struct.get("gearing"), (int, float)) else "N/A", badges.get("gearing", {}), None),
        ("Dette nette / EBITDA", f"{struct.get('dettes_ebitda', 'N/A')}" if isinstance(struct.get("dettes_ebitda"), (int, float)) else "N/A", badges.get("dette_ebitda", {}), None),
        ("Couverture int\u00e9r\u00eats", f"{struct.get('couverture_interets', 'N/A')}x" if isinstance(struct.get("couverture_interets"), (int, float)) else "N/A", badges.get("couverture", {}), None),
        ("BFR", _fmt_eur(liq.get("bfr")), None, None),
        ("BFR (jours CA)", f"{int(liq.get('bfr_jours_ca', 0))}j" if liq.get("bfr_jours_ca") else "N/A", None, None),
    ]

    # Fix liquidite display
    liq_val = liq.get("liquidite_generale")
    rows_def[6] = ("Liquidit\u00e9 g\u00e9n\u00e9rale", f"{liq_val:.2f}" if isinstance(liq_val, (int, float)) else "N/A", badges.get("liquidite", {}), None)
    gearing_val = struct.get("gearing")
    rows_def[7] = ("Gearing", f"{gearing_val:.2f}" if isinstance(gearing_val, (int, float)) else "N/A", badges.get("gearing", {}), None)
    de_val = struct.get("dettes_ebitda")
    rows_def[8] = ("Dette nette / EBITDA", f"{de_val:.1f}x" if isinstance(de_val, (int, float)) else "N/A", badges.get("dette_ebitda", {}), None)
    ci_val = struct.get("couverture_interets")
    rows_def[9] = ("Couverture int\u00e9r\u00eats", f"{ci_val:.1f}x" if isinstance(ci_val, (int, float)) else "N/A", badges.get("couverture", {}), None)

    html = ""
    for label, value, badge_data, _ in rows_def:
        badge_html = ""
        bench_html = ""
        if badge_data and badge_data.get("badge"):
            style = _badge_style(badge_data["badge"])
            blabel = badge_data.get("label", _badge_label(badge_data["badge"]))
            badge_html = f'<span style="{style}">{blabel}</span>'
            if badge_data.get("benchmark"):
                bench_html = f'<span style="font-size:10px;color:#888">{badge_data["benchmark"]}</span>'
        html += f"""<tr>
          <td style="padding:6px 10px;border-bottom:1px solid #eee;font-size:12px">{label}</td>
          <td style="padding:6px 10px;border-bottom:1px solid #eee;font-size:12px;font-weight:600;text-align:right">{value}</td>
          <td style="padding:6px 10px;border-bottom:1px solid #eee;text-align:center">{badge_html}</td>
          <td style="padding:6px 10px;border-bottom:1px solid #eee">{bench_html}</td>
        </tr>"""
    return html


def _evolution_rows(data):
    """Build N vs N-1 evolution rows if available."""
    exercices = data.get("exercices", [])
    if len(exercices) < 2:
        return ""
    # Compare last two exercices
    prev = exercices[-2]
    curr = exercices[-1]
    prev_r = prev.get("ratios", {}).get("rentabilite", {})
    curr_r = curr.get("ratios", {}).get("rentabilite", {})

    rows = []
    for label, key in [("EBITDA", "ebitda"), ("ROE", "roe"), ("Marge EBITDA", "marge_ebitda")]:
        v_prev = prev_r.get(key)
        v_curr = curr_r.get(key)
        if v_prev is not None and v_curr is not None:
            if key == "ebitda":
                fmt = _fmt_eur
            else:
                fmt = _fmt_pct
            arrow = "\u2191" if v_curr > v_prev else "\u2193" if v_curr < v_prev else "\u2192"
            rows.append(f"<tr><td style='padding:4px 10px;font-size:11px'>{label}</td>"
                        f"<td style='padding:4px 10px;font-size:11px;text-align:right'>{fmt(v_prev)}</td>"
                        f"<td style='padding:4px 10px;font-size:11px;text-align:center'>{arrow}</td>"
                        f"<td style='padding:4px 10px;font-size:11px;text-align:right;font-weight:600'>{fmt(v_curr)}</td></tr>")

    if not rows:
        return ""
    annee_prev = prev.get("annee", "N-1")
    annee_curr = curr.get("annee", "N")
    return f"""<table style="width:100%;border-collapse:collapse;margin-top:8px">
      <tr style="background:#f8f8f8"><th style="padding:4px 10px;font-size:11px;text-align:left">Ratio</th>
      <th style="padding:4px 10px;font-size:11px;text-align:right">{annee_prev}</th>
      <th style="padding:4px 10px;font-size:11px;text-align:center">Evol.</th>
      <th style="padding:4px 10px;font-size:11px;text-align:right">{annee_curr}</th></tr>
      {"".join(rows)}</table>"""


def generate_pdf(data: dict) -> bytes:
    """Generate a PDF report from analysis data. Returns PDF bytes."""
    now = datetime.now()
    date_str = now.strftime("%d/%m/%Y")
    denomination = data.get("denomination", "Soci\u00e9t\u00e9")
    annees = data.get("annees_disponibles", [data.get("annee")])
    annees_str = "-".join(str(a) for a in annees if a) if annees else ""
    score = data.get("score_sante", 50)
    valo = data.get("valorisation", {})
    ai = data.get("ai_analysis", {})
    prod = data.get("productivite")

    # Score SVG
    score_svg = _score_svg(score)
    score_label = _score_label(score)

    # Ratio rows
    ratio_html = _ratio_rows(data)

    # Evolution
    evolution_html = _evolution_rows(data)

    # Productivity section
    prod_html = ""
    if prod and prod.get("etp") and prod["etp"] > 0:
        badge_color = prod.get("badge_ebitda_etp", "gris")
        style = _badge_style(badge_color)
        prod_html = f"""
        <div style="margin-top:24px;page-break-inside:avoid">
          <h3 style="color:#1a1a1a;font-size:14px;margin-bottom:8px;border-bottom:2px solid #00c896;padding-bottom:4px">Productivit\u00e9 par employ\u00e9 ({prod['etp']} ETP)</h3>
          <table style="width:100%;border-collapse:collapse">
            <tr><td style="padding:6px 10px;font-size:12px">EBITDA / ETP</td>
                <td style="padding:6px 10px;font-size:12px;font-weight:600;text-align:right">{_fmt_eur(prod.get('ebitda_par_etp'))}</td>
                <td style="padding:6px 10px;text-align:center"><span style="{style}">{_badge_label(badge_color)}</span></td></tr>
            <tr><td style="padding:6px 10px;font-size:12px">Marge brute / ETP</td>
                <td style="padding:6px 10px;font-size:12px;font-weight:600;text-align:right">{_fmt_eur(prod.get('marge_par_etp'))}</td>
                <td></td></tr>"""
        if prod.get("ca_par_etp"):
            prod_html += f"""<tr><td style="padding:6px 10px;font-size:12px">CA / ETP</td>
                <td style="padding:6px 10px;font-size:12px;font-weight:600;text-align:right">{_fmt_eur(prod.get('ca_par_etp'))}</td>
                <td></td></tr>"""
        prod_html += "</table>"
        if prod.get("benchmark"):
            prod_html += f'<p style="font-size:10px;color:#888;margin-top:4px">{prod["benchmark"]}</p>'
        prod_html += "</div>"

    # AI diagnostic
    def _list_html(items, color):
        if not items:
            return ""
        lis = "".join(f'<li style="margin-bottom:4px;font-size:11px;line-height:1.5">{item}</li>' for item in items)
        return f'<ul style="margin:0;padding-left:18px;border-left:3px solid {color}">{lis}</ul>'

    points_forts = _list_html(ai.get("points_forts", []), "#00c896")
    points_attention = _list_html(ai.get("points_attention", []), "#f59e0b")
    risques = _list_html(ai.get("risques", []), "#ef4444")
    recommandations = _list_html(ai.get("recommandations", []), "#3b82f6")

    # EBITDA pondere detail
    ebitda_detail_html = ""
    detail = valo.get("ebitda_pondere_detail", [])
    if detail and len(detail) > 1:
        rows = "".join(
            f"<tr><td style='padding:3px 8px;font-size:11px'>{d['annee']}</td>"
            f"<td style='padding:3px 8px;font-size:11px;text-align:right'>{_fmt_eur(d['ebitda'])}</td>"
            f"<td style='padding:3px 8px;font-size:11px;text-align:center'>{d.get('poids_pct', int(d.get('poids', 0) * 100))}%</td>"
            f"<td style='padding:3px 8px;font-size:11px;text-align:right'>{_fmt_eur(d['contribution'])}</td></tr>"
            for d in detail
        )
        ebitda_detail_html = f"""
        <table style="width:100%;border-collapse:collapse;margin-top:6px;background:#f9f9f9;border-radius:4px">
          <tr style="background:#f0f0f0"><th style="padding:3px 8px;font-size:10px;text-align:left">Ann\u00e9e</th>
          <th style="padding:3px 8px;font-size:10px;text-align:right">EBITDA</th>
          <th style="padding:3px 8px;font-size:10px;text-align:center">Poids</th>
          <th style="padding:3px 8px;font-size:10px;text-align:right">Contribution</th></tr>
          {rows}
        </table>"""

    # Fourchette methode
    fourchette_methode = valo.get("fourchette_methode", "")

    html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<style>
  @page {{
    size: A4;
    margin: 20mm 18mm 25mm 18mm;
    @top-left {{
      content: "";
    }}
    @bottom-center {{
      content: "";
    }}
  }}
  @page :first {{
    margin-top: 15mm;
  }}
  body {{
    font-family: Helvetica, Arial, sans-serif;
    color: #1a1a1a;
    font-size: 12px;
    line-height: 1.5;
    margin: 0;
    padding: 0;
  }}
  .page-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #00c896;
    padding-bottom: 8px;
    margin-bottom: 6px;
  }}
  .page-header-logo {{
    font-size: 22px;
    font-weight: 800;
    color: #00c896;
    letter-spacing: -0.5px;
  }}
  .page-header-url {{
    font-size: 10px;
    color: #999;
  }}
  .footer-line {{
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    text-align: center;
    font-size: 8px;
    color: #aaa;
    padding: 6px 18mm;
    border-top: 1px solid #e0e0e0;
  }}
  h2 {{
    color: #1a1a1a;
    font-size: 18px;
    margin: 0 0 4px 0;
  }}
  h3 {{
    color: #1a1a1a;
    font-size: 14px;
    margin: 16px 0 8px 0;
  }}
  .subtitle {{
    font-size: 11px;
    color: #888;
    margin: 0 0 16px 0;
  }}
  .score-row {{
    display: flex;
    align-items: center;
    gap: 20px;
    margin: 16px 0;
  }}
  .score-info {{
    flex: 1;
  }}
  .valo-box {{
    background: #f8fffe;
    border: 1px solid #c8ede4;
    border-radius: 8px;
    padding: 14px 18px;
    margin: 12px 0;
  }}
  .valo-range {{
    font-size: 16px;
    font-weight: 700;
    color: #1a1a1a;
    text-align: center;
  }}
  .valo-label {{
    font-size: 10px;
    color: #888;
    text-align: center;
    margin-top: 4px;
  }}
  .diagnostic {{
    page-break-inside: avoid;
  }}
  .diag-section {{
    margin-bottom: 12px;
  }}
  .diag-section h4 {{
    font-size: 12px;
    margin: 8px 0 4px 0;
    color: #555;
  }}
  .page-break {{
    page-break-before: always;
  }}
</style>
</head>
<body>

<!-- Header -->
<div class="page-header">
  <span class="page-header-logo">BWIX.</span>
  <span class="page-header-url">bwix.app</span>
</div>

<!-- Footer (fixed) -->
<div class="footer-line">
  &copy; BWIX.app &mdash; {date_str} &mdash; Analyse indicative, non contractuelle. Consultez votre fiduciaire ou conseiller juridique pour toute d&eacute;cision.
</div>

<!-- Page 1: Header + Score + Valorisation -->
<h2>Rapport d'analyse financi&egrave;re</h2>
<p style="font-size:14px;font-weight:600;color:#333;margin:0">{denomination}</p>
<p class="subtitle">Exercices : {annees_str} &mdash; G&eacute;n&eacute;r&eacute; le {date_str}</p>
<p style="font-size:10px;color:#999;margin:-10px 0 16px 0">Rapport g&eacute;n&eacute;r&eacute; par BWIX.app &mdash; Analyse financi&egrave;re automatis&eacute;e depuis le bilan officiel BNB</p>

<div class="score-row">
  <div>{score_svg}</div>
  <div class="score-info">
    <div style="font-size:14px;font-weight:700">Score sant&eacute; : {score}/100</div>
    <div style="font-size:12px;color:#666">{score_label}</div>
  </div>
</div>

<div class="valo-box">
  <div style="font-size:11px;color:#888;text-align:center;margin-bottom:4px">Fourchette de valorisation</div>
  <div class="valo-range">{_fmt_eur(valo.get('fourchette_basse'))} &mdash; {_fmt_eur(valo.get('fourchette_haute'))}</div>
  <div class="valo-label">{fourchette_methode}</div>
  <table style="width:100%;border-collapse:collapse;margin-top:10px">
    <tr>
      <td style="padding:4px 8px;font-size:11px;color:#666">EBITDA pond&eacute;r&eacute;</td>
      <td style="padding:4px 8px;font-size:11px;font-weight:600;text-align:right">{_fmt_eur(valo.get('ebitda_reference'))}</td>
    </tr>
    <tr>
      <td style="padding:4px 8px;font-size:11px;color:#666">Multiple sectoriel</td>
      <td style="padding:4px 8px;font-size:11px;font-weight:600;text-align:right">{valo.get('multiple_sectoriel', 'N/A')}x</td>
    </tr>
    <tr>
      <td style="padding:4px 8px;font-size:11px;color:#666">EV/EBITDA</td>
      <td style="padding:4px 8px;font-size:11px;font-weight:600;text-align:right">{_fmt_eur(valo.get('ev_ebitda'))}</td>
    </tr>
    <tr>
      <td style="padding:4px 8px;font-size:11px;color:#666">DCF (equity)</td>
      <td style="padding:4px 8px;font-size:11px;font-weight:600;text-align:right">{_fmt_eur(valo.get('dcf')) if valo.get('dcf') else 'Non calculable'}</td>
    </tr>
    <tr>
      <td style="padding:4px 8px;font-size:11px;color:#666">Actif net comptable</td>
      <td style="padding:4px 8px;font-size:11px;font-weight:600;text-align:right">{_fmt_eur(valo.get('actif_net'))}</td>
    </tr>
  </table>
  {ebitda_detail_html}
</div>

<!-- Page 2: Ratios -->
<div class="page-break"></div>
<div class="page-header">
  <span class="page-header-logo">BWIX.</span>
  <span class="page-header-url">bwix.app</span>
</div>

<h3 style="border-bottom:2px solid #00c896;padding-bottom:4px">Ratios financiers</h3>
<table style="width:100%;border-collapse:collapse">
  <tr style="background:#f8f8f8">
    <th style="padding:6px 10px;font-size:11px;text-align:left">Ratio</th>
    <th style="padding:6px 10px;font-size:11px;text-align:right">Valeur</th>
    <th style="padding:6px 10px;font-size:11px;text-align:center">Statut</th>
    <th style="padding:6px 10px;font-size:11px;text-align:left">Benchmark</th>
  </tr>
  {ratio_html}
</table>

{evolution_html}

{prod_html}

<!-- Page 3: Diagnostic -->
<div class="page-break"></div>
<div class="page-header">
  <span class="page-header-logo">BWIX.</span>
  <span class="page-header-url">bwix.app</span>
</div>

<h3 style="border-bottom:2px solid #00c896;padding-bottom:4px">Diagnostic financier</h3>

<div class="diagnostic">
  <p style="font-size:12px;line-height:1.6;color:#333;margin-bottom:12px">{ai.get('synthese', '')}</p>

  <div class="diag-section">
    <h4 style="color:#00c896">Points forts</h4>
    {points_forts if points_forts else '<p style="font-size:11px;color:#999">Aucun</p>'}
  </div>

  <div class="diag-section">
    <h4 style="color:#f59e0b">Points d'attention</h4>
    {points_attention if points_attention else '<p style="font-size:11px;color:#999">Aucun</p>'}
  </div>

  <div class="diag-section">
    <h4 style="color:#ef4444">Risques</h4>
    {risques if risques else '<p style="font-size:11px;color:#999">Aucun</p>'}
  </div>

  <div class="diag-section">
    <h4 style="color:#3b82f6">Recommandations</h4>
    {recommandations if recommandations else '<p style="font-size:11px;color:#999">Aucun</p>'}
  </div>

  {"<div class='diag-section'><h4>Commentaire valorisation</h4><p style='font-size:11px;line-height:1.5'>" + ai['valorisation_commentaire'] + "</p></div>" if ai.get('valorisation_commentaire') else ""}
</div>

</body>
</html>"""

    pdf_bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes


def generate_pdf_base64(data: dict) -> str:
    """Generate PDF and return as base64 string (for email attachment)."""
    pdf_bytes = generate_pdf(data)
    return base64.b64encode(pdf_bytes).decode("utf-8")


def pdf_filename(data: dict) -> str:
    """Generate a clean filename for the PDF."""
    denom = data.get("denomination", "Analyse")
    # Clean for filename
    clean = "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in denom).strip().replace(" ", "_")
    annees = data.get("annees_disponibles", [data.get("annee")])
    annee_str = str(annees[-1]) if annees and annees[-1] else ""
    return f"BWIX_{clean}_{annee_str}.pdf"
