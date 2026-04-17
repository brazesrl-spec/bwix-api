"""Debug script: upload a BOB PDF via the API and see raw extraction.

Usage: python debug_bob.py /path/to/bob.pdf
   OR: python debug_bob.py --raw /path/to/bob.pdf   (just dump text)
"""

import sys
import re
import pdfplumber


def dump_raw(pdf_path):
    """Dump raw text from every page."""
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ''
            print(f"\n{'='*60}")
            print(f"PAGE {i+1}")
            print(f"{'='*60}")
            for j, line in enumerate(text.split('\n'), 1):
                print(f"  {j:3d} | {line}")


def debug_extract(pdf_path):
    """Run the extract and show what we get."""
    from extract import extract_pdf, detect_format

    fmt = detect_format(pdf_path)
    print(f"Detected format: {fmt}")
    print()

    result = extract_pdf(pdf_path)
    print(f"Format: {result.get('format')}")
    print(f"Denomination: {result.get('denomination')}")
    print(f"Annee exercice: {result.get('annee_exercice')}")
    print(f"Annee precedente: {result.get('annee_precedente')}")

    ex = result.get('exercice', {})
    print(f"\n--- Exercice N ({result.get('annee_exercice')}) ---")
    for k in ['chiffre_affaires', 'marge_brute', 'resultat_exploitation',
              'amortissements', 'charges_financieres', 'resultat_net',
              'capitaux_propres', 'total_actif', 'total_passif',
              'dettes_long_terme', 'dettes_court_terme', 'tresorerie',
              'stocks', 'creances_court_terme']:
        print(f"  {k}: {ex.get(k, 'MISSING')}")
    ebitda = (ex.get('resultat_exploitation', 0) or 0) + abs(ex.get('amortissements', 0) or 0)
    print(f"  => EBITDA calculé: {ebitda}")

    ex1 = result.get('exercice_precedent', {})
    print(f"\n--- Exercice N-1 ({result.get('annee_precedente')}) ---")
    for k in ['chiffre_affaires', 'marge_brute', 'resultat_exploitation',
              'amortissements', 'resultat_net', 'capitaux_propres', 'total_actif']:
        print(f"  {k}: {ex1.get(k, 'MISSING')}")
    ebitda1 = (ex1.get('resultat_exploitation', 0) or 0) + abs(ex1.get('amortissements', 0) or 0)
    print(f"  => EBITDA calculé: {ebitda1}")

    extras = result.get('exercices_supplementaires', [])
    for extra in extras:
        annee = extra['annee']
        c = extra['comptes']
        print(f"\n--- Exercice {annee} (supplementaire) ---")
        for k in ['chiffre_affaires', 'resultat_exploitation', 'amortissements', 'resultat_net']:
            print(f"  {k}: {c.get(k, 'MISSING')}")
        ebitda_x = (c.get('resultat_exploitation', 0) or 0) + abs(c.get('amortissements', 0) or 0)
        print(f"  => EBITDA calculé: {ebitda_x}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python debug_bob.py [--raw] /path/to/pdf")
        sys.exit(1)

    if sys.argv[1] == '--raw':
        dump_raw(sys.argv[2])
    else:
        dump_raw(sys.argv[1])
        print("\n\n" + "="*60)
        print("EXTRACTION RESULTS")
        print("="*60)
        debug_extract(sys.argv[1])
