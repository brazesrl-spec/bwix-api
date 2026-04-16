"""BWIX — PDF report generation via ReportLab."""

import base64
import io
import math
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether,
    PageBreak,
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


# ── Colors ─────────────────────────────────────────────────────────────────
BWIX_GREEN = colors.Color(0 / 255, 200 / 255, 150 / 255)
BWIX_GREEN_LIGHT = colors.Color(232 / 255, 250 / 255, 244 / 255)
YELLOW = colors.Color(245 / 255, 158 / 255, 11 / 255)
RED = colors.Color(239 / 255, 68 / 255, 68 / 255)
BLUE = colors.Color(59 / 255, 130 / 255, 246 / 255)
GRAY = colors.Color(0.4, 0.4, 0.4)
LIGHT_GRAY = colors.Color(0.95, 0.95, 0.95)
DARK = colors.Color(0.1, 0.1, 0.1)

BADGE_COLORS = {
    "vert": BWIX_GREEN,
    "jaune": YELLOW,
    "rouge": RED,
    "gris": GRAY,
}
BADGE_BG = {
    "vert": BWIX_GREEN_LIGHT,
    "jaune": colors.Color(254 / 255, 249 / 255, 231 / 255),
    "rouge": colors.Color(253 / 255, 236 / 255, 236 / 255),
    "gris": LIGHT_GRAY,
}


# ── Formatters ─────────────────────────────────────────────────────────────
def _fmt_eur(v):
    if v is None:
        return "N/A"
    return f"{round(v):,}\u202f\u20ac".replace(",", "\u202f")


def _fmt_pct(v):
    if v is None:
        return "N/A"
    return f"{v * 100:.1f}\u202f%"


def _badge_label(badge_color):
    return {"vert": "Bon", "jaune": "Correct", "rouge": "Faible", "gris": "N/A"}.get(badge_color, "N/A")


def _score_label(score):
    if score < 30:
        return "Situation critique"
    if score < 50:
        return "Situation fragile"
    if score < 70:
        return "Situation correcte"
    return "Bonne sant\u00e9 financi\u00e8re"


def _score_color(score):
    if score >= 70:
        return BWIX_GREEN
    if score >= 50:
        return YELLOW
    if score >= 30:
        return colors.Color(1, 140 / 255, 0)
    return RED


# ── Styles ─────────────────────────────────────────────────────────────────
def _get_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("BWIXTitle", parent=styles["Heading1"], fontSize=16, textColor=DARK,
                              spaceAfter=2, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle("BWIXSubtitle", parent=styles["Normal"], fontSize=10, textColor=GRAY,
                              spaceAfter=10))
    styles.add(ParagraphStyle("BWIXSmall", parent=styles["Normal"], fontSize=8, textColor=GRAY))
    styles.add(ParagraphStyle("BWIXSection", parent=styles["Heading2"], fontSize=12, textColor=DARK,
                              fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6,
                              borderWidth=0, borderPadding=0))
    styles.add(ParagraphStyle("BWIXBody", parent=styles["Normal"], fontSize=9, textColor=DARK,
                              leading=13))
    styles.add(ParagraphStyle("BWIXBodySmall", parent=styles["Normal"], fontSize=8, textColor=GRAY,
                              leading=11))
    styles.add(ParagraphStyle("BWIXCenter", parent=styles["Normal"], fontSize=13, textColor=DARK,
                              fontName="Helvetica-Bold", alignment=TA_CENTER))
    styles.add(ParagraphStyle("BWIXCenterSmall", parent=styles["Normal"], fontSize=8, textColor=GRAY,
                              alignment=TA_CENTER))
    styles.add(ParagraphStyle("BWIXBullet", parent=styles["Normal"], fontSize=9, textColor=DARK,
                              leading=13, leftIndent=12, bulletIndent=0))
    return styles


