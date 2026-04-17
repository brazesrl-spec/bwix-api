"""Financial ratios & valuation — adapted from AppCptResultat/database.py."""

SECTEUR_MULTIPLES = {
    'Construction / BTP': {'low': 4, 'high': 6, 'default': 5},
    'Tech / SaaS':        {'low': 8, 'high': 15, 'default': 10},
    'Services':           {'low': 5, 'high': 8, 'default': 6},
    'Commerce':           {'low': 4, 'high': 7, 'default': 5},
    'Industrie':          {'low': 5, 'high': 8, 'default': 6},
    # Structures particulières
    'Management / Holding': {'low': 3, 'high': 6, 'default': 4},
    'Immobilier / SCI':     {'low': 6, 'high': 12, 'default': 8},
    'ASBL':                 {'low': 0, 'high': 0, 'default': 0},
    'Startup':              {'low': 5, 'high': 20, 'default': 8},
}

SECTEUR_BENCHMARKS = {
    'Construction / BTP': {
        'marge_ebitda': (0.08, 0.15), 'marge_nette': (0.03, 0.08),
        'roe': (0.08, 0.20), 'solvabilite': (0.25, 0.45),
        'liquidite_generale': (1.1, 1.8), 'gearing': (0.3, 1.5),
    },
    'Tech / SaaS': {
        'marge_ebitda': (0.15, 0.40), 'marge_nette': (0.08, 0.25),
        'roe': (0.12, 0.30), 'solvabilite': (0.30, 0.60),
        'liquidite_generale': (1.5, 3.0), 'gearing': (0.0, 0.8),
    },
    'Services': {
        'marge_ebitda': (0.10, 0.25), 'marge_nette': (0.05, 0.15),
        'roe': (0.10, 0.25), 'solvabilite': (0.25, 0.50),
        'liquidite_generale': (1.2, 2.0), 'gearing': (0.2, 1.2),
    },
    'Commerce': {
        'marge_ebitda': (0.05, 0.12), 'marge_nette': (0.02, 0.06),
        'roe': (0.08, 0.18), 'solvabilite': (0.20, 0.40),
        'liquidite_generale': (1.0, 1.6), 'gearing': (0.5, 2.0),
    },
    'Industrie': {
        'marge_ebitda': (0.10, 0.20), 'marge_nette': (0.04, 0.10),
        'roe': (0.08, 0.20), 'solvabilite': (0.30, 0.50),
        'liquidite_generale': (1.2, 2.0), 'gearing': (0.3, 1.5),
    },
    # Structures particulières — seuils adaptés
    'Management / Holding': {
        'marge_ebitda': (0.0, 1.0), 'marge_nette': (0.0, 1.0),
        'roe': (0.03, 0.50), 'solvabilite': (0.20, 0.80),
        'liquidite_generale': (0.7, 5.0), 'gearing': (0.0, 3.0),
    },
    'Immobilier / SCI': {
        'marge_ebitda': (0.20, 0.70), 'marge_nette': (0.05, 0.40),
        'roe': (0.03, 0.15), 'solvabilite': (0.15, 0.50),
        'liquidite_generale': (0.7, 2.0), 'gearing': (0.5, 4.0),
    },
    'ASBL': {
        'marge_ebitda': (-0.10, 0.15), 'marge_nette': (-0.10, 0.10),
        'roe': (0.0, 0.10), 'solvabilite': (0.20, 0.70),
        'liquidite_generale': (0.7, 3.0), 'gearing': (0.0, 2.0),
    },
    'Startup': {
        'marge_ebitda': (-0.50, 0.30), 'marge_nette': (-0.50, 0.20),
        'roe': (-0.50, 0.50), 'solvabilite': (0.10, 0.60),
        'liquidite_generale': (0.7, 3.0), 'gearing': (0.0, 3.0),
    },
}

# Sectors where EBITDA volatility is expected (warning instead of malus)
STRUCTURE_PARTICULIERE = {'Management / Holding', 'Immobilier / SCI', 'ASBL', 'Startup'}

