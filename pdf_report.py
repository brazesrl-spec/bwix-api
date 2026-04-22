"""BWIX — PDF report generation via ReportLab (v2 redesign)."""

import base64
import io
from datetime import datetime

from ratios import compute_badges

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether,
    PageBreak, HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.graphics.shapes import Drawing, Circle, Wedge, String, Line, Rect
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.graphics import renderPDF


# ── Colors ─────────────────────────────────────────────────────────────────
BWIX = colors.HexColor("#00c896")
BWIX_LIGHT = colors.HexColor("#e8faf4")
BWIX_DARK = colors.HexColor("#00a87d")
YELLOW_BADGE = colors.HexColor("#f59e0b")
YELLOW_BG = colors.HexColor("#fef9e7")
RED_BADGE = colors.HexColor("#ef4444")
RED_BG = colors.HexColor("#fdecec")
BLUE = colors.HexColor("#3b82f6")
BLUE_BG = colors.HexColor("#eff6ff")
DARK = colors.HexColor("#1a1a2e")
GRAY = colors.HexColor("#6b7280")
GRAY_LIGHT = colors.HexColor("#f3f4f6")
GRAY_LINE = colors.HexColor("#e5e7eb")
WHITE = colors.white

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN


# ── Ratio explanations (didactic) ─────────────────────────────────────────
RATIO_EXPLAIN = {
    "ebitda": "Cash genere par l'activite principale, avant amortissements, financement et impots.",
    "marge_ebitda": "Part du chiffre d'affaires convertie en cash operationnel.",
    "marge_nette": "Part du CA restant en benefice net apres toutes les charges.",
    "roe": "Rendement pour les actionnaires : benefice net / capitaux propres.",
    "roa": "Efficacite globale des actifs a generer du profit.",
    "solvabilite": "Part des fonds propres dans le bilan. > 30% = autonomie financiere saine.",
    "liquidite_generale": "Actifs court terme / dettes court terme. > 1 = capacite a payer ses dettes.",
    "gearing": "Dette nette / capitaux propres. Mesure le levier financier.",
    "dettes_ebitda": "Annees necessaires pour rembourser la dette avec l'EBITDA. < 3 = sain.",
    "couverture_interets": "Nombre de fois que le resultat couvre les charges financieres. > 3 = confortable.",
    "bfr": "Capital immobilise dans le cycle d'exploitation (stocks + creances - fournisseurs).",
    "bfr_jours_ca": "BFR exprime en jours de CA. Moins c'est eleve, mieux c'est.",
}


# ── Formatters ─────────────────────────────────────────────────────────────
def _fmt_eur(v):
    if v is None:
        return "N/A"
    return f"{round(v):,}\u202f\u20ac".replace(",", "\u202f")


def _fmt_pct(v):
    if v is None:
        return "N/A"
    return f"{v * 100:.1f}%"


def _badge_label(bc):
    return {"vert": "Bon", "jaune": "Correct", "rouge": "Faible", "gris": "N/A"}.get(bc, "")


def _badge_color(bc):
    return {"vert": "#00c896", "jaune": "#b8860b", "rouge": "#c0392b", "gris": "#6b7280"}.get(bc, "#6b7280")


def _badge_bg(bc):
    return {"vert": BWIX_LIGHT, "jaune": YELLOW_BG, "rouge": RED_BG, "gris": GRAY_LIGHT}.get(bc, GRAY_LIGHT)


def _score_color_hex(score):
    if score >= 70:
        return "#00c896"
    if score >= 50:
        return "#f59e0b"
    if score >= 30:
        return "#ff8c00"
    return "#ef4444"


def _score_label(score):
    if score < 30:
        return "Situation critique"
    if score < 50:
        return "Situation fragile"
    if score < 70:
        return "Situation correcte"
    return "Bonne sante financiere"


# ── Styles ─────────────────────────────────────────────────────────────────
def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle("Title1", fontName="Helvetica-Bold", fontSize=18, textColor=DARK,
                          spaceAfter=2, leading=22))
    s.add(ParagraphStyle("CompanyName", fontName="Helvetica-Bold", fontSize=13, textColor=DARK,
                          spaceAfter=1, leading=16))
    s.add(ParagraphStyle("Subtitle", fontName="Helvetica", fontSize=9, textColor=GRAY, spaceAfter=4))
    s.add(ParagraphStyle("Tiny", fontName="Helvetica", fontSize=7, textColor=GRAY, leading=9))
    s.add(ParagraphStyle("Section", fontName="Helvetica-Bold", fontSize=12, textColor=DARK,
                          spaceBefore=16, spaceAfter=8, leading=15))
    s.add(ParagraphStyle("SectionSub", fontName="Helvetica", fontSize=8, textColor=GRAY,
                          spaceAfter=6, leading=10))
    s.add(ParagraphStyle("Body", fontName="Helvetica", fontSize=9, textColor=DARK, leading=13))
    s.add(ParagraphStyle("BodyBold", fontName="Helvetica-Bold", fontSize=9, textColor=DARK, leading=13))
    s.add(ParagraphStyle("Small", fontName="Helvetica", fontSize=7.5, textColor=GRAY, leading=10))
    s.add(ParagraphStyle("SmallItalic", fontName="Helvetica-Oblique", fontSize=7.5, textColor=GRAY, leading=10))
    s.add(ParagraphStyle("Center", fontName="Helvetica-Bold", fontSize=14, textColor=DARK,
                          alignment=TA_CENTER, leading=18))
    s.add(ParagraphStyle("CenterSm", fontName="Helvetica", fontSize=8, textColor=GRAY,
                          alignment=TA_CENTER))
    s.add(ParagraphStyle("BWIXBullet", fontName="Helvetica", fontSize=8.5, textColor=DARK,
                          leading=12, leftIndent=14, bulletIndent=0))
    s.add(ParagraphStyle("DiagTitle", fontName="Helvetica-Bold", fontSize=10, textColor=DARK,
                          spaceBefore=8, spaceAfter=3, leading=13))
    s.add(ParagraphStyle("FicheId", fontName="Helvetica", fontSize=8, textColor=colors.HexColor("#374151"),
                          leading=11, spaceAfter=1))
    s.add(ParagraphStyle("FiabLabel", fontName="Helvetica-Bold", fontSize=9.5, leading=13))
    s.add(ParagraphStyle("FiabMsg", fontName="Helvetica", fontSize=8, textColor=colors.HexColor("#374151"),
                          leading=11))
    return s


