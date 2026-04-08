"""BNB PDF extraction — adapted from AppCptResultat/app.py."""

import re


def extract_bnb_pdf(pdf_path: str) -> dict:
    """Extract financial data (N and N-1) from BNB annual accounts PDF."""
    import pdfplumber

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

    def parse_bnb_amount(text):
        if not text:
            return None
        text = text.strip()
        negative = text.startswith('-')
        if negative:
            text = text[1:]
        text = text.replace('.', '')
        if not text:
            return None
        try:
            val = int(text)
            return -val if negative else val
        except ValueError:
            return None

    data_n = dict(EMPTY_DATA)
    data_n1 = dict(EMPTY_DATA)
    annee_exercice = None
    annee_precedente = None

    with pdfplumber.open(pdf_path) as pdf:
        page1_text = pdf.pages[0].extract_text() or ''

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

                    # Match BNB amounts after the code.
                    # BNB format: dots as thousands sep (520.980) OR plain integers (904, 85, 0)
                    # After the code position, everything is amounts — safe to be permissive.
                    amounts = re.findall(r'-?(?:\d{1,3}(?:\.\d{3})+|\b\d+\b)', after_code)

                    if not amounts:
                        break

                    val_n = parse_bnb_amount(amounts[0])
                    val_n1 = parse_bnb_amount(amounts[1]) if len(amounts) > 1 else None

                    if val_n is not None and key not in seen_n:
                        data_n[key] = val_n
                        seen_n.add(key)
                    if val_n1 is not None and key not in seen_n1:
                        data_n1[key] = val_n1
                        seen_n1.add(key)

                    break

    # Post-processing
    for data in (data_n, data_n1):
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

    return {
        'exercice': data_n,
        'exercice_precedent': data_n1,
        'annee_exercice': annee_exercice,
        'annee_precedente': annee_precedente,
    }


def detect_consolidated(pdf_path: str) -> bool:
    """Check if a PDF contains consolidated accounts keywords."""
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[:3]:
            text = (page.extract_text() or '').lower()
            if 'consolidé' in text or 'geconsolideerd' in text:
                return True
    return False
