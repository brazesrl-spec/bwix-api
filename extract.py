"""PDF extraction — BNB official + BOB multi-exercices."""

import re


# ── Shared code map ────────────────────────────────────────────────────────
CODE_MAP = {
    '21/28': 'actifs_immobilises',
    '29/58': 'actifs_circulants',
    '30/36': 'stocks', '30/37': 'stocks', '3': 'stocks',
    '40/41': 'creances_court_terme',
    '54/58': 'tresorerie',
    '50/53': 'placements_tresorerie',
    '20/58': 'total_actif',
    '22/27': 'immo_corporelles',
    '22': 'immo_terrains_constructions',
    '23': 'immo_installations_machines',
    '24': 'immo_mobilier_roulant',
    '28': 'immo_financieres',
    '40': 'creances_commerciales',
    '41': 'autres_creances',
    '490/1': 'comptes_regularisation_actif',
    '10/15': 'capitaux_propres',
    '17': 'dettes_long_terme',
    '42/48': 'dettes_court_terme',
    '10/49': 'total_passif',
    '17/49': 'total_dettes',
    '170/4': 'dettes_financieres_lt',
    '172/3': 'dettes_credit_lt',
    '174/0': 'autres_emprunts_lt',
    '42': 'dettes_lt_echeant_annee',
    '43': 'dettes_financieres_ct',
    '430/8': 'dettes_credit_ct',
    '44': 'dettes_commerciales',
    '440/4': 'fournisseurs',
    '46': 'acomptes_commandes',
    '45': 'dettes_fiscales_sociales',
    '450/3': 'dettes_fiscales',
    '454/9': 'dettes_sociales',
    '47/48': 'autres_dettes',
    '492/3': 'comptes_regularisation_passif',
    '9900': 'marge_brute',
    '70': 'chiffre_affaires',
    '60/61': 'achats_services',
    '62': 'remunerations',
    '630': 'amortissements',
    '640/8': 'autres_charges',
    '9901': 'resultat_exploitation',
    '75/76B': 'produits_financiers',
    '65/66B': 'charges_financieres',
    '65': 'charges_financieres_recurrentes',
    '9903': 'resultat_avant_impots',
    '67/77': 'impots',
    '9904': 'resultat_net',
    '9905': 'resultat_net_a_affecter',
    '9087': 'etp_moyen',
}

ALL_CODES = sorted(CODE_MAP.keys(), key=lambda c: -len(c))

EMPTY_DATA = {
    'actifs_immobilises': 0, 'actifs_circulants': 0,
    'stocks': 0, 'creances_court_terme': 0, 'tresorerie': 0,
    'total_actif': 0, 'capitaux_propres': 0,
    'dettes_long_terme': 0, 'dettes_court_terme': 0, 'total_passif': 0,
    'chiffre_affaires': 0, 'marge_brute': 0,
    'achats_services': 0, 'remunerations': 0,
    'amortissements': 0, 'autres_charges': 0, 'resultat_exploitation': 0,
    'charges_financieres': 0, 'resultat_avant_impots': 0,
    'impots': 0, 'resultat_net': 0,
}


def _parse_amount(text):
    """Parse BNB/BOB amounts. Handles:
    - BNB: "520.980" (dots = thousands) → 520980
    - BOB: "2.698.418,25" (dots = thousands, comma = decimals) → 2698418
    - Plain: "274391" → 274391
    """
    if not text:
        return None
    text = text.strip().replace('\u202f', '').replace('\xa0', '')
    negative = text.startswith('-')
    if negative:
        text = text[1:]
    # Strip decimal part (,XX) — bilans are in whole euros
    if ',' in text:
        text = text.split(',')[0]
    # Remove thousands separators (dots)
    text = text.replace('.', '')
    if not text:
        return None
    try:
        val = int(text)
        return -val if negative else val
    except ValueError:
        return None


# Regex for amounts: European format (1.234.567,89) or plain integers
_AMOUNT_RE = r'-?(?:\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:,\d{1,2})?)'


def _postprocess(data):
    """Post-processing shared by BNB and BOB parsers."""
    if not data.get('actifs_circulants'):
        data['actifs_circulants'] = (
            data.get('stocks', 0) + data.get('creances_court_terme', 0) + data.get('tresorerie', 0)
        )
    if not data.get('chiffre_affaires') and data.get('marge_brute'):
        data['chiffre_affaires'] = data['marge_brute']
        data['_ca_is_marge_brute'] = True
    if not data.get('charges_financieres') and data.get('charges_financieres_recurrentes'):
        data['charges_financieres'] = data['charges_financieres_recurrentes']
    if not data.get('resultat_net') and data.get('resultat_net_a_affecter'):
        data['resultat_net'] = data['resultat_net_a_affecter']

    dette_bancaire_lt = data.get('dettes_credit_lt', 0) or data.get('dettes_financieres_lt', 0) or 0
    dette_bancaire_ct = (data.get('dettes_credit_ct', 0) or 0) + (data.get('dettes_lt_echeant_annee', 0) or 0)
    tresorerie_totale = (data.get('tresorerie', 0) or 0) + (data.get('placements_tresorerie', 0) or 0)
    data['dette_bancaire_lt'] = dette_bancaire_lt
    data['dette_bancaire_ct'] = dette_bancaire_ct
    data['dette_nette_bancaire'] = dette_bancaire_lt + dette_bancaire_ct - tresorerie_totale


