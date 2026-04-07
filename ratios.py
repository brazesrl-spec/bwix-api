"""Financial ratios & valuation — adapted from AppCptResultat/database.py."""

SECTEUR_MULTIPLES = {
    'Construction / BTP': {'low': 4, 'high': 6, 'default': 5},
    'Tech / SaaS':        {'low': 8, 'high': 15, 'default': 10},
    'Services':           {'low': 5, 'high': 8, 'default': 6},
    'Commerce':           {'low': 4, 'high': 7, 'default': 5},
    'Industrie':          {'low': 5, 'high': 8, 'default': 6},
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
}


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