# Sector-specific thresholds for badges + valuation multiples
SECTEUR_SEUILS = {
    'Construction / BTP': {
        'solvabilite': {'bon': 0.35, 'correct': 0.25},
        'liquidite': {'bon': 1.5, 'correct': 1.0},
        'roe': {'bon': 0.10, 'correct': 0.05},
        'gearing': {'bon': 0.5, 'modere': 1.0},
        'dette_ebitda': {'bon': 2, 'correct': 4},
        'couverture': {'bon': 5, 'correct': 2},
        'ebitda_par_etp': {'bon': 15000, 'correct': 8000},
        'multiple_bas': 4, 'multiple_central': 5, 'multiple_haut': 6.5,
        'label': 'BTP',
    },
    'Services': {
        'solvabilite': {'bon': 0.40, 'correct': 0.30},
        'liquidite': {'bon': 1.5, 'correct': 1.0},
        'roe': {'bon': 0.15, 'correct': 0.08},
        'gearing': {'bon': 0.3, 'modere': 0.7},
        'dette_ebitda': {'bon': 1.5, 'correct': 3},
        'couverture': {'bon': 6, 'correct': 3},
        'ebitda_par_etp': {'bon': 20000, 'correct': 10000},
        'multiple_bas': 5, 'multiple_central': 6, 'multiple_haut': 8,
        'label': 'Services',
    },
    'Commerce': {
        'solvabilite': {'bon': 0.30, 'correct': 0.20},
        'liquidite': {'bon': 1.3, 'correct': 0.8},
        'roe': {'bon': 0.12, 'correct': 0.06},
        'gearing': {'bon': 0.5, 'modere': 1.0},
        'dette_ebitda': {'bon': 2, 'correct': 4},
        'couverture': {'bon': 4, 'correct': 2},
        'ebitda_par_etp': {'bon': 12000, 'correct': 6000},
        'multiple_bas': 4, 'multiple_central': 5, 'multiple_haut': 6,
        'label': 'Commerce',
    },
    'Industrie': {
        'solvabilite': {'bon': 0.35, 'correct': 0.25},
        'liquidite': {'bon': 1.5, 'correct': 1.0},
        'roe': {'bon': 0.10, 'correct': 0.05},
        'gearing': {'bon': 0.5, 'modere': 1.0},
        'dette_ebitda': {'bon': 2.5, 'correct': 4},
        'couverture': {'bon': 5, 'correct': 2},
        'ebitda_par_etp': {'bon': 15000, 'correct': 8000},
        'multiple_bas': 5, 'multiple_central': 6, 'multiple_haut': 8,
        'label': 'Industrie',
    },
    'Tech / SaaS': {
        'solvabilite': {'bon': 0.50, 'correct': 0.35},
        'liquidite': {'bon': 2.0, 'correct': 1.2},
        'roe': {'bon': 0.20, 'correct': 0.10},
        'gearing': {'bon': 0.2, 'modere': 0.5},
        'dette_ebitda': {'bon': 1, 'correct': 2},
        'couverture': {'bon': 8, 'correct': 4},
        'ebitda_par_etp': {'bon': 40000, 'correct': 20000},
        'multiple_bas': 8, 'multiple_central': 10, 'multiple_haut': 15,
        'label': 'Tech',
    },
    # Structures particulières
    'Management / Holding': {
        'solvabilite': {'bon': 0.30, 'correct': 0.15},
        'liquidite': {'bon': 1.0, 'correct': 0.5},
        'roe': {'bon': 0.05, 'correct': 0.02},
        'gearing': {'bon': 0.5, 'modere': 2.0},
        'dette_ebitda': {'bon': 3, 'correct': 6},
        'couverture': {'bon': 3, 'correct': 1},
        'multiple_bas': 3, 'multiple_central': 4, 'multiple_haut': 6,
        'label': 'Holding',
    },
    'Immobilier / SCI': {
        'solvabilite': {'bon': 0.25, 'correct': 0.15},
        'liquidite': {'bon': 1.0, 'correct': 0.5},
        'roe': {'bon': 0.06, 'correct': 0.03},
        'gearing': {'bon': 1.0, 'modere': 3.0},
        'dette_ebitda': {'bon': 4, 'correct': 8},
        'couverture': {'bon': 2, 'correct': 1},
        'multiple_bas': 6, 'multiple_central': 8, 'multiple_haut': 12,
        'label': 'Immobilier',
    },
}


def _badge(val, seuil, higher_is_better=True):
    """Return badge dict {badge, label, benchmark} based on sector thresholds."""
    if val is None:
        return {'badge': 'gris', 'label': 'N/A', 'benchmark': None}
    bon = seuil.get('bon', seuil.get('modere', 0))
    correct = seuil.get('correct', seuil.get('modere', 0))
    if higher_is_better:
        if val >= bon:
            return {'badge': 'vert', 'label': 'Bon'}
        elif val >= correct:
            return {'badge': 'jaune', 'label': 'Correct'}
        else:
            return {'badge': 'rouge', 'label': 'Faible'}
    else:
        # Lower is better (gearing, dette_ebitda)
        if val <= bon:
            return {'badge': 'vert', 'label': 'Bon' if 'bon' in seuil else 'Faible'}
        elif val <= correct or val <= seuil.get('modere', float('inf')):
            return {'badge': 'jaune', 'label': 'Correct' if 'correct' in seuil else 'Mod\u00e9r\u00e9'}
        else:
            return {'badge': 'rouge', 'label': '\u00c9lev\u00e9'}


