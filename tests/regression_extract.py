"""Filet de non-régression pour l'extraction PDF (extract.py).

But : garantir que les optimisations mémoire (A1 passe unique, A2 streaming +
flush_cache, A4 del content) ne changent PAS *ce qui* est extrait — seulement
*comment*. On capture une référence "avant", puis on rejoue "après" et on
compare à l'identique.

Ce qui est capturé pour chaque PDF de tests/fixtures/*.pdf :
  - format détecté (detect_format)
  - is_consolidated (detect_consolidated)
  - denomination, annee_exercice, annee_precedente
  - exercice (tous les codes comptables -> montants)
  - exercice_precedent
  - exercices_supplementaires (BOB multi-années)

Le timing et le pic mémoire sont AUSSI mesurés et affichés, mais NE font PAS
partie de la comparaison d'égalité (la perf doit changer, les valeurs non).

Usage :
  python tests/regression_extract.py baseline   # capture -> tests/baseline.json
  python tests/regression_extract.py check      # rejoue + compare, exit!=0 si diff
"""

import os
import sys
import glob
import json
import time
import resource

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

FIXTURES = os.path.join(HERE, "fixtures")
BASELINE = os.path.join(HERE, "baseline.json")


def _peak_rss_mb():
    # macOS: ru_maxrss en octets ; Linux: en Ko. On normalise grossièrement.
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / (1024 * 1024) if sys.platform == "darwin" else rss / 1024


def capture_one(pdf_path):
    """Renvoie (valeurs_extraites, infos_perf) pour un PDF."""
    from extract import extract_pdf, detect_format, detect_consolidated

    t0 = time.time()
    fmt = detect_format(pdf_path)
    is_conso = detect_consolidated(pdf_path)
    result = extract_pdf(pdf_path)
    dt = time.time() - t0

    # Valeurs extraites — ce qui DOIT rester identique
    values = {
        "format": fmt,
        "is_consolidated": is_conso,
        "denomination": result.get("denomination"),
        "annee_exercice": result.get("annee_exercice"),
        "annee_precedente": result.get("annee_precedente"),
        # codes non vides seulement, triés -> stable et lisible dans le diff
        "exercice": _clean(result.get("exercice")),
        "exercice_precedent": _clean(result.get("exercice_precedent")),
        "exercices_supplementaires": [
            {"annee": e.get("annee"), "comptes": _clean(e.get("comptes"))}
            for e in (result.get("exercices_supplementaires") or [])
        ],
    }
    perf = {"seconds": round(dt, 2)}
    return values, perf


def _clean(d):
    """Garde uniquement les codes à valeur non nulle/non None, triés."""
    if not isinstance(d, dict):
        return {}
    return {k: d[k] for k in sorted(d) if d[k]}


def run_all():
    pdfs = sorted(glob.glob(os.path.join(FIXTURES, "*.pdf")))
    if not pdfs:
        print(f"!! Aucun PDF dans {FIXTURES} — rien à capturer.")
        sys.exit(2)
    snapshot = {}
    print(f"{'fichier':28s} {'format':22s} {'années':12s} {'sec':>6s}  dénomination")
    print("-" * 100)
    for p in pdfs:
        name = os.path.basename(p)
        values, perf = capture_one(p)
        snapshot[name] = values
        ans = f"{values['annee_exercice']}/{values['annee_precedente']}"
        ncodes = len(values["exercice"])
        print(f"{name:28s} {values['format']:22s} {ans:12s} {perf['seconds']:6.1f}  "
              f"{(values['denomination'] or '')[:30]}  [{ncodes} codes N]")
    print("-" * 100)
    print(f"pic mémoire process (ru_maxrss): {_peak_rss_mb():.0f} Mo")
    return snapshot


def cmd_baseline():
    snap = run_all()
    with open(BASELINE, "w") as f:
        json.dump(snap, f, indent=2, ensure_ascii=False, sort_keys=True)
    print(f"\n✅ Référence écrite : {BASELINE} ({len(snap)} PDF)")


def cmd_check():
    if not os.path.exists(BASELINE):
        print(f"!! Pas de référence ({BASELINE}). Lance d'abord : baseline")
        sys.exit(2)
    with open(BASELINE) as f:
        ref = json.load(f)
    cur = run_all()

    # Comparaison stricte clé par clé
    diffs = []
    all_names = sorted(set(ref) | set(cur))
    for name in all_names:
        if name not in ref:
            diffs.append(f"[NOUVEAU] {name} absent de la référence")
            continue
        if name not in cur:
            diffs.append(f"[MANQUANT] {name} présent dans la référence, absent maintenant")
            continue
        r_json = json.dumps(ref[name], sort_keys=True, ensure_ascii=False)
        c_json = json.dumps(cur[name], sort_keys=True, ensure_ascii=False)
        if r_json != c_json:
            diffs.append(_field_diff(name, ref[name], cur[name]))

    print("\n" + "=" * 60)
    if not diffs:
        print("✅ AUCUN DIFF — valeurs extraites identiques à la référence.")
        sys.exit(0)
    print(f"❌ {len(diffs)} PDF avec différences :\n")
    for d in diffs:
        print(d)
    sys.exit(1)


def _field_diff(name, ref, cur):
    """Diff champ par champ lisible."""
    lines = [f"--- {name} ---"]
    keys = sorted(set(ref) | set(cur))
    for k in keys:
        rv, cv = ref.get(k), cur.get(k)
        if json.dumps(rv, sort_keys=True) != json.dumps(cv, sort_keys=True):
            if isinstance(rv, dict) and isinstance(cv, dict):
                subk = sorted(set(rv) | set(cv))
                for sk in subk:
                    if rv.get(sk) != cv.get(sk):
                        lines.append(f"  {k}.{sk}: AVANT={rv.get(sk)!r}  APRÈS={cv.get(sk)!r}")
            else:
                lines.append(f"  {k}: AVANT={rv!r}  APRÈS={cv!r}")
    return "\n".join(lines)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    if cmd == "baseline":
        cmd_baseline()
    elif cmd == "check":
        cmd_check()
    else:
        print(__doc__)
        sys.exit(2)
