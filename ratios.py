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


def compute_score(ratios: dict, secteur: str = '', comptes_data: dict = None,
                   nb_exercices: int = 1, ebitda_variation: float = None) -> dict:
    """Deterministic health score 0-100 with deduction breakdown.

    Returns {'score': int, 'score_deductions': [{'motif': str, 'points': int}]}
    """
    if comptes_data is None:
        comptes_data = {}
    is_special = secteur in STRUCTURE_PARTICULIERE
    score = 50  # baseline
    deductions = []
    ind = ratios.get('indicators', {})

    # +/- points based on indicator status
    weights = {
        'solvabilite': 15,
        'liquidite_generale': 8 if is_special else 12,
        'roe': 6 if is_special else 12,
        'marge_ebitda': 6 if is_special else 12,
        'marge_nette': 4 if is_special else 8,
        'gearing': 4 if is_special else 8,
    }
    for key, w in weights.items():
        status = (ind.get(key) or {}).get('status', 'neutral')
        if status == 'bon':
            score += w
        elif status == 'alerte':
            score -= (w // 2) if is_special else w

    # Positive EBITDA bonus
    ebitda = ratios.get('rentabilite', {}).get('ebitda', 0) or 0
    if ebitda > 0:
        score += 5
    elif ebitda < 0:
        score -= 5 if is_special else 10

    # Positive net result bonus
    roe = ratios.get('rentabilite', {}).get('roe')
    roe_threshold = 0.03 if is_special else 0.05
    if roe is not None and roe > roe_threshold:
        score += 5

    # Debt coverage
    dettes_ebitda = ratios.get('structure', {}).get('dettes_ebitda')
    if dettes_ebitda is not None:
        if dettes_ebitda < 2:
            score += 5
        elif dettes_ebitda > 5:
            score -= 3 if is_special else 5

    # ── Risk deductions (applied after base score) ──────────────────────
    ca = comptes_data.get('chiffre_affaires', 0) or 0
    stocks = comptes_data.get('stocks', 0) or 0
    total_passif = comptes_data.get('total_passif', 0) or 0
    autres_dettes = comptes_data.get('autres_dettes', 0) or 0
    charges_fin = abs(comptes_data.get('charges_financieres', 0) or 0)
    dette_bancaire_lt = comptes_data.get('dette_bancaire_lt', 0) or 0
    dette_bancaire_ct = comptes_data.get('dette_bancaire_ct', 0) or 0
    bfr = ratios.get('liquidite', {}).get('bfr', 0) or 0

    # BFR vs CA (non-cumulative: highest applies)
    if ca > 0:
        bfr_ratio = bfr / ca
        if bfr_ratio > 1.5:
            deductions.append({'motif': 'BFR > 1.5x CA', 'points': -8})
            score -= 8
        elif bfr_ratio > 1.0:
            deductions.append({'motif': 'BFR > 1.0x CA', 'points': -5})
            score -= 5

    # Stocks vs CA
    if ca > 0 and stocks > ca:
        deductions.append({'motif': 'Stocks > 1.0x CA', 'points': -5})
        score -= 5

    # Autres dettes vs total passif
    if total_passif > 0 and autres_dettes / total_passif > 0.15:
        deductions.append({'motif': 'Autres dettes > 15% du passif', 'points': -4})
        score -= 4

    # Charges financières without identified bank debt
    if charges_fin > 0 and dette_bancaire_lt == 0 and dette_bancaire_ct == 0:
        deductions.append({'motif': 'Charges financi\u00e8res sans dette bancaire identifi\u00e9e', 'points': -3})
        score -= 3

    # EBITDA variation > 30%
    if ebitda_variation is not None and ebitda_variation > 0.30:
        deductions.append({'motif': 'Variation EBITDA N/N-1 > 30%', 'points': -4})
        score -= 4

    # Less than 3 exercises
    if nb_exercices < 3:
        deductions.append({'motif': f'Seulement {nb_exercices} exercice(s) disponible(s)', 'points': -3})
        score -= 3

    # Clamp to [0, 95]
    score = max(0, min(95, score))

    return {'score': score, 'score_deductions': deductions}


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