def compute_badges(ratios: dict, secteur: str = '') -> dict:
    """Compute colored badges for each ratio based on sector thresholds."""
    seuils = SECTEUR_SEUILS.get(secteur, {})
    if not seuils:
        return {}

    sect_label = seuils.get('label', secteur)
    rent = ratios.get('rentabilite', {})
    struct = ratios.get('structure', {})
    liq = ratios.get('liquidite', {})

    badges = {}

    # Solvabilité (higher is better)
    s = seuils.get('solvabilite')
    if s:
        v = struct.get('solvabilite')
        b = _badge(v, s, True)
        b['benchmark'] = f"Seuil {sect_label} : {int(s['correct']*100)}% minimum"
        b['valeur'] = round(v * 100, 1) if v else None
        badges['solvabilite'] = b

    # Liquidité (higher is better)
    s = seuils.get('liquidite')
    if s:
        v = liq.get('liquidite_generale')
        b = _badge(v, s, True)
        b['benchmark'] = f"Seuil {sect_label} : {s['correct']} minimum"
        b['valeur'] = round(v, 2) if v else None
        badges['liquidite'] = b

    # ROE (higher is better)
    s = seuils.get('roe')
    if s:
        v = rent.get('roe')
        b = _badge(v, s, True)
        b['benchmark'] = f"Seuil {sect_label} : {int(s['correct']*100)}% minimum"
        b['valeur'] = round(v * 100, 1) if v else None
        badges['roe'] = b

    # Gearing (lower is better)
    s = seuils.get('gearing')
    if s:
        v = struct.get('gearing')
        if v is not None and v < 0:
            badges['gearing'] = {'badge': 'vert', 'label': 'Tr\u00e9sorerie nette', 'valeur': round(v, 2),
                                 'benchmark': f"Seuil {sect_label} : < {s['bon']}"}
        else:
            b = _badge(v, s, False)
            b['benchmark'] = f"Seuil {sect_label} : < {s['bon']} id\u00e9al"
            b['valeur'] = round(v, 2) if v else None
            badges['gearing'] = b

    # Dette/EBITDA (lower is better)
    s = seuils.get('dette_ebitda')
    if s:
        v = struct.get('dettes_ebitda')
        if v is not None and v < 0:
            badges['dette_ebitda'] = {'badge': 'vert', 'label': 'Tr\u00e9sorerie nette', 'valeur': round(v, 2),
                                      'benchmark': f"Seuil {sect_label} : < {s['bon']} ans"}
        else:
            b = _badge(v, s, False)
            b['benchmark'] = f"Seuil {sect_label} : < {s['bon']} ans"
            b['valeur'] = round(v, 1) if v else None
            badges['dette_ebitda'] = b

    # Couverture intérêts (higher is better)
    s = seuils.get('couverture')
    if s:
        v = struct.get('couverture_interets')
        b = _badge(v, s, True)
        b['benchmark'] = f"Seuil {sect_label} : > {s['correct']}x"
        b['valeur'] = round(v, 1) if v else None
        badges['couverture'] = b

    return badges


def _safe_div(a, b):
    if not b:
        return None
    return round(a / b, 4)