# ── Fiche d'identite ──────────────────────────────────────────────────────
def _fiche_identite(data, st):
    """Build company identity lines. Skip missing fields silently."""
    parts = []
    # Line 1: raison sociale + BCE + forme juridique
    line1 = []
    if data.get("denomination"):
        line1.append(f'<b>{data["denomination"]}</b>')
    if data.get("bce"):
        line1.append(f'BCE {data["bce"]}')
    if data.get("forme_juridique"):
        line1.append(data["forme_juridique"])
    if line1:
        parts.append(Paragraph(" \u2022 ".join(line1), st["FicheId"]))
    # Line 2: adresse + secteur + NACE
    line2 = []
    if data.get("adresse"):
        line2.append(f'Siege : {data["adresse"]}')
    secteur = data.get("secteur", "")
    if secteur:
        nace = data.get("nace_code")
        line2.append(f'Secteur : {secteur}' + (f' (NACE {nace})' if nace else ''))
    if line2:
        parts.append(Paragraph(" \u2022 ".join(line2), st["FicheId"]))
    # Line 3: exercices
    annees = data.get("annees_disponibles", [])
    annees_clean = sorted([a for a in annees if a])
    if annees_clean:
        nb = len(annees_clean)
        parts.append(Paragraph(
            f'Exercices analyses : {nb} ({annees_clean[0]} \u2192 {annees_clean[-1]})',
            st["FicheId"],
        ))
    # Line 4: source + date
    fmt = data.get("format", "")
    source = "Comptes annuels BNB" if "BNB" in fmt else "Export comptable BOB" if "BOB" in fmt else "Comptes annuels"
    from datetime import datetime
    date_str = datetime.now().strftime("%d/%m/%Y")
    parts.append(Paragraph(f'Source : {source} \u2022 Genere le {date_str}', st["FicheId"]))
    return parts


# ── Bandeau fiabilite ─────────────────────────────────────────────────────
_FIABILITE = {
    "low": {
        "label": "Analyse sur {n} exercice{s}",
        "color": "#EA580C",
        "bg": "#FED7AA",
        "border": "#EA580C",
        "message": "Pour une analyse plus robuste, un minimum de 3 exercices est conseille.",
    },
    "medium": {
        "label": "Analyse correcte \u2014 3 exercices",
        "color": "#CA8A04",
        "bg": "#FEF3C7",
        "border": "#CA8A04",
        "message": "Tendance observable, valorisation ponderee credible.",
    },
    "high": {
        "label": "Analyse robuste \u2014 {n} exercices",
        "color": "#16A34A",
        "bg": "#DCFCE7",
        "border": "#16A34A",
        "message": "Cycle economique visible, tendances confirmees.",
    },
}


def _fiabilite_bandeau(data, st):
    """Build reliability banner as a bordered table."""
    annees = data.get("annees_disponibles", [])
    nb = len([a for a in annees if a])
    if nb <= 2:
        cfg = _FIABILITE["low"]
    elif nb == 3:
        cfg = _FIABILITE["medium"]
    else:
        cfg = _FIABILITE["high"]

    label = cfg["label"].format(n=nb, s="s" if nb > 1 else "")
    col = cfg["color"]
    inner = [
        Paragraph(f'<font color="{col}"><b>{label}</b></font>', st["FiabLabel"]),
        Paragraph(cfg["message"], st["FiabMsg"]),
    ]
    t = Table([[inner]], colWidths=[CONTENT_W - 12])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(cfg["bg"])),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("LINEBELOW", (0, 0), (-1, -1), 0, colors.white),
        ("LINEBEFORE", (0, 0), (0, -1), 4, colors.HexColor(cfg["border"])),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    return t