# ── Header / Footer ────────────────────────────────────────────────────────
def _header_footer(canvas_obj, doc):
    canvas_obj.saveState()
    w, h = A4
    # Header
    canvas_obj.setStrokeColor(BWIX_GREEN)
    canvas_obj.setLineWidth(1.5)
    canvas_obj.line(18 * mm, h - 14 * mm, w - 18 * mm, h - 14 * mm)
    canvas_obj.setFont("Helvetica-Bold", 16)
    canvas_obj.setFillColor(BWIX_GREEN)
    canvas_obj.drawString(18 * mm, h - 12 * mm, "BWIX.")
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.setFillColor(GRAY)
    canvas_obj.drawRightString(w - 18 * mm, h - 12 * mm, "bwix.app")
    # Footer
    canvas_obj.setStrokeColor(colors.Color(0.88, 0.88, 0.88))
    canvas_obj.setLineWidth(0.5)
    canvas_obj.line(18 * mm, 16 * mm, w - 18 * mm, 16 * mm)
    canvas_obj.setFont("Helvetica", 6)
    canvas_obj.setFillColor(GRAY)
    now_str = datetime.now().strftime("%d/%m/%Y")
    footer = f"\u00a9 BWIX.app \u2014 {now_str} \u2014 Analyse indicative, non contractuelle. Consultez votre fiduciaire ou conseiller juridique pour toute d\u00e9cision."
    canvas_obj.drawCentredString(w / 2, 11 * mm, footer)
    # Page number
    canvas_obj.drawRightString(w - 18 * mm, 11 * mm, f"Page {doc.page}")
    canvas_obj.restoreState()


# ── Score gauge drawing ────────────────────────────────────────────────────
def _draw_score_gauge(canvas_obj, x, y, score, size=60):
    """Draw a circular score gauge at (x, y)."""
    cx, cy = x + size / 2, y + size / 2
    r = size / 2 - 4
    # Background circle
    canvas_obj.setStrokeColor(colors.Color(0.88, 0.88, 0.88))
    canvas_obj.setLineWidth(5)
    canvas_obj.circle(cx, cy, r, fill=0)
    # Score arc
    score_color = _score_color(score)
    canvas_obj.setStrokeColor(score_color)
    canvas_obj.setLineWidth(5)
    sweep = (score / 100) * 360
    canvas_obj.arc(cx - r, cy - r, cx + r, cy + r, startAng=90, extent=-sweep)
    # Score text
    canvas_obj.setFont("Helvetica-Bold", 18)
    canvas_obj.setFillColor(DARK)
    canvas_obj.drawCentredString(cx, cy - 2, str(score))
    canvas_obj.setFont("Helvetica", 7)
    canvas_obj.setFillColor(GRAY)
    canvas_obj.drawCentredString(cx, cy - 12, "/100")


# ── Section header with green underline ────────────────────────────────────
def _section_header(text, styles):
    return Paragraph(
        f'<font color="#00c896">\u2501</font> {text}',
        styles["BWIXSection"],
    )


# ── Build ratio table data ─────────────────────────────────────────────────
def _build_ratio_table(data, styles):
    ratios = data.get("ratios", {})
    badges = ratios.get("badges", {})
    rent = ratios.get("rentabilite", {})
    struct = ratios.get("structure", {})
    liq = ratios.get("liquidite", {})

    def _fval(v, fmt="eur"):
        if v is None:
            return "N/A"
        if fmt == "eur":
            return _fmt_eur(v)
        if fmt == "pct":
            return _fmt_pct(v)
        if fmt == "ratio":
            return f"{v:.2f}"
        if fmt == "x":
            return f"{v:.1f}x"
        if fmt == "days":
            return f"{int(v)}j"
        return str(v)

    rows_def = [
        ("EBITDA", _fval(rent.get("ebitda")), None),
        ("Marge EBITDA", _fval(rent.get("marge_ebitda"), "pct"), None),
        ("Marge nette", _fval(rent.get("marge_nette"), "pct"), None),
        ("ROE", _fval(rent.get("roe"), "pct"), badges.get("roe")),
        ("ROA", _fval(rent.get("roa"), "pct"), None),
        ("Solvabilit\u00e9", _fval(struct.get("solvabilite"), "pct"), badges.get("solvabilite")),
        ("Liquidit\u00e9 g\u00e9n\u00e9rale", _fval(liq.get("liquidite_generale"), "ratio"), badges.get("liquidite")),
        ("Gearing", _fval(struct.get("gearing"), "ratio"), badges.get("gearing")),
        ("Dette nette / EBITDA", _fval(struct.get("dettes_ebitda"), "x"), badges.get("dette_ebitda")),
        ("Couverture int\u00e9r\u00eats", _fval(struct.get("couverture_interets"), "x"), badges.get("couverture")),
        ("BFR", _fval(liq.get("bfr")), None),
        ("BFR (jours CA)", _fval(liq.get("bfr_jours_ca"), "days"), None),
    ]

    header = [
        Paragraph("<b>Ratio</b>", styles["BWIXBodySmall"]),
        Paragraph("<b>Valeur</b>", styles["BWIXBodySmall"]),
        Paragraph("<b>Statut</b>", styles["BWIXBodySmall"]),
        Paragraph("<b>Benchmark</b>", styles["BWIXBodySmall"]),
    ]
    table_data = [header]

    row_colors = []
    for i, (label, value, badge) in enumerate(rows_def):
        badge_text = ""
        bench_text = ""
        if badge and badge.get("badge"):
            bl = badge.get("label", _badge_label(badge["badge"]))
            bc = {"vert": "#00c896", "jaune": "#b8860b", "rouge": "#c0392b", "gris": "#666"}.get(badge["badge"], "#666")
            badge_text = f'<font color="{bc}"><b>{bl}</b></font>'
            row_colors.append((i + 1, badge["badge"]))
            if badge.get("benchmark"):
                bench_text = badge["benchmark"]
        else:
            row_colors.append((i + 1, None))

        table_data.append([
            Paragraph(label, styles["BWIXBody"]),
            Paragraph(f"<b>{value}</b>", styles["BWIXBody"]),
            Paragraph(badge_text, styles["BWIXBody"]),
            Paragraph(bench_text, styles["BWIXBodySmall"]),
        ])

    col_widths = [120, 80, 55, None]
    available = A4[0] - 36 * mm
    col_widths[3] = available - sum(w for w in col_widths[:3])

    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GRAY),
        ("TEXTCOLOR", (0, 0), (-1, 0), GRAY),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.Color(0.9, 0.9, 0.9)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
    ]
    # Alternate row shading
    for i in range(2, len(table_data), 2):
        style_cmds.append(("BACKGROUND", (0, i), (-1, i), colors.Color(0.98, 0.98, 0.98)))

    t.setStyle(TableStyle(style_cmds))
    return t