def compute_ratios(data: dict, secteur: str = None, params: dict = None) -> dict:
    """Compute all financial ratios from comptes annuels data dict."""
    if params is None:
        params = {}

    ca_reel = data.get('chiffre_affaires', 0) or 0
    marge_brute = data.get('marge_brute', 0) or 0
    schema_abrege = bool(data.get('_ca_is_marge_brute'))
    ca = ca_reel if not schema_abrege else 0
    achats = abs(data.get('achats_services', 0) or 0)
    remunerations = abs(data.get('remunerations', 0) or 0)
    amortissements = abs(data.get('amortissements', 0) or 0)
    autres_charges = abs(data.get('autres_charges', 0) or 0)
    res_exploit = data.get('resultat_exploitation', 0) or 0
    charges_fin = abs(data.get('charges_financieres', 0) or 0)
    res_avant_impots = data.get('resultat_avant_impots', 0) or 0
    impots = abs(data.get('impots', 0) or 0)
    res_net = data.get('resultat_net', 0) or 0

    actifs_immo = data.get('actifs_immobilises', 0) or 0
    stocks = data.get('stocks', 0) or 0
    creances = data.get('creances_court_terme', 0) or 0
    tresorerie = data.get('tresorerie', 0) or 0
    actif_circulant = data.get('actifs_circulants', 0) or (stocks + creances + tresorerie)
    total_actif = data.get('total_actif', 0) or 0
    capitaux_propres = data.get('capitaux_propres', 0) or 0
    dettes_lt = data.get('dettes_long_terme', 0) or 0
    dettes_ct = data.get('dettes_court_terme', 0) or 0
    total_passif = data.get('total_passif', 0) or 0

    ebitda = res_exploit + amortissements
    ebit = res_exploit
    marge_ebitda = _safe_div(ebitda, ca)
    marge_nette = _safe_div(res_net, ca)
    roe = _safe_div(res_net, capitaux_propres)
    roa = _safe_div(res_net, total_actif)

    dette_nette_bancaire = data.get('dette_nette_bancaire')
    dette_nette_comptable = dettes_lt + dettes_ct - tresorerie
    if dette_nette_bancaire is not None and dette_nette_bancaire != 0:
        dette_nette_calc = dette_nette_bancaire
    else:
        dette_nette_calc = dette_nette_comptable
    dette_nette = params.get('dette_nette', dette_nette_calc)
    gearing = _safe_div(dette_nette, capitaux_propres)
    solvabilite = _safe_div(capitaux_propres, total_actif)
    dettes_ebitda = _safe_div(dette_nette, ebitda) if ebitda else None
    couverture_interets = _safe_div(ebit, charges_fin)

    liquidite_generale = _safe_div(actif_circulant, dettes_ct)
    liquidite_reduite = _safe_div(creances + tresorerie, dettes_ct)
    bfr = stocks + creances - dettes_ct
    bfr_jours_ca = _safe_div(bfr * 365, ca) if ca else None

    secteur_key = secteur or ''
    multiples = SECTEUR_MULTIPLES.get(secteur_key, {'low': 4, 'high': 8, 'default': 5})
    multiple = params.get('multiple_ebitda', multiples['default'])

    valeur_ev_ebitda = ebitda * multiple if ebitda else 0
    valeur_equity_ev = valeur_ev_ebitda - dette_nette if valeur_ev_ebitda else 0
    valeur_capitaux = capitaux_propres

    ratios = {
        'schema_abrege': schema_abrege,
        'marge_brute': round(marge_brute, 2) if marge_brute else 0,
        'rentabilite': {
            'ebitda': round(ebitda, 2),
            'marge_ebitda': marge_ebitda,
            'ebit': round(ebit, 2),
            'marge_nette': marge_nette,
            'roe': roe,
            'roa': roa,
        },
        'structure': {
            'dette_nette': round(dette_nette, 2),
            'gearing': gearing,
            'solvabilite': solvabilite,
            'dettes_ebitda': round(dettes_ebitda, 2) if dettes_ebitda is not None else None,
            'couverture_interets': round(couverture_interets, 2) if couverture_interets is not None else None,
        },
        'liquidite': {
            'liquidite_generale': round(liquidite_generale, 2) if liquidite_generale is not None else None,
            'liquidite_reduite': round(liquidite_reduite, 2) if liquidite_reduite is not None else None,
            'bfr': round(bfr, 2),
            'bfr_jours_ca': round(bfr_jours_ca, 0) if bfr_jours_ca is not None else None,
        },
        'structure_detail': {
            'dettes_lt': round(dettes_lt, 2),
            'dettes_ct': round(dettes_ct, 2),
            'tresorerie': round(tresorerie, 2),
            'dette_nette_comptable': round(dette_nette_comptable, 2),
            'dette_nette_bancaire': round(dette_nette_bancaire, 2) if dette_nette_bancaire is not None else None,
            'dettes_credit_lt': data.get('dettes_credit_lt', 0) or 0,
            'dettes_financieres_lt': data.get('dettes_financieres_lt', 0) or 0,
            'autres_emprunts_lt': data.get('autres_emprunts_lt', 0) or 0,
            'dettes_lt_echeant_annee': data.get('dettes_lt_echeant_annee', 0) or 0,
            'dettes_credit_ct': data.get('dettes_credit_ct', 0) or 0,
            'dettes_financieres_ct': data.get('dettes_financieres_ct', 0) or 0,
            'fournisseurs': data.get('fournisseurs', 0) or 0,
            'acomptes_commandes': data.get('acomptes_commandes', 0) or 0,
            'dettes_fiscales_sociales': data.get('dettes_fiscales_sociales', 0) or 0,
            'autres_dettes': data.get('autres_dettes', 0) or 0,
            'creances_commerciales': data.get('creances_commerciales', 0) or 0,
            'autres_creances': data.get('autres_creances', 0) or 0,
            'placements_tresorerie': data.get('placements_tresorerie', 0) or 0,
        },
        'valorisation': {
            'multiple_utilise': multiple,
            'valeur_ev_ebitda': round(valeur_ev_ebitda, 2),
            'valeur_equity_ev': round(valeur_equity_ev, 2),
            'valeur_capitaux_propres': round(valeur_capitaux, 2),
            'fourchette_ev_low': round(ebitda * multiples['low'] - dette_nette, 2) if ebitda else 0,
            'fourchette_ev_high': round(ebitda * multiples['high'] - dette_nette, 2) if ebitda else 0,
            'fourchette_low_multiple': multiples['low'],
            'fourchette_high_multiple': multiples['high'],
        },
    }

    benchmarks = SECTEUR_BENCHMARKS.get(secteur_key, {})
    indicators = {}

    def _indicator(key, val, bench_key=None):
        bk = bench_key or key
        if val is None:
            return {'value': None, 'status': 'neutral', 'benchmark': None}
        bench = benchmarks.get(bk)
        if not bench:
            return {'value': val, 'status': 'neutral', 'benchmark': None}
        low, high = bench
        if low <= val <= high:
            status = 'bon'
        elif val > high:
            status = 'bon' if bk in ('marge_ebitda', 'marge_nette', 'roe', 'solvabilite', 'liquidite_generale') else 'attention'
        else:
            status = 'alerte' if bk in ('marge_ebitda', 'marge_nette', 'roe', 'solvabilite', 'liquidite_generale') else 'bon'
        return {'value': val, 'status': status, 'benchmark': {'low': low, 'high': high}}

    indicators['marge_ebitda'] = _indicator('marge_ebitda', marge_ebitda)
    indicators['marge_nette'] = _indicator('marge_nette', marge_nette)
    indicators['roe'] = _indicator('roe', roe)
    indicators['solvabilite'] = _indicator('solvabilite', solvabilite)
    indicators['liquidite_generale'] = _indicator('liquidite_generale', liquidite_generale)
    indicators['gearing'] = _indicator('gearing', gearing)

    ratios['indicators'] = indicators
    ratios['valorisation_resume'] = {
        'ebitda': round(ebitda, 2),
        'multiple': multiple,
        'ev_ebitda': round(valeur_ev_ebitda, 2),
        'dette_nette': round(dette_nette, 2),
        'equity_ev_ebitda': round(valeur_equity_ev, 2),
        'capitaux_propres_comptables': round(valeur_capitaux, 2),
        'fourchette_equity_low': round(ebitda * multiples['low'] - dette_nette, 2) if ebitda else 0,
        'fourchette_equity_high': round(ebitda * multiples['high'] - dette_nette, 2) if ebitda else 0,
        'dcf_ev': None,
        'dcf_equity': None,
    }
    return ratios