# ── Header / Footer (drawn on canvas) ─────────────────────────────────────
def _header_footer(c, doc):
    c.saveState()
    # Header bar
    c.setFillColor(BWIX)
    c.rect(0, PAGE_H - 10 * mm, PAGE_W, 10 * mm, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(WHITE)
    c.drawString(MARGIN, PAGE_H - 7.5 * mm, "BWIX.")
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#b0f0dd"))
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - 7.5 * mm, "bwix.app")
    # Footer
    c.setStrokeColor(GRAY_LINE)
    c.setLineWidth(0.5)
    c.line(MARGIN, 14 * mm, PAGE_W - MARGIN, 14 * mm)
    c.setFont("Helvetica", 5.5)
    c.setFillColor(GRAY)
    now_str = datetime.now().strftime("%d/%m/%Y")
    c.drawString(MARGIN, 10 * mm,
                 f"\u00a9 BWIX.app \u2014 {now_str} \u2014 Analyse indicative, non contractuelle. "
                 "Consultez votre fiduciaire pour toute decision.")
    c.setFont("Helvetica", 6)
    c.drawRightString(PAGE_W - MARGIN, 10 * mm, f"Page {doc.page}")
    c.restoreState()


# ── Score gauge (ReportLab Drawing) ────────────────────────────────────────
def _score_drawing(score):
    size = 72
    d = Drawing(size, size)
    cx, cy, r = size / 2, size / 2, 30
    # Background circle
    d.add(Circle(cx, cy, r, strokeColor=GRAY_LINE, strokeWidth=6, fillColor=None))
    # Score arc
    sc = colors.HexColor(_score_color_hex(score))
    sweep = -(score / 100) * 360
    if score > 0:
        d.add(Wedge(cx, cy, r, 90, 90 + sweep, strokeColor=sc, strokeWidth=6,
                     fillColor=None, yradius=r))
    # Score text
    d.add(String(cx, cy - 4, str(score), fontName="Helvetica-Bold", fontSize=18,
                 fillColor=DARK, textAnchor="middle"))
    d.add(String(cx, cy - 14, "/100", fontName="Helvetica", fontSize=7,
                 fillColor=GRAY, textAnchor="middle"))
    return d


# ── Section header ─────────────────────────────────────────────────────────
def _section(text, st, subtitle=None):
    els = [
        HRFlowable(width="100%", thickness=2, color=BWIX, spaceBefore=10, spaceAfter=0),
        Paragraph(text, st["Section"]),
    ]
    if subtitle:
        els.append(Paragraph(subtitle, st["SectionSub"]))
    return els


# ── Colored box ────────────────────────────────────────────────────────────
def _box_table(inner_elements, bg_color=BWIX_LIGHT, border_color=BWIX):
    """Wrap elements in a colored rounded box using a 1-cell table."""
    cell = []
    for el in inner_elements:
        cell.append(el)
    t = Table([[cell]], colWidths=[CONTENT_W - 8])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_color),
        ("BOX", (0, 0), (-1, -1), 1, border_color),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    return t


# ── Ratio table with explanations ─────────────────────────────────────────
def _ratio_table(data, st):
    ratios = data.get("ratios", {})
    # Always recompute badges to include all 10 types
    badges = compute_badges(ratios, data.get("secteur", ""))
    rent = ratios.get("rentabilite", {})
    struct = ratios.get("structure", {})
    liq = ratios.get("liquidite", {})

    def _fv(v, fmt):
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
        ("Rentabilite", None, None, None, None),
        ("EBITDA", _fv(rent.get("ebitda"), "eur"), badges.get("ebitda"), "ebitda", None),
        ("Marge EBITDA", _fv(rent.get("marge_ebitda"), "pct"), badges.get("marge_ebitda"), "marge_ebitda", None),
        ("Marge nette", _fv(rent.get("marge_nette"), "pct"), badges.get("marge_nette"), "marge_nette", None),
        ("ROE", _fv(rent.get("roe"), "pct"), badges.get("roe"), "roe", None),
        ("ROA", _fv(rent.get("roa"), "pct"), None, "roa", None),
        ("Structure financiere", None, None, None, None),
        ("Solvabilite", _fv(struct.get("solvabilite"), "pct"), badges.get("solvabilite"), "solvabilite", None),
        ("Gearing", _fv(struct.get("gearing"), "ratio"), badges.get("gearing"), "gearing", None),
        ("Dette / EBITDA", _fv(struct.get("dettes_ebitda"), "x"), badges.get("dette_ebitda"), "dettes_ebitda", None),
        ("Couverture interets", _fv(struct.get("couverture_interets"), "x"), badges.get("couverture"), "couverture_interets", None),
        ("Liquidite & BFR", None, None, None, None),
        ("Liquidite generale", _fv(liq.get("liquidite_generale"), "ratio"), badges.get("liquidite"), "liquidite_generale", None),
        ("BFR", _fv(liq.get("bfr"), "eur"), badges.get("bfr"), "bfr", None),
        ("BFR (jours CA)", _fv(liq.get("bfr_jours_ca"), "days"), badges.get("bfr"), "bfr_jours_ca", None),
    ]

    # Header
    header = [
        Paragraph("<b>Indicateur</b>", st["Small"]),
        Paragraph("<b>Valeur</b>", st["Small"]),
        Paragraph("<b>Statut</b>", st["Small"]),
        Paragraph("<b>Explication</b>", st["Small"]),
    ]
    table_data = [header]

    section_rows = set()
    for i, (label, value, badge, key, _) in enumerate(rows_def):
        row_idx = i + 1
        if value is None:
            # Section separator row
            table_data.append([
                Paragraph(f'<b><font color="#00c896">{label}</font></b>', st["Small"]),
                "", "", "",
            ])
            section_rows.add(row_idx)
            continue

        # Badge
        badge_text = ""
        if badge and badge.get("badge"):
            bl = badge.get("label", _badge_label(badge["badge"]))
            bc = _badge_color(badge["badge"])
            badge_text = f'<font color="{bc}"><b>{bl}</b></font>'
            if badge.get("benchmark"):
                badge_text += f'<br/><font size="6" color="#999">{badge["benchmark"]}</font>'

        # Explanation
        explain = RATIO_EXPLAIN.get(key, "")

        table_data.append([
            Paragraph(f"<b>{label}</b>", st["Body"]),
            Paragraph(f"<b>{value}</b>", st["Body"]),
            Paragraph(badge_text, st["Small"]),
            Paragraph(f'<i><font color="#6b7280">{explain}</font></i>', st["Small"]),
        ])

    col_w = [100, 70, 85, CONTENT_W - 100 - 70 - 85]
    t = Table(table_data, colWidths=col_w, repeatRows=1)
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0fdf8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), DARK),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, GRAY_LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]
    # Section separator styling
    for r in section_rows:
        cmds.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#f8fafc")))
        cmds.append(("SPAN", (0, r), (-1, r)))
        cmds.append(("TOPPADDING", (0, r), (-1, r), 8))
        cmds.append(("BOTTOMPADDING", (0, r), (-1, r), 3))
    # Alternating rows (skip section headers)
    data_idx = 0
    for i in range(1, len(table_data)):
        if i not in section_rows:
            data_idx += 1
            if data_idx % 2 == 0:
                cmds.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#fafafa")))

    t.setStyle(TableStyle(cmds))
    return t