# ── Format detection ───────────────────────────────────────────────────────

def detect_format(pdf_path: str) -> str:
    """Detect PDF format: BNB_OFFICIEL, BOB_MULTI_EXERCICES, or UNKNOWN."""
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages[:5]:
            full_text += (page.extract_text() or '') + '\n'

    lower = full_text.lower()

    # BOB detection: look for **/20XX column headers or "bob" mention
    bob_years = re.findall(r'\*\*/\s*(20\d{2})', full_text)
    if not bob_years:
        # Also try bare year columns like "2024  2023  2022"
        bob_years = re.findall(r'\b(20\d{2})\b', full_text)
        # Only consider BOB if 3+ distinct years found AND no BNB markers
        bob_years_unique = sorted(set(int(y) for y in bob_years))
        has_bnb_markers = ('schéma complet' in lower or 'schema complet' in lower
                           or 'schéma abrégé' in lower or 'schema abrege' in lower
                           or 'banque nationale' in lower or 'bnb' in lower
                           or 'période du' in lower or 'periode du' in lower)
        has_bob_markers = ('bob' in lower or 'sage bob' in lower
                           or 'bob software' in lower or 'bob50' in lower)

        if has_bnb_markers:
            return "BNB_OFFICIEL"
        if has_bob_markers and len(bob_years_unique) >= 2:
            return "BOB_MULTI_EXERCICES"
        # 3+ year columns without BNB markers → likely BOB/accounting software
        if len(bob_years_unique) >= 3 and not has_bnb_markers:
            return "BOB_MULTI_EXERCICES"
        return "BNB_OFFICIEL"  # fallback to BNB parser

    # Explicit **/20XX headers → BOB
    return "BOB_MULTI_EXERCICES"


# ── BNB parser (existing) ─────────────────────────────────────────────────

def extract_bnb_pdf(pdf_path: str) -> dict:
    """Extract financial data (N and N-1) from BNB annual accounts PDF."""
    import pdfplumber

    data_n = dict(EMPTY_DATA)
    data_n1 = dict(EMPTY_DATA)
    annee_exercice = None
    annee_precedente = None
    denomination = None

    with pdfplumber.open(pdf_path) as pdf:
        page1_text = pdf.pages[0].extract_text() or ''

        # Extract company name
        m_denom = re.search(r'[Dd]\u00e9nomination\s*:\s*(.+)', page1_text)
        if m_denom:
            denomination = m_denom.group(1).strip()
            for cut in ['Forme juridique', 'Adresse']:
                if cut in denomination:
                    denomination = denomination[:denomination.index(cut)].strip()

        m = re.search(
            r'p[ée]riode\s+du\s+\d{2}-\d{2}-(\d{4})\s+au\s+\d{2}-\d{2}-(\d{4})',
            page1_text)
        if m:
            annee_exercice = int(m.group(2))

        m3 = re.search(
            r'exercice\s+pr[ée]c[ée]dent.*?au\s+\d{2}-\d{2}-(\d{4})',
            page1_text)
        if m3:
            annee_precedente = int(m3.group(1))
        elif annee_exercice:
            annee_precedente = annee_exercice - 1

        seen_n = set()
        seen_n1 = set()

        for page in pdf.pages:
            text = page.extract_text() or ''
            for line in text.split('\n'):
                line = line.strip()
                if not line or line.startswith('Page ') or line.startswith('N° '):
                    continue

                for code in ALL_CODES:
                    pattern = r'(?:^|\s)' + re.escape(code) + r'(?:\s|$)'
                    m = re.search(pattern, line)
                    if not m:
                        continue

                    key = CODE_MAP[code]
                    after_code = line[m.end():].strip()
                    amounts = re.findall(_AMOUNT_RE, after_code)

                    if not amounts:
                        break

                    val_n = _parse_amount(amounts[0])
                    val_n1 = _parse_amount(amounts[1]) if len(amounts) > 1 else None

                    if val_n is not None and key not in seen_n:
                        data_n[key] = val_n
                        seen_n.add(key)
                    if val_n1 is not None and key not in seen_n1:
                        data_n1[key] = val_n1
                        seen_n1.add(key)

                    break

    _postprocess(data_n)
    _postprocess(data_n1)

    return {
        'exercice': data_n,
        'exercice_precedent': data_n1,
        'annee_exercice': annee_exercice,
        'annee_precedente': annee_precedente,
        'denomination': denomination,
        'format': 'BNB_OFFICIEL',
    }