# ── Linear scoring system ──────────────────────────────────────────────────
#
# Each ratio is scored 0-10 via piecewise linear interpolation:
#   value <= borne_min  → 0/10
#   borne_min < value < seuil   → linear 0 → 7
#   seuil <= value < borne_max  → linear 7 → 10
#   value >= borne_max → 10/10
#
# For "lower is better" ratios (gearing, dette_ebitda): the scale is inverted.
# Each ratio has a weight; the final score is weighted sum → 0-100.

SECTEUR_BORNES = {
    'Construction / BTP': {
        # higher is better
        'solvabilite':  {'min': 0.10, 'seuil': 0.25, 'max': 0.40, 'poids': 15},
        'liquidite':    {'min': 0.60, 'seuil': 1.10, 'max': 1.80, 'poids': 12},
        'roe':          {'min': 0.00, 'seuil': 0.08, 'max': 0.20, 'poids': 12},
        'marge_ebitda': {'min': 0.00, 'seuil': 0.08, 'max': 0.15, 'poids': 10},
        'couverture':   {'min': 0.00, 'seuil': 2.00, 'max': 5.00, 'poids': 8},
        # lower is better (inverted)
        'gearing':      {'min': 0.30, 'seuil': 1.00, 'max': 2.00, 'poids': 10, 'inv': True},
        'dette_ebitda': {'min': 1.00, 'seuil': 3.00, 'max': 5.00, 'poids': 10, 'inv': True},
        # binary
        'ebitda_positif': {'poids': 15},
        'resultat_net':   {'poids': 8},
    },
    'Services': {
        'solvabilite':  {'min': 0.15, 'seuil': 0.30, 'max': 0.50, 'poids': 15},
        'liquidite':    {'min': 0.70, 'seuil': 1.20, 'max': 2.00, 'poids': 12},
        'roe':          {'min': 0.00, 'seuil': 0.10, 'max': 0.25, 'poids': 12},
        'marge_ebitda': {'min': 0.00, 'seuil': 0.10, 'max': 0.25, 'poids': 10},
        'couverture':   {'min': 0.00, 'seuil': 3.00, 'max': 6.00, 'poids': 8},
        'gearing':      {'min': 0.20, 'seuil': 0.70, 'max': 1.50, 'poids': 10, 'inv': True},
        'dette_ebitda': {'min': 0.50, 'seuil': 2.00, 'max': 4.00, 'poids': 10, 'inv': True},
        'ebitda_positif': {'poids': 15},
        'resultat_net':   {'poids': 8},
    },
    'Commerce': {
        'solvabilite':  {'min': 0.08, 'seuil': 0.20, 'max': 0.35, 'poids': 15},
        'liquidite':    {'min': 0.50, 'seuil': 0.80, 'max': 1.60, 'poids': 12},
        'roe':          {'min': 0.00, 'seuil': 0.06, 'max': 0.18, 'poids': 12},
        'marge_ebitda': {'min': 0.00, 'seuil': 0.05, 'max': 0.12, 'poids': 10},
        'couverture':   {'min': 0.00, 'seuil': 2.00, 'max': 4.00, 'poids': 8},
        'gearing':      {'min': 0.50, 'seuil': 1.00, 'max': 2.50, 'poids': 10, 'inv': True},
        'dette_ebitda': {'min': 1.00, 'seuil': 3.00, 'max': 5.00, 'poids': 10, 'inv': True},
        'ebitda_positif': {'poids': 15},
        'resultat_net':   {'poids': 8},
    },
    'Industrie': {
        'solvabilite':  {'min': 0.12, 'seuil': 0.25, 'max': 0.45, 'poids': 15},
        'liquidite':    {'min': 0.60, 'seuil': 1.00, 'max': 2.00, 'poids': 12},
        'roe':          {'min': 0.00, 'seuil': 0.05, 'max': 0.20, 'poids': 12},
        'marge_ebitda': {'min': 0.00, 'seuil': 0.10, 'max': 0.20, 'poids': 10},
        'couverture':   {'min': 0.00, 'seuil': 2.00, 'max': 5.00, 'poids': 8},
        'gearing':      {'min': 0.30, 'seuil': 1.00, 'max': 2.00, 'poids': 10, 'inv': True},
        'dette_ebitda': {'min': 1.00, 'seuil': 3.00, 'max': 5.00, 'poids': 10, 'inv': True},
        'ebitda_positif': {'poids': 15},
        'resultat_net':   {'poids': 8},
    },
    'Tech / SaaS': {
        'solvabilite':  {'min': 0.15, 'seuil': 0.35, 'max': 0.60, 'poids': 15},
        'liquidite':    {'min': 0.80, 'seuil': 1.50, 'max': 3.00, 'poids': 12},
        'roe':          {'min': 0.00, 'seuil': 0.10, 'max': 0.30, 'poids': 12},
        'marge_ebitda': {'min': 0.00, 'seuil': 0.15, 'max': 0.40, 'poids': 10},
        'couverture':   {'min': 0.00, 'seuil': 4.00, 'max': 8.00, 'poids': 8},
        'gearing':      {'min': 0.00, 'seuil': 0.50, 'max': 1.00, 'poids': 10, 'inv': True},
        'dette_ebitda': {'min': 0.50, 'seuil': 1.50, 'max': 3.00, 'poids': 10, 'inv': True},
        'ebitda_positif': {'poids': 15},
        'resultat_net':   {'poids': 8},
    },
    'Management / Holding': {
        'solvabilite':  {'min': 0.05, 'seuil': 0.15, 'max': 0.40, 'poids': 18},
        'liquidite':    {'min': 0.30, 'seuil': 0.50, 'max': 2.00, 'poids': 10},
        'roe':          {'min': 0.00, 'seuil': 0.02, 'max': 0.10, 'poids': 8},
        'marge_ebitda': {'min': 0.00, 'seuil': 0.00, 'max': 1.00, 'poids': 4},
        'couverture':   {'min': 0.00, 'seuil': 1.00, 'max': 3.00, 'poids': 8},
        'gearing':      {'min': 0.50, 'seuil': 2.00, 'max': 4.00, 'poids': 10, 'inv': True},
        'dette_ebitda': {'min': 1.00, 'seuil': 4.00, 'max': 8.00, 'poids': 10, 'inv': True},
        'ebitda_positif': {'poids': 20},
        'resultat_net':   {'poids': 12},
    },
    'Immobilier / SCI': {
        'solvabilite':  {'min': 0.05, 'seuil': 0.15, 'max': 0.35, 'poids': 18},
        'liquidite':    {'min': 0.30, 'seuil': 0.50, 'max': 1.50, 'poids': 10},
        'roe':          {'min': 0.00, 'seuil': 0.03, 'max': 0.10, 'poids': 8},
        'marge_ebitda': {'min': 0.00, 'seuil': 0.20, 'max': 0.50, 'poids': 6},
        'couverture':   {'min': 0.00, 'seuil': 1.00, 'max': 2.00, 'poids': 8},
        'gearing':      {'min': 1.00, 'seuil': 3.00, 'max': 5.00, 'poids': 10, 'inv': True},
        'dette_ebitda': {'min': 2.00, 'seuil': 6.00, 'max': 10.00, 'poids': 8, 'inv': True},
        'ebitda_positif': {'poids': 20},
        'resultat_net':   {'poids': 12},
    },
}