# ── Valuation detail table ─────────────────────────────────────────────────
# ── Chiffres cles multi-annees ─────────────────────────────────────────────
def _chiffres_cles(data, st):
    """Build a multi-year key figures table from exercices data."""
    exercices = data.get("exercices", [])
    if len(exercices) < 2:
        return [Paragraph(
            '<i><font color="#6b7280">Donnees insuffisantes pour une vue multi-annuelle.</font></i>',
            st["Body"],
        )]

    exercices_sorted = sorted(exercices, key=lambda e: e.get("annee", 0))
    years = [e.get("annee") for e in exercices_sorted]
    last_year = years[-1]

    # Also grab raw comptes for N and N-1 (CA, resultat_net not in ratios)
    comptes_n = data.get("comptes", {})
    comptes_n1 = data.get("comptes_precedent", {})
    annee_n = data.get("annee")
    annee_n1 = data.get("annee_precedente")

    def _get_comptes(ex):
        """Get raw comptes for an exercice if available."""
        a = ex.get("annee")
        if a == annee_n:
            return comptes_n
        if a == annee_n1:
            return comptes_n1
        return {}

    def _fe(v):
        if v is None or v == 0:
            return "\u2014"
        return f"{round(v):,}\u202f\u20ac".replace(",", "\u202f")

    def _fp(v):
        if v is None:
            return "\u2014"
        return f"{v * 100:.1f}%".replace(".", ",")

    def _dash():
        return "\u2014"

    # Build rows
    row_defs = []

    # 1. CA (comptes bruts → fallback EBITDA/marge)
    ca_vals = []
    for ex in exercices_sorted:
        c = _get_comptes(ex)
        ca = c.get("chiffre_affaires") or c.get("marge_brute")
        if not ca:
            ebitda = ex.get("ebitda", 0)
            me = (ex.get("ratios", {}).get("rentabilite", {}).get("marge_ebitda"))
            if ebitda and me and me > 0:
                ca = round(ebitda / me)
        ca_vals.append(ca or 0)
    row_defs.append(("Chiffre d'affaires", [_fe(v) if v else _dash() for v in ca_vals]))

    # 2. Croissance CA
    growth = [_dash()]
    for i in range(1, len(ca_vals)):
        if ca_vals[i - 1] and ca_vals[i - 1] > 0 and ca_vals[i]:
            g = (ca_vals[i] - ca_vals[i - 1]) / ca_vals[i - 1]
            growth.append(_fp(g))
        else:
            growth.append(_dash())
    row_defs.append(("Croissance CA", growth))

    # 3. EBITDA
    row_defs.append(("EBITDA", [_fe(ex.get("ebitda")) for ex in exercices_sorted]))

    # 4. Marge EBITDA
    row_defs.append(("Marge EBITDA", [
        _fp(ex.get("ratios", {}).get("rentabilite", {}).get("marge_ebitda"))
        for ex in exercices_sorted
    ]))

    # 5. Resultat net (comptes bruts → fallback ROE × capitaux propres)
    rn_vals = []
    for ex in exercices_sorted:
        c = _get_comptes(ex)
        rn = c.get("resultat_net")
        if not rn:
            roe = ex.get("ratios", {}).get("rentabilite", {}).get("roe")
            fp = ex.get("ratios", {}).get("valorisation", {}).get("valeur_capitaux_propres")
            if roe and fp:
                rn = round(roe * fp)
        rn_vals.append(rn or 0)
    row_defs.append(("Resultat net", [_fe(v) if v else _dash() for v in rn_vals]))

    # 6. Marge nette
    row_defs.append(("Marge nette", [
        _fp(ex.get("ratios", {}).get("rentabilite", {}).get("marge_nette"))
        for ex in exercices_sorted
    ]))

    # 7. Capitaux propres
    row_defs.append(("Capitaux propres", [
        _fe(ex.get("ratios", {}).get("valorisation", {}).get("valeur_capitaux_propres"))
        for ex in exercices_sorted
    ]))

    # 8. ETP (optional)
    etp_vals = [ex.get("productivite", {}) or {} for ex in exercices_sorted]
    has_etp = any(p.get("etp") for p in etp_vals)
    if has_etp:
        row_defs.append(("Effectif (ETP)", [
            str(round(p["etp"], 1)) if p.get("etp") else _dash() for p in etp_vals
        ]))
        row_defs.append(("EBITDA / ETP", [
            _fe(p.get("ebitda_par_etp")) if p.get("ebitda_par_etp") else _dash() for p in etp_vals
        ]))

    # Build table
    nb_years = len(years)
    label_w = 110
    year_w = (CONTENT_W - label_w) / nb_years
    col_widths = [label_w] + [year_w] * nb_years

    HEADER_BG = colors.HexColor("#1E3A5F")

    # Header row
    header = [Paragraph("", st["Small"])]
    for y in years:
        header.append(Paragraph(f'<font color="white"><b>{y}</b></font>', st["Small"]))
    table_data = [header]

    # Data rows
    for label, vals in row_defs:
        row = [Paragraph(label, st["Body"])]
        for i, v in enumerate(vals):
            is_last = (years[i] == last_year)
            row.append(Paragraph(f'<b>{v}</b>' if is_last else v, st["Body"]))
        table_data.append(row)

    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, GRAY_LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    # Zebra rows
    for i in range(2, len(table_data), 2):
        cmds.append(("BACKGROUND", (0, i), (-1, i), GRAY_LIGHT))

    t.setStyle(TableStyle(cmds))
    return [t]