# ── Build valuation detail table ───────────────────────────────────────────
def _build_valo_table(valo, styles):
    rows = [
        ("EBITDA pond\u00e9r\u00e9", _fmt_eur(valo.get("ebitda_reference"))),
        ("Multiple sectoriel", f"{valo.get('multiple_sectoriel', 'N/A')}x"),
        ("EV/EBITDA", _fmt_eur(valo.get("ev_ebitda"))),
        ("DCF (equity)", _fmt_eur(valo.get("dcf")) if valo.get("dcf") else "Non calculable"),
        ("Actif net comptable", _fmt_eur(valo.get("actif_net"))),
    ]
    table_data = [[Paragraph(l, styles["BWIXBody"]), Paragraph(f"<b>{v}</b>", styles["BWIXBody"])] for l, v in rows]
    t = Table(table_data, colWidths=[140, 140])
    t.setStyle(TableStyle([
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.Color(0.92, 0.92, 0.92)),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    return t


# ── Build EBITDA pondere detail table ──────────────────────────────────────
def _build_ebitda_detail(valo, styles):
    detail = valo.get("ebitda_pondere_detail", [])
    if not detail or len(detail) < 2:
        return None
    header = [
        Paragraph("<b>Ann\u00e9e</b>", styles["BWIXBodySmall"]),
        Paragraph("<b>EBITDA</b>", styles["BWIXBodySmall"]),
        Paragraph("<b>Poids</b>", styles["BWIXBodySmall"]),
        Paragraph("<b>Contribution</b>", styles["BWIXBodySmall"]),
    ]
    rows = [header]
    for d in detail:
        pct = d.get("poids_pct", int(d.get("poids", 0) * 100))
        rows.append([
            Paragraph(str(d["annee"]), styles["BWIXBodySmall"]),
            Paragraph(_fmt_eur(d["ebitda"]), styles["BWIXBodySmall"]),
            Paragraph(f"{pct}%", styles["BWIXBodySmall"]),
            Paragraph(_fmt_eur(d["contribution"]), styles["BWIXBodySmall"]),
        ])
    t = Table(rows, colWidths=[60, 100, 50, 100])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GRAY),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
    ]))
    return t


# ── Diagnostic bullet list ─────────────────────────────────────────────────
def _diag_list(title, items, color_hex, styles):
    if not items:
        return []
    elements = [Paragraph(f'<font color="{color_hex}"><b>{title}</b></font>', styles["BWIXBody"])]
    for item in items:
        elements.append(Paragraph(f'\u2022 {item}', styles["BWIXBullet"]))
    elements.append(Spacer(1, 6))
    return elements