# Fallback bornes for sectors not explicitly listed (ASBL, Startup, unknown)
_BORNES_DEFAULT = {
    'solvabilite':  {'min': 0.10, 'seuil': 0.25, 'max': 0.45, 'poids': 15},
    'liquidite':    {'min': 0.50, 'seuil': 1.00, 'max': 2.00, 'poids': 12},
    'roe':          {'min': 0.00, 'seuil': 0.05, 'max': 0.20, 'poids': 12},
    'marge_ebitda': {'min': 0.00, 'seuil': 0.08, 'max': 0.20, 'poids': 10},
    'couverture':   {'min': 0.00, 'seuil': 2.00, 'max': 5.00, 'poids': 8},
    'gearing':      {'min': 0.30, 'seuil': 1.00, 'max': 2.00, 'poids': 10, 'inv': True},
    'dette_ebitda': {'min': 1.00, 'seuil': 3.00, 'max': 5.00, 'poids': 10, 'inv': True},
    'ebitda_positif': {'poids': 15},
    'resultat_net':   {'poids': 8},
}


def _score_linear(value, borne_min, seuil, borne_max):
    """Piecewise linear interpolation → 0.0 to 10.0.

    value <= borne_min → 0
    borne_min < value < seuil  → linear 0 → 7
    seuil <= value < borne_max → linear 7 → 10
    value >= borne_max → 10
    """
    if value is None:
        return None
    if value <= borne_min:
        return 0.0
    if value < seuil:
        return 7.0 * (value - borne_min) / (seuil - borne_min) if seuil > borne_min else 7.0
    if value < borne_max:
        return 7.0 + 3.0 * (value - seuil) / (borne_max - seuil) if borne_max > seuil else 10.0
    return 10.0


def _score_linear_inv(value, borne_min, seuil, borne_max):
    """Inverted linear for "lower is better" ratios.

    value <= borne_min → 10
    borne_min < value < seuil  → linear 10 → 7
    seuil <= value < borne_max → linear 7 → 0
    value >= borne_max → 0
    """
    if value is None:
        return None
    if value <= borne_min:
        return 10.0
    if value < seuil:
        return 10.0 - 3.0 * (value - borne_min) / (seuil - borne_min) if seuil > borne_min else 7.0
    if value < borne_max:
        return 7.0 - 7.0 * (value - seuil) / (borne_max - seuil) if borne_max > seuil else 0.0
    return 0.0