# ── Fiches par exercice ────────────────────────────────────────────────────
def _fiches_exercices(data, st):
    """One compact card per exercise year."""
    exercices = data.get("exercices", [])
    if len(exercices) < 2:
        return []

    exercices_sorted = sorted(exercices, key=lambda e: e.get("annee", 0))
    last_year = exercices_sorted[-1].get("annee")
    els = []
    els.append(PageBreak())
    els.extend(_section("Analyse par exercice", st,
                        "Fiche synthetique de chaque annee analysee"))

    HEADER_BG = colors.HexColor("#1E3A5F")

    for i, ex in enumerate(exercices_sorted):
        annee = ex.get("annee", "?")
        ebitda = ex.get("ebitda", 0)
        rent = ex.get("ratios", {}).get("rentabilite", {})
        struct = ex.get("ratios", {}).get("structure", {})
        liq = ex.get("ratios", {}).get("liquidite", {})
        valo_ex = ex.get("ratios", {}).get("valorisation", {})
        prod = ex.get("productivite") or {}

        # CA fallback
        me = rent.get("marge_ebitda")
        ca = round(ebitda / me) if ebitda and me and me > 0 else None

        # RN fallback
        roe = rent.get("roe")
        fp = valo_ex.get("valeur_capitaux_propres")
        rn = round(roe * fp) if roe and fp else None

        # Delta CA
        delta_ca_str = "\u2014"
        if i > 0 and ca:
            prev = exercices_sorted[i - 1]
            prev_ebitda = prev.get("ebitda", 0)
            prev_me = prev.get("ratios", {}).get("rentabilite", {}).get("marge_ebitda")
            prev_ca = round(prev_ebitda / prev_me) if prev_ebitda and prev_me and prev_me > 0 else None
            if prev_ca and prev_ca > 0:
                delta = (ca - prev_ca) / prev_ca * 100
                sign = "+" if delta >= 0 else ""
                delta_ca_str = f"{sign}{delta:.1f}%".replace(".", ",")

        def _v(val, fmt="eur"):
            if val is None:
                return "\u2014"
            if fmt == "eur":
                return _fmt_eur(val)
            if fmt == "pct":
                return _fmt_pct(val)
            if fmt == "ratio":
                return f"{val:.2f}"
            if fmt == "x":
                return f"{val:.1f}x"
            if fmt == "days":
                return f"{int(val)}j"
            return str(val)

        rows_data = [
            ("Chiffre d'affaires", _v(ca)),
            ("Croissance CA", delta_ca_str),
            ("EBITDA", _v(ebitda)),
            ("Marge EBITDA", _v(me, "pct")),
            ("Resultat net", _v(rn)),
            ("Marge nette", _v(rent.get("marge_nette"), "pct")),
            ("ROE", _v(roe, "pct")),
            ("Gearing", _v(struct.get("gearing"), "ratio")),
            ("BFR (jours CA)", _v(liq.get("bfr_jours_ca"), "days")),
        ]
        if prod.get("etp"):
            rows_data.append(("Effectif (ETP)", str(round(prod["etp"], 1))))

        # Title banner
        ref = " (exercice de reference)" if annee == last_year else ""
        title = Paragraph(
            f'<font color="white"><b>Exercice {annee}{ref}</b></font>', st["Body"])
        title_t = Table([[title]], colWidths=[CONTENT_W - 8])
        title_t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), HEADER_BG),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("ROUNDEDCORNERS", [4, 4, 0, 0]),
        ]))

        # Data table
        table_rows = []
        for label, val in rows_data:
            table_rows.append([
                Paragraph(label, st["Body"]),
                Paragraph(f"<b>{val}</b>", st["Body"]),
            ])
        dt = Table(table_rows, colWidths=[CONTENT_W * 0.5 - 4, CONTENT_W * 0.5 - 4])
        cmds = [
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, GRAY_LINE),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]
        for j in range(1, len(table_rows), 2):
            cmds.append(("BACKGROUND", (0, j), (-1, j), GRAY_LIGHT))
        dt.setStyle(TableStyle(cmds))

        els.append(KeepTogether([title_t, dt]))
        els.append(Spacer(1, 14))

    return els