# ── BOB multi-exercices parser ────────────────────────────────────────────

def extract_bob_pdf(pdf_path: str) -> dict:
    """Extract financial data from BOB-style PDF with 2-5 year columns."""
    import pdfplumber

    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        all_lines = []
        for page in pdf.pages:
            text = page.extract_text() or ''
            full_text += text + '\n'
            all_lines.extend(text.split('\n'))

    # ── Detect year columns ────────────────────────────────────────────
    # Look for **/20XX patterns first
    star_years = re.findall(r'\*\*/\s*(20\d{2})', full_text)
    if star_years:
        years = sorted(set(int(y) for y in star_years), reverse=True)
    else:
        # Fallback: find header lines with multiple consecutive years
        years = []
        for line in all_lines[:30]:
            found = re.findall(r'\b(20\d{2})\b', line)
            if len(found) >= 2:
                years = sorted(set(int(y) for y in found), reverse=True)
                break
        if not years:
            # Last resort: collect all 20XX from first pages
            all_years = re.findall(r'\b(20\d{2})\b', full_text[:3000])
            years = sorted(set(int(y) for y in all_years), reverse=True)[:5]

    if not years:
        return {'exercice': {'error': 'Aucune annee detectee dans le document BOB.'}}

    nb_cols = len(years)

    # ── Extract company name ───────────────────────────────────────────
    denomination = None
    for line in all_lines[:15]:
        line_clean = line.strip()
        # Skip lines that look like headers, dates, codes
        if not line_clean or re.match(r'^(20\d{2}|Page|\d{2}/\d{2}|N°|Code|\*\*)', line_clean):
            continue
        if len(line_clean) > 5 and not re.match(r'^\d', line_clean):
            denomination = line_clean
            break

    # ── Parse each code across year columns ────────────────────────────
    year_data = {y: dict(EMPTY_DATA) for y in years}
    year_seen = {y: set() for y in years}

    for line in all_lines:
        line = line.strip()
        if not line:
            continue

        for code in ALL_CODES:
            pattern = r'(?:^|\s)' + re.escape(code) + r'(?:\s|$)'
            m = re.search(pattern, line)
            if not m:
                continue

            key = CODE_MAP[code]
            after_code = line[m.end():].strip()

            # Extract all amounts on the line
            amounts = re.findall(_AMOUNT_RE, after_code)
            if not amounts:
                break

            # Map amounts to year columns (left to right = most recent to oldest)
            for i, year in enumerate(years):
                if i < len(amounts) and key not in year_seen[year]:
                    val = _parse_amount(amounts[i])
                    if val is not None:
                        year_data[year][key] = val
                        year_seen[year].add(key)

            break

    # Post-process all years
    for y in years:
        _postprocess(year_data[y])

    # ── Build return structure ─────────────────────────────────────────
    # Most recent = exercice, second = exercice_precedent
    # Additional years returned in 'exercices_supplementaires'
    sorted_years = sorted(years, reverse=True)
    annee_n = sorted_years[0]
    annee_n1 = sorted_years[1] if len(sorted_years) > 1 else None

    result = {
        'exercice': year_data[annee_n],
        'exercice_precedent': year_data[annee_n1] if annee_n1 else dict(EMPTY_DATA),
        'annee_exercice': annee_n,
        'annee_precedente': annee_n1,
        'denomination': denomination,
        'format': 'BOB_MULTI_EXERCICES',
    }

    # Additional years beyond the first two
    if len(sorted_years) > 2:
        extras = []
        for y in sorted_years[2:]:
            extras.append({
                'annee': y,
                'comptes': year_data[y],
            })
        result['exercices_supplementaires'] = extras

    return result


# ── Unified extraction entry point ────────────────────────────────────────

def extract_pdf(pdf_path: str) -> dict:
    """Auto-detect format and extract financial data."""
    fmt = detect_format(pdf_path)
    if fmt == "BOB_MULTI_EXERCICES":
        return extract_bob_pdf(pdf_path)
    return extract_bnb_pdf(pdf_path)


# ── Consolidated detection ─────────────────────────────────────────────────

def detect_consolidated(pdf_path: str) -> bool:
    """Check if a PDF contains consolidated accounts keywords."""
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[:3]:
            text = (page.extract_text() or '').lower()
            if 'consolidé' in text or 'geconsolideerd' in text:
                return True
    return False