def compute_score(ratios: dict, secteur: str = '', comptes_data: dict = None,
                   nb_exercices: int = 1, ebitda_variation: float = None) -> dict:
    """Deterministic linear health score 0-100.

    Each ratio is scored 0-10 via piecewise linear interpolation against
    sector-specific bounds, then weighted to produce a 0-100 composite.

    Returns {'score': int, 'score_deductions': [{'motif': str, 'points': float}]}
    """
    bornes = SECTEUR_BORNES.get(secteur, _BORNES_DEFAULT)

    rent = ratios.get('rentabilite', {})
    struct = ratios.get('structure', {})
    liq = ratios.get('liquidite', {})

    # Map ratio keys → extracted values
    ratio_values = {
        'solvabilite':  struct.get('solvabilite'),
        'liquidite':    liq.get('liquidite_generale'),
        'roe':          rent.get('roe'),
        'marge_ebitda': rent.get('marge_ebitda'),
        'couverture':   struct.get('couverture_interets'),
        'gearing':      struct.get('gearing'),
        'dette_ebitda': struct.get('dettes_ebitda'),
    }

    total_points = 0.0
    total_weight = 0.0
    details = []

    # Score each continuous ratio
    for key, value in ratio_values.items():
        b = bornes.get(key)
        if not b or 'min' not in b:
            continue
        poids = b['poids']
        if value is None:
            # Unknown value → neutral (5/10)
            pts = 5.0
            details.append({'motif': f'{key} : N/A (neutre)', 'points': round(pts, 1)})
        elif b.get('inv'):
            pts = _score_linear_inv(value, b['min'], b['seuil'], b['max'])
            details.append({'motif': f'{key} : {_fmt_ratio(key, value)} → {pts:.1f}/10', 'points': round(pts, 1)})
        else:
            pts = _score_linear(value, b['min'], b['seuil'], b['max'])
            details.append({'motif': f'{key} : {_fmt_ratio(key, value)} → {pts:.1f}/10', 'points': round(pts, 1)})
        total_points += pts * poids
        total_weight += poids

    # Binary: EBITDA positif
    ebitda = rent.get('ebitda', 0) or 0
    b_ebitda = bornes.get('ebitda_positif', {})
    poids_ebitda = b_ebitda.get('poids', 15)
    if ebitda > 0:
        pts = 10.0
    elif ebitda == 0:
        pts = 5.0
    else:
        pts = 0.0
    details.append({'motif': f'ebitda_positif : {ebitda:,.0f}€ → {pts:.0f}/10', 'points': round(pts, 1)})
    total_points += pts * poids_ebitda
    total_weight += poids_ebitda

    # Binary: résultat net positif
    roe = rent.get('roe')
    b_rn = bornes.get('resultat_net', {})
    poids_rn = b_rn.get('poids', 8)
    if roe is not None and roe > 0:
        pts = 10.0
    elif roe is not None and roe == 0:
        pts = 5.0
    else:
        pts = 0.0
    details.append({'motif': f'resultat_net : ROE {_fmt_ratio("roe", roe)} → {pts:.0f}/10', 'points': round(pts, 1)})
    total_points += pts * poids_rn
    total_weight += poids_rn

    # Weighted average → 0-100
    if total_weight > 0:
        score = round((total_points / total_weight) * 10)  # (pts/10) / weight * 100
    else:
        score = 50

    score = max(0, min(95, score))

    return {'score': score, 'score_deductions': details}


def _fmt_ratio(key, value):
    """Format a ratio value for the deduction detail string."""
    if value is None:
        return 'N/A'
    if key in ('solvabilite', 'roe', 'marge_ebitda'):
        return f'{value * 100:.1f}%'
    if key in ('liquidite', 'gearing'):
        return f'{value:.2f}'
    if key in ('dette_ebitda', 'couverture'):
        return f'{value:.1f}x'
    return f'{value}'


POIDS_EBITDA = {
    1: [1.0],
    2: [0.35, 0.65],
    3: [0.20, 0.30, 0.50],
    4: [0.10, 0.20, 0.30, 0.40],
    5: [0.05, 0.10, 0.20, 0.30, 0.35],
}


def compute_ebitda_pondere(exercices: list) -> dict:
    """Compute weighted EBITDA from exercices sorted by year ascending.

    Returns {ebitda_pondere, poids_detail: [{annee, ebitda, poids, contribution}]}
    """
    ebitdas = [(ex.get('annee'), ex.get('ebitda', 0) or 0) for ex in exercices if ex.get('annee')]
    n = len(ebitdas)
    if n == 0:
        return {'ebitda_pondere': 0, 'poids_detail': []}

    weights = POIDS_EBITDA.get(n, POIDS_EBITDA[5])
    # If more than 5, use last 5 with standard weights
    if n > 5:
        ebitdas = ebitdas[-5:]
        weights = POIDS_EBITDA[5]
        n = 5

    # Pad weights if fewer entries
    if len(weights) > n:
        weights = weights[-n:]

    total = 0
    detail = []
    for i, (annee, ebitda) in enumerate(ebitdas):
        w = weights[i] if i < len(weights) else 0
        contribution = round(ebitda * w, 2)
        total += contribution
        detail.append({
            'annee': annee,
            'ebitda': round(ebitda, 2),
            'poids': w,
            'poids_pct': int(w * 100),
            'contribution': contribution,
        })

    return {
        'ebitda_pondere': round(total, 2),
        'poids_detail': detail,
    }