def _valo_detail(valo, st):
    items = [
        ("EBITDA pondere", _fmt_eur(valo.get("ebitda_reference")),
         "Base de calcul ponderee selon le nombre d'exercices"),
        ("Multiple sectoriel", f"{valo.get('multiple_sectoriel', 'N/A')}x",
         "Multiple EV/EBITDA median du secteur"),
        ("Valeur EV/EBITDA", _fmt_eur(valo.get("ev_ebitda")),
         "EBITDA x multiple = valeur d'entreprise"),
        ("DCF (equity)", _fmt_eur(valo.get("dcf")) if valo.get("dcf") else "Non calculable",
         "Projection des flux de tresorerie actualises"),
        ("Actif net comptable", _fmt_eur(valo.get("actif_net")),
         "Capitaux propres = plancher de valorisation"),
    ]
    header = [
        Paragraph("<b>Methode</b>", st["Small"]),
        Paragraph("<b>Montant</b>", st["Small"]),
        Paragraph("<b>Description</b>", st["Small"]),
    ]
    rows = [header]
    for label, val, desc in items:
        rows.append([
            Paragraph(label, st["Body"]),
            Paragraph(f"<b>{val}</b>", st["Body"]),
            Paragraph(f'<font color="#6b7280"><i>{desc}</i></font>', st["Small"]),
        ])
    t = Table(rows, colWidths=[110, 100, CONTENT_W - 210 - 12])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GRAY_LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, GRAY_LINE),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


# ── EBITDA pondere breakdown ───────────────────────────────────────────────
def _ebitda_breakdown(valo, st):
    detail = valo.get("ebitda_pondere_detail", [])
    if not detail or len(detail) < 2:
        return None
    header = [
        Paragraph("<b>Annee</b>", st["Small"]),
        Paragraph("<b>EBITDA</b>", st["Small"]),
        Paragraph("<b>Poids</b>", st["Small"]),
        Paragraph("<b>Contribution</b>", st["Small"]),
    ]
    rows = [header]
    for d in detail:
        pct = d.get("poids_pct", int(d.get("poids", 0) * 100))
        rows.append([
            Paragraph(str(d["annee"]), st["Small"]),
            Paragraph(_fmt_eur(d["ebitda"]), st["Small"]),
            Paragraph(f"{pct}%", st["Small"]),
            Paragraph(f"<b>{_fmt_eur(d['contribution'])}</b>", st["Small"]),
        ])
    t = Table(rows, colWidths=[55, 95, 45, 95])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GRAY_LIGHT),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, GRAY_LINE),
    ]))
    return t


# ── Diagnostic lists ──────────────────────────────────────────────────────
def _diag_block(title, items, color_hex, icon, st):
    if not items:
        return []
    els = [Paragraph(f'<font color="{color_hex}"><b>{icon} {title}</b></font>', st["DiagTitle"])]
    for item in items:
        els.append(Paragraph(f'<font color="#374151">\u2022 {item}</font>', st["BWIXBullet"]))
    els.append(Spacer(1, 8))
    return els


# ── Productivity ──────────────────────────────────────────────────────────
def _productivity(prod, st):
    if not prod or not prod.get("etp") or prod["etp"] <= 0:
        return []
    els = list(_section(f"Productivite par employe \u2014 {prod['etp']} ETP", st,
                        "Performance rapportee a l'effectif moyen"))
    items = [
        ("EBITDA / ETP", _fmt_eur(prod.get("ebitda_par_etp")),
         "Cash operationnel genere par employe"),
        ("Marge brute / ETP", _fmt_eur(prod.get("marge_par_etp")),
         "Valeur ajoutee par employe"),
    ]
    if prod.get("ca_par_etp"):
        items.append(("CA / ETP", _fmt_eur(prod["ca_par_etp"]),
                       "Chiffre d'affaires par employe"))
    rows = []
    for label, val, desc in items:
        rows.append([
            Paragraph(label, st["Body"]),
            Paragraph(f"<b>{val}</b>", st["Body"]),
            Paragraph(f'<i><font color="#6b7280">{desc}</font></i>', st["Small"]),
        ])
    t = Table(rows, colWidths=[110, 100, CONTENT_W - 210 - 12])
    t.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, GRAY_LINE),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    els.append(t)
    if prod.get("benchmark"):
        els.append(Spacer(1, 3))
        els.append(Paragraph(f'<i>{prod["benchmark"]}</i>', st["SmallItalic"]))
    return els