# ── Productivity section ───────────────────────────────────────────────────
def _build_productivity(prod, styles):
    if not prod or not prod.get("etp") or prod["etp"] <= 0:
        return []
    elements = [_section_header(f"Productivit\u00e9 par employ\u00e9 ({prod['etp']} ETP)", styles)]
    rows = [
        ("EBITDA / ETP", _fmt_eur(prod.get("ebitda_par_etp"))),
        ("Marge brute / ETP", _fmt_eur(prod.get("marge_par_etp"))),
    ]
    if prod.get("ca_par_etp"):
        rows.append(("CA / ETP", _fmt_eur(prod["ca_par_etp"])))
    table_data = [[Paragraph(l, styles["BWIXBody"]), Paragraph(f"<b>{v}</b>", styles["BWIXBody"])] for l, v in rows]
    t = Table(table_data, colWidths=[140, 140])
    t.setStyle(TableStyle([
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.Color(0.92, 0.92, 0.92)),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    elements.append(t)
    if prod.get("benchmark"):
        elements.append(Spacer(1, 3))
        elements.append(Paragraph(prod["benchmark"], styles["BWIXBodySmall"]))
    return elements


# ── Main PDF generation ────────────────────────────────────────────────────
def generate_pdf(data: dict) -> bytes:
    """Generate a PDF report from analysis data. Returns PDF bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=20 * mm, bottomMargin=22 * mm,
    )
    styles = _get_styles()
    elements = []

    now = datetime.now()
    date_str = now.strftime("%d/%m/%Y")
    denomination = data.get("denomination", "Soci\u00e9t\u00e9")
    annees = data.get("annees_disponibles", [data.get("annee")])
    annees_str = "-".join(str(a) for a in annees if a) if annees else ""
    score = data.get("score_sante", 50)
    valo = data.get("valorisation", {})
    ai = data.get("ai_analysis", {})
    prod = data.get("productivite")

    # ── PAGE 1: Header + Score + Valorisation ──────────────────────────
    elements.append(Paragraph("Rapport d'analyse financi\u00e8re", styles["BWIXTitle"]))
    elements.append(Paragraph(f"<b>{denomination}</b>", styles["BWIXBody"]))
    elements.append(Paragraph(
        f"Exercices : {annees_str} \u2014 G\u00e9n\u00e9r\u00e9 le {date_str}",
        styles["BWIXSubtitle"],
    ))
    elements.append(Paragraph(
        "Rapport g\u00e9n\u00e9r\u00e9 par BWIX.app \u2014 Analyse financi\u00e8re automatis\u00e9e depuis le bilan officiel BNB",
        styles["BWIXSmall"],
    ))
    elements.append(Spacer(1, 10))

    # Score as table layout (gauge will be drawn via afterFlowable)
    score_color_hex = {True: "#00c896"}.get(score >= 70,
                      {True: "#ffb432"}.get(score >= 50,
                      {True: "#ff8c00"}.get(score >= 30, "#ef4444")))
    score_text = f'<font size="22" color="{score_color_hex}"><b>{score}</b></font><font size="9" color="#999"> /100</font>'
    score_label_text = _score_label(score)
    score_table = Table([
        [Paragraph(score_text, styles["BWIXBody"]),
         Paragraph(f'<b>Score sant\u00e9</b><br/><font color="#666">{score_label_text}</font>', styles["BWIXBody"])],
    ], colWidths=[80, 200])
    score_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(score_table)
    elements.append(Spacer(1, 8))

    # Valorisation box
    fourchette_methode = valo.get("fourchette_methode", "")
    elements.append(_section_header("Fourchette de valorisation", styles))
    fourchette_text = f"{_fmt_eur(valo.get('fourchette_basse'))}  \u2014  {_fmt_eur(valo.get('fourchette_haute'))}"
    elements.append(Paragraph(f'<font size="14"><b>{fourchette_text}</b></font>', styles["BWIXCenter"]))
    if fourchette_methode:
        elements.append(Paragraph(fourchette_methode, styles["BWIXCenterSmall"]))
    elements.append(Spacer(1, 8))

    # Valuation detail table
    elements.append(_build_valo_table(valo, styles))
    elements.append(Spacer(1, 4))

    # EBITDA pondere detail
    ebitda_detail = _build_ebitda_detail(valo, styles)
    if ebitda_detail:
        elements.append(ebitda_detail)
    elements.append(Spacer(1, 6))

    # ── PAGE 2: Ratios ─────────────────────────────────────────────────
    elements.append(PageBreak())
    elements.append(_section_header("Ratios financiers", styles))
    elements.append(_build_ratio_table(data, styles))
    elements.append(Spacer(1, 10))

    # Evolution N vs N-1
    exercices = data.get("exercices", [])
    if len(exercices) >= 2:
        prev = exercices[-2]
        curr = exercices[-1]
        prev_r = prev.get("ratios", {}).get("rentabilite", {})
        curr_r = curr.get("ratios", {}).get("rentabilite", {})
        evo_rows = []
        for label, key in [("EBITDA", "ebitda"), ("ROE", "roe"), ("Marge EBITDA", "marge_ebitda")]:
            v_prev = prev_r.get(key)
            v_curr = curr_r.get(key)
            if v_prev is not None and v_curr is not None:
                fmt = _fmt_eur if key == "ebitda" else _fmt_pct
                arrow = "\u2191" if v_curr > v_prev else "\u2193" if v_curr < v_prev else "\u2192"
                evo_rows.append([
                    Paragraph(label, styles["BWIXBodySmall"]),
                    Paragraph(fmt(v_prev), styles["BWIXBodySmall"]),
                    Paragraph(arrow, styles["BWIXBodySmall"]),
                    Paragraph(f"<b>{fmt(v_curr)}</b>", styles["BWIXBodySmall"]),
                ])
        if evo_rows:
            annee_prev = prev.get("annee", "N-1")
            annee_curr = curr.get("annee", "N")
            header = [
                Paragraph("<b>Ratio</b>", styles["BWIXBodySmall"]),
                Paragraph(f"<b>{annee_prev}</b>", styles["BWIXBodySmall"]),
                Paragraph("<b>Evol.</b>", styles["BWIXBodySmall"]),
                Paragraph(f"<b>{annee_curr}</b>", styles["BWIXBodySmall"]),
            ]
            evo_table = Table([header] + evo_rows, colWidths=[120, 100, 40, 100])
            evo_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GRAY),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("ALIGN", (2, 0), (2, -1), "CENTER"),
                ("ALIGN", (3, 0), (3, -1), "RIGHT"),
            ]))
            elements.append(Spacer(1, 6))
            elements.append(Paragraph("<b>\u00c9volution N vs N-1</b>", styles["BWIXBodySmall"]))
            elements.append(Spacer(1, 3))
            elements.append(evo_table)

    # Productivity
    prod_elements = _build_productivity(prod, styles)
    if prod_elements:
        elements.append(Spacer(1, 10))
        elements.extend(prod_elements)

    # ── PAGE 3: Diagnostic ─────────────────────────────────────────────
    elements.append(PageBreak())
    elements.append(_section_header("Diagnostic financier", styles))

    synthese = ai.get("synthese", "")
    if synthese:
        elements.append(Paragraph(synthese, styles["BWIXBody"]))
        elements.append(Spacer(1, 10))

    elements.extend(_diag_list("Points forts", ai.get("points_forts", []), "#00c896", styles))
    elements.extend(_diag_list("Points d'attention", ai.get("points_attention", []), "#b8860b", styles))
    elements.extend(_diag_list("Risques", ai.get("risques", []), "#c0392b", styles))
    elements.extend(_diag_list("Recommandations", ai.get("recommandations", []), "#3b82f6", styles))

    valo_comment = ai.get("valorisation_commentaire", "")
    if valo_comment:
        elements.append(Spacer(1, 6))
        elements.append(Paragraph("<b>Commentaire valorisation</b>", styles["BWIXBody"]))
        elements.append(Paragraph(valo_comment, styles["BWIXBody"]))

    # Build PDF
    doc.build(elements, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return buf.getvalue()


def generate_pdf_base64(data: dict) -> str:
    """Generate PDF and return as base64 string (for email attachment)."""
    pdf_bytes = generate_pdf(data)
    return base64.b64encode(pdf_bytes).decode("utf-8")


def pdf_filename(data: dict) -> str:
    """Generate a clean filename for the PDF."""
    denom = data.get("denomination", "Analyse")
    clean = "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in denom).strip().replace(" ", "_")
    annees = data.get("annees_disponibles", [data.get("annee")])
    annee_str = str(annees[-1]) if annees and annees[-1] else ""
    return f"BWIX_{clean}_{annee_str}.pdf"