def compute_dcf(comptes_list: list, wacc: float = 0.08, growth: float = 0.02) -> dict | None:
    """Simple DCF from multi-year data."""
    if len(comptes_list) < 2:
        return None

    ebitdas = []
    fcfs = []
    for d in comptes_list:
        res_ex = d.get('resultat_exploitation', 0) or 0
        amort = abs(d.get('amortissements', 0) or 0)
        impots = abs(d.get('impots', 0) or 0)
        ebitda = res_ex + amort
        ebitdas.append(ebitda)
        fcfs.append(ebitda - impots - amort)

    if not ebitdas or ebitdas[-1] <= 0:
        return None

    last_ebitda = ebitdas[-1]
    last_fcf = fcfs[-1]

    growth_rates = []
    for i in range(1, len(ebitdas)):
        if ebitdas[i - 1] > 0:
            growth_rates.append((ebitdas[i] - ebitdas[i - 1]) / ebitdas[i - 1])
    hist_growth = sum(growth_rates) / len(growth_rates) if growth_rates else growth

    if len(comptes_list) <= 2:
        proj_growth = max(-0.03, min(hist_growth, 0.03))
    else:
        proj_growth = max(-0.05, min(hist_growth, 0.05))

    projected_fcfs = []
    projected_ebitdas = []
    for yr in range(1, 6):
        projected_ebitdas.append(last_ebitda * ((1 + proj_growth) ** yr))
        projected_fcfs.append(max(last_fcf * ((1 + proj_growth) ** yr), 0))

    if wacc > growth and projected_fcfs[-1] > 0:
        terminal_value = projected_fcfs[-1] * (1 + growth) / (wacc - growth)
    else:
        terminal_value = 0

    dcf_value = sum(fcf / ((1 + wacc) ** (i + 1)) for i, fcf in enumerate(projected_fcfs))
    dcf_value += terminal_value / ((1 + wacc) ** 5)

    return {
        'valeur_dcf': round(dcf_value, 2),
        'ebitda_projetes': [round(e, 2) for e in projected_ebitdas],
        'fcf_projetes': [round(f, 2) for f in projected_fcfs],
        'terminal_value': round(terminal_value, 2),
        'taux_croissance_historique': round(hist_growth, 4),
        'taux_croissance_projete': round(proj_growth, 4),
    }


def compute_productivite(data: dict, ratios: dict, secteur: str = '') -> dict | None:
    """Compute productivity per FTE if ETP data is available."""
    etp = data.get('etp_moyen')
    if not etp or etp <= 0:
        return None

    ebitda = ratios.get('rentabilite', {}).get('ebitda', 0) or 0
    marge_brute = data.get('marge_brute', 0) or 0
    ca = data.get('chiffre_affaires', 0) or 0
    schema_abrege = bool(data.get('_ca_is_marge_brute'))

    ebitda_par_etp = round(ebitda / etp, 2) if ebitda else None
    marge_par_etp = round(marge_brute / etp, 2) if marge_brute else None
    ca_par_etp = round(ca / etp, 2) if ca and not schema_abrege else None

    # Badge for EBITDA/ETP
    seuils = SECTEUR_SEUILS.get(secteur, {})
    etp_seuil = seuils.get('ebitda_par_etp')
    sect_label = seuils.get('label', secteur)
    badge = 'gris'
    if etp_seuil and ebitda_par_etp is not None:
        if ebitda_par_etp >= etp_seuil['bon']:
            badge = 'vert'
        elif ebitda_par_etp >= etp_seuil['correct']:
            badge = 'jaune'
        else:
            badge = 'rouge'

    benchmark = f"Benchmark {sect_label} : ~{etp_seuil['bon']:,.0f}\u20ac/ETP" if etp_seuil else None

    return {
        'etp': round(etp, 1),
        'ebitda_par_etp': ebitda_par_etp,
        'marge_par_etp': marge_par_etp,
        'ca_par_etp': ca_par_etp,
        'badge_ebitda_etp': badge,
        'benchmark': benchmark,
    }


def compute_evolution(exercices: list) -> dict:
    """Compute evolution and tendencies across multiple exercises.

    exercices: list of {annee, ratios, badges} dicts, sorted by year ascending.
    Returns evolution_ratios and tendances.
    """
    if len(exercices) < 2:
        return {'evolution_ratios': {}, 'tendances': {}}

    ratio_keys = ['solvabilite', 'roe', 'liquidite', 'gearing', 'dette_ebitda', 'couverture']
    ratio_paths = {
        'solvabilite': lambda r: (r.get('structure') or {}).get('solvabilite'),
        'roe': lambda r: (r.get('rentabilite') or {}).get('roe'),
        'liquidite': lambda r: (r.get('liquidite') or {}).get('liquidite_generale'),
        'gearing': lambda r: (r.get('structure') or {}).get('gearing'),
        'dette_ebitda': lambda r: (r.get('structure') or {}).get('dettes_ebitda'),
        'couverture': lambda r: (r.get('structure') or {}).get('couverture_interets'),
    }

    evolution = {}
    tendances = {}

    for key in ratio_keys:
        path_fn = ratio_paths[key]
        points = []
        for ex in exercices:
            val = path_fn(ex.get('ratios', {}))
            badge_data = ex.get('badges', {}).get(key, {})
            points.append({
                'annee': ex['annee'],
                'valeur': round(val * 100, 1) if val is not None and key in ('solvabilite', 'roe') else (round(val, 2) if val is not None else None),
                'badge': badge_data.get('badge', 'gris'),
            })

        evolution[key] = points

        # Tendance: compare last vs first
        first_val = points[0].get('valeur')
        last_val = points[-1].get('valeur')
        if first_val is not None and last_val is not None and first_val != 0:
            change_pct = abs(last_val - first_val) / abs(first_val)
            higher_is_better = key not in ('gearing', 'dette_ebitda')
            if change_pct < 0.02:
                tendances[key] = 'stable'
            elif last_val > first_val:
                tendances[key] = 'amelioration' if higher_is_better else 'degradation'
            else:
                tendances[key] = 'degradation' if higher_is_better else 'amelioration'
        else:
            tendances[key] = 'stable'

    return {'evolution_ratios': evolution, 'tendances': tendances}