# ── Evolution N vs N-1 ────────────────────────────────────────────────────
def _evolution(data, st):
    exercices = data.get("exercices", [])
    if len(exercices) < 2:
        return []
    prev, curr = exercices[-2], exercices[-1]
    prev_r = prev.get("ratios", {}).get("rentabilite", {})
    curr_r = curr.get("ratios", {}).get("rentabilite", {})
    evo_rows = []
    for label, key in [("EBITDA", "ebitda"), ("ROE", "roe"), ("Marge EBITDA", "marge_ebitda")]:
        vp, vc = prev_r.get(key), curr_r.get(key)
        if vp is not None and vc is not None:
            fmt = _fmt_eur if key == "ebitda" else _fmt_pct
            if vc > vp:
                arrow = '<font color="#00c896">\u2191</font>'
            elif vc < vp:
                arrow = '<font color="#ef4444">\u2193</font>'
            else:
                arrow = '\u2192'
            evo_rows.append([
                Paragraph(label, st["Body"]),
                Paragraph(fmt(vp), st["Body"]),
                Paragraph(arrow, st["Body"]),
                Paragraph(f"<b>{fmt(vc)}</b>", st["Body"]),
            ])
    if not evo_rows:
        return []
    ap, ac = prev.get("annee", "N-1"), curr.get("annee", "N")
    header = [
        Paragraph("<b>Indicateur</b>", st["Small"]),
        Paragraph(f"<b>{ap}</b>", st["Small"]),
        Paragraph("", st["Small"]),
        Paragraph(f"<b>{ac}</b>", st["Small"]),
    ]
    t = Table([header] + evo_rows, colWidths=[110, 100, 30, 100])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GRAY_LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("ALIGN", (3, 0), (3, -1), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, GRAY_LINE),
    ]))
    return [Spacer(1, 8), Paragraph("<b>Evolution N vs N-1</b>", st["BodyBold"]), Spacer(1, 4), t]


# ══════════════════════════════════════════════════════════════════════════
#  MAIN GENERATION
# ══════════════════════════════════════════════════════════════════════════
def generate_pdf(data: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=16 * mm, bottomMargin=20 * mm,
    )
    st = _styles()
    els = []

    now = datetime.now()
    date_str = now.strftime("%d/%m/%Y")
    denomination = data.get("denomination", "Societe")
    annees = data.get("annees_disponibles", [data.get("annee")])
    annees_clean = [a for a in annees if a]
    annees_str = "-".join(str(a) for a in annees_clean) if annees_clean else ""
    score = data.get("score_sante", 50)
    valo = data.get("valorisation", {})
    ai = data.get("ai_analysis", {})
    prod = data.get("productivite")
    secteur = data.get("secteur", "")

    # ── PAGE 1 : Cover + Fiche + Fiabilite + Score + Valorisation ────
    els.append(Spacer(1, 6))
    els.append(Paragraph("Rapport d'analyse financiere", st["Title1"]))
    els.append(Spacer(1, 6))

    # Fiche d'identite
    els.extend(_fiche_identite(data, st))
    els.append(Spacer(1, 10))

    # Bandeau fiabilite
    els.append(_fiabilite_bandeau(data, st))
    els.append(Spacer(1, 14))

    # Score card
    sc_hex = _score_color_hex(score)
    sc_label = _score_label(score)
    score_left = [
        Paragraph(f'<font size="28" color="{sc_hex}"><b>{score}</b></font>'
                  f'<font size="10" color="#999"> /100</font>', st["Body"]),
        Spacer(1, 16),
        Paragraph(f'<font size="8" color="{sc_hex}"><b>{sc_label}</b></font>', st["Body"]),
    ]
    score_right = []
    score_right.append(Paragraph("<b>Score sante</b>", st["Body"]))
    score_right.append(Paragraph(
        "Score composite base sur la rentabilite, la structure financiere, "
        "la liquidite et les risques detectes. Calcule par interpolation lineaire "
        "sur les seuils sectoriels.", st["Small"]))

    score_t = Table([[score_left, score_right]], colWidths=[CONTENT_W * 0.35, CONTENT_W * 0.65])
    score_t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (0, 0), 12),
        ("LEFTPADDING", (1, 0), (1, 0), 16),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fffe")),
        ("BOX", (0, 0), (-1, -1), 1, BWIX),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    els.append(score_t)
    els.append(Spacer(1, 16))

    # Valorisation
    els.extend(_section("Valorisation de l'entreprise", st))
    low = valo.get('fourchette_basse')
    high = valo.get('fourchette_haute')
    central = round((low + high) / 2) if low and high else None
    els.append(Paragraph('<font size="8" color="#6b7280">Valeur estimee</font>', st["CenterSm"]))
    els.append(Paragraph(f'<font size="20" color="#00c896"><b>{_fmt_eur(central)}</b></font>', st["Center"]))
    els.append(Spacer(1, 4))
    fourchette = f"Fourchette : {_fmt_eur(low)}  \u2014  {_fmt_eur(high)}"
    els.append(Paragraph(fourchette, st["CenterSm"]))
    methode = valo.get("fourchette_methode", "")
    if methode:
        els.append(Paragraph(methode, st["CenterSm"]))
    els.append(Spacer(1, 12))
    els.append(_valo_detail(valo, st))

    # EBITDA breakdown
    ebd = _ebitda_breakdown(valo, st)
    if ebd:
        els.append(Spacer(1, 8))
        els.append(Paragraph("<b>Detail EBITDA pondere</b>", st["Small"]))
        els.append(Spacer(1, 3))
        els.append(ebd)

    # Synthese executive
    se = data.get("synthese_executive")
    if se:
        els.append(Spacer(1, 12))
        els.extend(_section("Synthese", st))
        els.append(Paragraph(se, st["Body"]))

    # ── PAGE 2 : Chiffres cles ───────────────────────────────────────
    els.append(PageBreak())
    els.extend(_section("Chiffres cles", st,
                        "Vue synthetique multi-annuelle des indicateurs principaux"))
    els.extend(_chiffres_cles(data, st))

    # ── PAGE 3 : Ratios ────────────────────────────────────────────────
    els.append(PageBreak())
    els.extend(_section("Ratios financiers", st,
                        "Chaque ratio est compare aux benchmarks sectoriels. "
                        "Les explications aident a interpreter les valeurs."))
    els.append(_ratio_table(data, st))

    # Evolution
    evo_els = _evolution(data, st)
    if evo_els:
        els.extend(evo_els)

    # Productivity
    prod_els = _productivity(prod, st)
    if prod_els:
        els.append(Spacer(1, 6))
        els.extend(prod_els)

    # ── PAGE 4 : Diagnostic ────────────────────────────────────────────
    els.append(PageBreak())
    els.extend(_section("Diagnostic financier", st,
                        "Analyse generee par intelligence artificielle a partir des donnees comptables"))

    # New 4-bloc format
    blocs = ai.get("diagnostic_blocs", [])
    bloc_colors = ["#00c896", "#3b82f6", "#f59e0b", "#8b5cf6"]
    bloc_icons = ["\u2714", "\u2261", "\u21c4", "\u2197"]

    if blocs:
        for i, bloc in enumerate(blocs):
            color = bloc_colors[i] if i < len(bloc_colors) else "#6b7280"
            icon = bloc_icons[i] if i < len(bloc_icons) else "\u2022"
            els.append(Paragraph(
                f'<font color="{color}"><b>{icon} {bloc.get("title", "")}</b></font>',
                st["DiagTitle"],
            ))
            for line in bloc.get("lines", []):
                # Bold the prefix (Constat/Evolution/Impact/Piste)
                prefix_end = line.find(':')
                if prefix_end > 0 and prefix_end < 12:
                    prefix = line[:prefix_end + 1]
                    rest = line[prefix_end + 1:]
                    els.append(Paragraph(f'<b>{prefix}</b>{rest}', st["Body"]))
                else:
                    els.append(Paragraph(line, st["Body"]))
            els.append(Spacer(1, 10))
    else:
        # Fallback: old format or raw text
        raw = ai.get("diagnostic_raw", "")
        if raw:
            els.append(Paragraph(raw, st["Body"]))
        else:
            synthese = ai.get("synthese", "")
            if synthese:
                els.append(Paragraph(synthese, st["Body"]))
            els.extend(_diag_block("Points forts", ai.get("points_forts", []), "#00c896", "\u2714", st))
            els.extend(_diag_block("Points d'attention", ai.get("points_attention", []), "#f59e0b", "\u26a0", st))
            els.extend(_diag_block("Risques", ai.get("risques", []), "#ef4444", "\u2716", st))
            els.extend(_diag_block("Recommandations", ai.get("recommandations", []), "#3b82f6", "\u279c", st))

    # ── PAGE 5+ : Fiches par exercice ─────────────────────────────────
    els.extend(_fiches_exercices(data, st))

    # Build
    doc.build(els, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return buf.getvalue()


def generate_pdf_base64(data: dict) -> str:
    pdf_bytes = generate_pdf(data)
    return base64.b64encode(pdf_bytes).decode("utf-8")


def pdf_filename(data: dict) -> str:
    denom = data.get("denomination", "Analyse")
    clean = "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in denom).strip().replace(" ", "_")
    annees = data.get("annees_disponibles", [data.get("annee")])
    annees_clean = [a for a in annees if a]
    if len(annees_clean) >= 2:
        annee_str = f"{annees_clean[0]}-{annees_clean[-1]}"
    elif annees_clean:
        annee_str = str(annees_clean[0])
    else:
        annee_str = ""
    return f"BWIX_{clean}_{annee_str}.pdf"
