"""BWIX — FastAPI backend for PDF analysis, Stripe payments, and Resend emails."""

import hashlib
import json
import os
import tempfile
import uuid

import anthropic
import httpx
import stripe
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from extract import extract_bnb_pdf, detect_consolidated
from ratios import compute_ratios, compute_dcf, compute_score, SECTEUR_MULTIPLES, STRUCTURE_PARTICULIERE

# ── Config ──────────────────────────────────────────────────────────────────
import logging

SUPABASE_URL = os.environ["SUPABASE_URL"].strip()
SUPABASE_KEY = os.environ["SUPABASE_KEY"].strip()
RESEND_API_KEY = os.environ["RESEND_API_KEY"].strip()
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"].strip()
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://bwixapp.vercel.app").strip()
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "").strip()

# Stripe: test mode support
STRIPE_TEST_MODE = os.environ.get("STRIPE_TEST_MODE", "false").strip().lower() == "true"
if STRIPE_TEST_MODE:
    STRIPE_SECRET = os.environ.get("STRIPE_SECRET_KEY_TEST", "").strip()
    STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID_TEST", "").strip()
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
    logging.warning("\u26a0\ufe0f STRIPE TEST MODE ACTIF")
else:
    STRIPE_SECRET = os.environ["STRIPE_SECRET_KEY"].strip()
    STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "price_1TJK3M1XczkPkPz652TlUn4J").strip()
    STRIPE_WEBHOOK_SECRET = os.environ["STRIPE_WEBHOOK_SECRET"].strip()

stripe.api_key = STRIPE_SECRET

app = FastAPI(title="BWIX API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "https://bwixapp.vercel.app", "https://bwix.app", "https://www.bwix.app", "http://localhost:8080"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Supabase helpers ────────────────────────────────────────────────────────
def _supabase_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


async def _supabase_insert(table: str, data: dict) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers=_supabase_headers(),
            json=data,
        )
        if r.status_code not in (200, 201):
            raise HTTPException(500, f"Supabase insert error: {r.text}")
        return r.json()[0]


async def _supabase_select(table: str, params: str) -> list:
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{SUPABASE_URL}/rest/v1/{table}?{params}",
            headers=_supabase_headers(),
        )
        return r.json() if r.status_code == 200 else []


async def _supabase_update(table: str, match_params: str, data: dict):
    async with httpx.AsyncClient() as client:
        await client.patch(
            f"{SUPABASE_URL}/rest/v1/{table}?{match_params}",
            headers=_supabase_headers(),
            json=data,
        )


# ── Claude AI analysis ─────────────────────────────────────────────────────
def run_claude_analysis(ratios_data: dict, comptes_data: dict, secteur: str,
                        valorisation: dict = None) -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    if valorisation is None:
        valorisation = {}

    ia_summary = {
        'secteur': secteur,
        'schema_abrege': ratios_data.get('schema_abrege', False),
        'rentabilite': ratios_data.get('rentabilite', {}),
        'structure': ratios_data.get('structure', {}),
        'liquidite': ratios_data.get('liquidite', {}),
        'indicators': ratios_data.get('indicators', {}),
    }

    valo_block = f"""
VALORISATIONS (ne pas recalculer) :
- EBITDA de référence : {valorisation.get('ebitda_reference', 0):,.0f}€ ({valorisation.get('ebitda_reference_label', '')})
- Multiple sectoriel : {valorisation.get('multiple_sectoriel', 5)}x
- EV/EBITDA : {valorisation.get('ev_ebitda', 0):,.0f}€
- DCF : {valorisation.get('dcf', 'Non calculable')}{'€' if isinstance(valorisation.get('dcf'), (int, float)) else ''}
- Actif net corrigé : {valorisation.get('actif_net', 0):,.0f}€
- Fourchette : {valorisation.get('fourchette_basse', 0):,.0f}€ → {valorisation.get('fourchette_haute', 0):,.0f}€"""

    context = (
        f"Données comptables :\n{json.dumps(comptes_data, indent=2, ensure_ascii=False)}\n\n"
        f"Ratios :\n{json.dumps(ia_summary, indent=2, ensure_ascii=False)}\n\n"
        f"{valo_block}"
    )

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system="""Tu reçois des données financières déjà calculées par le système.
NE PAS recalculer les valorisations toi-même.
Utilise UNIQUEMENT les chiffres fournis dans la section VALORISATIONS ci-dessous.
Quand tu mentionnes une fourchette de valeur, utilise uniquement fourchette_basse et fourchette_haute.
Quand tu mentionnes la valeur EV/EBITDA, utilise uniquement ev_ebitda.

Tu es un analyste financier expert en PME belges.
Analyse ces données de façon claire, structurée et actionnable.
Pas de jargon inutile. Sois direct sur les points forts, les risques et les recommandations prioritaires.

IMPORTANT :
- Si schema_abrege=true, ne commente pas les marges (EBITDA, nette).
- La dette nette fournie est la dette nette BANCAIRE retraitée.

CONTEXTUALISATION DES RATIOS FAIBLES :
Quand un ratio est sous le seuil sectoriel, ne pas se contenter de le signaler. Proposer systématiquement une explication structurelle probable :

- Solvabilité faible : "Peut s'expliquer par une politique de distribution active aux associés, des remontées vers une holding, ou un financement important d'actifs. À contextualiser avec votre comptable."
- BFR élevé (>1x CA) : "Structurel dans ce secteur (délais de paiement clients 60-90 jours). Surveillez le recouvrement et la rotation des stocks."
- Dette/EBITDA élevé (>3x) : "Peut refléter un investissement récent (immo, matériel) plutôt qu'une fragilité structurelle. Vérifier la nature et la maturité des dettes."
- Charges financières sans dette bancaire visible : "Peut indiquer du leasing, des emprunts intra-groupe ou des dettes hors bilan. Clarification conseillée."
- ROE faible (<8%) : "Peut résulter d'une rémunération des dirigeants via management fees non visibles dans ce bilan, ou d'une année de transition."

RÈGLES :
- Toujours signaler le ratio en point d'attention si sous le seuil — ne jamais masquer.
- Toujours proposer une explication probable.
- Toujours terminer par "À vérifier avec votre comptable/fiduciaire".
- Ne jamais affirmer avec certitude — BWIX lit un bilan, pas la réalité complète.

Réponds UNIQUEMENT en JSON valide :
{
  "synthese": "2-3 phrases résumé",
  "points_forts": ["...", "..."],
  "points_attention": ["...", "..."],
  "risques": ["...", "..."],
  "recommandations": ["...", "..."],
  "valorisation_commentaire": "...",
  "score_sante": 0-100
}""",
        messages=[{"role": "user", "content": context}],
    )

    response_text = message.content[0].text.strip()
    if response_text.startswith('```'):
        response_text = response_text.split('\n', 1)[1].rsplit('```', 1)[0].strip()

    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        return {
            'synthese': response_text[:500],
            'points_forts': [], 'points_attention': [], 'risques': [],
            'recommandations': [], 'valorisation_commentaire': '',
            'score_sante': 50,
        }


# ── Resend email ────────────────────────────────────────────────────────────
async def send_email(to: str, subject: str, html: str):
    async with httpx.AsyncClient() as client:
        await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json={
                "from": "BWIX <noreply@bwix.app>",
                "to": [to],
                "subject": subject,
                "html": html,
            },
        )


async def send_unlock_email(email: str, token: str):
    """Send analysis unlock confirmation email. Shared by Stripe webhook and promo codes."""
    link = f"{FRONTEND_URL}/resultats?token={token}"
    await send_email(
        email,
        "Votre analyse BWIX est pr\u00eate",
        f"""<div style="font-family:Inter,sans-serif;max-width:600px;margin:0 auto;padding:40px 20px">
        <h1 style="color:#1e3a5f">Votre analyse BWIX</h1>
        <p>Votre analyse financi\u00e8re compl\u00e8te est d\u00e9sormais accessible.</p>
        <p><a href="{link}" style="display:inline-block;background:#00c896;color:#0b1929;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:600">
        Voir l'analyse compl\u00e8te</a></p>
        <p style="color:#8fa3bf;font-size:14px;margin-top:24px">
        Ce lien est unique et reste accessible \u00e0 tout moment.</p>
        <hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0">
        <p style="color:#8fa3bf;font-size:12px">
        BWIX est un outil d'aide \u00e0 la d\u00e9cision indicatif. Les r\u00e9sultats ne constituent pas un conseil financier ou comptable.</p>
        </div>""",
    )


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/health")
@app.get("/api/health")
async def health():
    return {"status": "ok"}


# ── Free slots ──────────────────────────────────────────────────────────────

@app.get("/api/free-slots")
async def get_free_slots():
    rows = await _supabase_select("settings", "key=eq.free_slots&select=value")
    count = int(rows[0]["value"]) if rows else 0
    return {"free_slots": max(0, count)}


@app.post("/api/claim-free")
async def claim_free_slot(request: Request):
    """Claim a free analysis slot with email. Returns the analysis token."""
    body = await request.json()
    email = (body.get("email") or "").strip().lower()
    analyse_token = body.get("token")

    if not email or "@" not in email or not analyse_token:
        raise HTTPException(400, "Email et token requis.")

    # Check if email already used a free slot
    existing = await _supabase_select("waitlist", f"email=eq.{email}&source=eq.free_slot&select=email")
    if existing:
        # Find their previous analysis
        prev = await _supabase_select("analyses", f"email=eq.{email}&unlocked=eq.true&select=token&order=created_at.desc&limit=1")
        if prev:
            return {"ok": True, "already_used": True, "previous_token": prev[0]["token"],
                    "message": "Cet email a d\u00e9j\u00e0 utilis\u00e9 son analyse gratuite."}
        # Email used but no unlocked analysis found — allow retry
        pass

    # Check remaining slots
    rows = await _supabase_select("settings", "key=eq.free_slots&select=value")
    remaining = int(rows[0]["value"]) if rows else 0
    if remaining <= 0:
        raise HTTPException(410, "Plus d'analyses gratuites disponibles.")

    # Check analysis exists
    analyses = await _supabase_select("analyses", f"token=eq.{analyse_token}&select=token,unlocked")
    if not analyses:
        raise HTTPException(404, "Analyse introuvable.")
    if analyses[0].get("unlocked"):
        return {"ok": True, "message": "Analyse d\u00e9j\u00e0 d\u00e9bloqu\u00e9e."}

    # Unlock analysis
    await _supabase_update("analyses", f"token=eq.{analyse_token}", {"unlocked": True})

    # Record email in waitlist
    try:
        await _supabase_insert("waitlist", {"email": email, "source": "free_slot"})
    except Exception:
        pass  # email might already exist in waitlist from before

    # Decrement free slots
    await _supabase_update("settings", "key=eq.free_slots", {"value": str(remaining - 1)})

    # Send email
    await send_unlock_email(email, analyse_token)

    return {"ok": True, "free_slots_remaining": remaining - 1}


@app.post("/api/analyse")
async def create_analyse(
    file: UploadFile = File(...),
    email: str = Form(...),
    secteur: str = Form(""),
    admin: str = Form(""),
):
    """Upload PDF → extract → compute ratios → Claude analysis → store in Supabase."""
    is_admin = bool(ADMIN_SECRET and admin == ADMIN_SECRET)
    if is_admin:
        import logging
        logging.warning("ADMIN MODE — analyse for %s", email)
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "Seuls les fichiers PDF sont acceptés.")

    # Save to temp file
    content = await file.read()
    pdf_hash = hashlib.sha256(content).hexdigest()

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Check consolidated
        is_consolidated = detect_consolidated(tmp_path)

        # Extract financial data
        extracted = extract_bnb_pdf(tmp_path)
    finally:
        os.unlink(tmp_path)  # RGPD: delete PDF immediately

    if 'error' in extracted.get('exercice', {}):
        raise HTTPException(422, f"Erreur d'extraction : {extracted['exercice']['error']}")

    data_n = extracted['exercice']
    data_n1 = extracted['exercice_precedent']
    has_n1 = bool(data_n1 and any(v for k, v in data_n1.items() if k not in ('_ca_is_marge_brute',) and v))

    # Compute ratios for current year
    ratios = compute_ratios(data_n, secteur)
    ratios_n1 = compute_ratios(data_n1, secteur) if has_n1 else None

    # EBITDA multi-year
    ebitda_n = ratios['rentabilite']['ebitda']
    ebitda_n1 = ratios_n1['rentabilite']['ebitda'] if ratios_n1 else None
    nb_exercices = 2 if has_n1 else 1
    annee_n = extracted.get('annee_exercice')
    annee_n1 = extracted.get('annee_precedente')

    # EBITDA variation
    ebitda_variation = None
    if ebitda_n1 and ebitda_n1 != 0:
        ebitda_variation = round(abs(ebitda_n - ebitda_n1) / abs(ebitda_n1), 4)

    # ── CORRECTION 2: single EBITDA reference for valuation ──
    if nb_exercices >= 2 and ebitda_n1 is not None:
        ebitda_reference = round((ebitda_n + ebitda_n1) / 2, 2)
        ebitda_reference_label = f"Moyenne {annee_n}-{annee_n1}"
    else:
        ebitda_reference = ebitda_n
        ebitda_reference_label = f"{annee_n} seul"

    secteur_key = secteur or ''
    multiples = SECTEUR_MULTIPLES.get(secteur_key, {'low': 4, 'high': 8, 'default': 5})
    dette_nette = ratios['structure']['dette_nette']
    multiple = multiples['default']

    ev_ebitda = round(ebitda_reference * multiple, 2) if ebitda_reference > 0 else 0
    actif_net = ratios['valorisation']['valeur_capitaux_propres']

    # Compute DCF if we have 2 years
    dcf_equity = None
    if has_n1:
        dcf = compute_dcf([data_n1, data_n])
        if dcf:
            ratios['valorisation']['dcf'] = dcf
            dcf_equity = round(dcf['valeur_dcf'] - dette_nette, 2)

    # CORRECTION 6: fourchette cohérente
    # Borne basse = min(ev_ebitda, actif_net) × 0.9
    # Borne haute = max(ev_ebitda, dcf) × 1.05 if stable, else max(ev_ebitda, actif_net) × 1.05
    vals_for_low = [v for v in [ev_ebitda, actif_net] if v and v > 0]
    fourchette_low = round(min(vals_for_low) * 0.9, 2) if vals_for_low else 0

    is_stable = ebitda_variation is None or ebitda_variation <= 0.30
    if is_stable and dcf_equity and dcf_equity > 0:
        vals_for_high = [v for v in [ev_ebitda, dcf_equity] if v and v > 0]
        fourchette_methode = "EV/EBITDA + DCF"
    else:
        vals_for_high = [v for v in [ev_ebitda, actif_net] if v and v > 0]
        fourchette_methode = "EV/EBITDA + Actif net"
    fourchette_high = round(max(vals_for_high) * 1.05, 2) if vals_for_high else 0

    # Unified valorisation object
    valorisation_unified = {
        'ebitda_reference': ebitda_reference,
        'ebitda_reference_label': ebitda_reference_label,
        'nb_exercices': nb_exercices,
        'multiple_sectoriel': multiple,
        'ev_ebitda': ev_ebitda,
        'dcf': dcf_equity,
        'actif_net': actif_net,
        'fourchette_basse': fourchette_low,
        'fourchette_haute': fourchette_high,
        'fourchette_methode': fourchette_methode,
        'dette_nette': dette_nette,
    }

    # Update ratios with unified values
    ratios['valorisation_resume'] = {
        'ebitda': ebitda_reference,
        'ebitda_reference': ebitda_reference,
        'ebitda_reference_label': ebitda_reference_label,
        'multiple': multiple,
        'ev_ebitda': ev_ebitda,
        'dette_nette': dette_nette,
        'equity_ev_ebitda': round(ev_ebitda - dette_nette, 2) if ev_ebitda else 0,
        'capitaux_propres_comptables': actif_net,
        'fourchette_equity_low': fourchette_low,
        'fourchette_equity_high': fourchette_high,
        'dcf_ev': dcf['valeur_dcf'] if has_n1 and dcf_equity else None,
        'dcf_equity': dcf_equity,
    }

    # Claude AI analysis (CORRECTION 3: strict prompt)
    try:
        ai_analysis = run_claude_analysis(ratios, data_n, secteur, valorisation_unified)
    except Exception:
        ai_analysis = {
            'synthese': 'Analyse IA indisponible.',
            'points_forts': [], 'points_attention': [], 'risques': [],
            'recommandations': [], 'valorisation_commentaire': '',
            'score_sante': 50,
        }

    # Deterministic score with deductions (CORRECTION 1)
    score_result = compute_score(
        ratios, secteur, comptes_data=data_n,
        nb_exercices=nb_exercices, ebitda_variation=ebitda_variation
    )
    score_sante = score_result['score']
    score_deductions = score_result['score_deductions']

    # Build full analysis payload
    token = str(uuid.uuid4())
    full_data = {
        'comptes': data_n,
        'comptes_precedent': data_n1,
        'annee': annee_n,
        'annee_precedente': annee_n1,
        'annees_disponibles': [annee_n1, annee_n] if has_n1 else [annee_n],
        'nb_exercices': nb_exercices,
        'ebitda_n': ebitda_n,
        'ebitda_n1': ebitda_n1,
        'ebitda_reference': ebitda_reference,
        'ebitda_reference_label': ebitda_reference_label,
        'ebitda_variation': ebitda_variation,
        'valorisation': valorisation_unified,
        'ratios': ratios,
        'score_sante': score_sante,
        'score_deductions': score_deductions,
        'ai_analysis': ai_analysis,
        'secteur': secteur,
        'is_structure_particuliere': secteur in STRUCTURE_PARTICULIERE,
        'is_consolidated': is_consolidated,
    }

    # Store in Supabase
    record = await _supabase_insert("analyses", {
        "token": token,
        "email": email.strip().lower(),
        "pdf_hash": pdf_hash,
        "data_json": full_data,
        "unlocked": is_admin,
    })

    # Common response fields
    multi = {
        "nb_exercices": nb_exercices,
        "annee": annee_n,
        "annee_precedente": annee_n1,
        "annees_disponibles": [annee_n1, annee_n] if has_n1 else [annee_n],
        "ebitda_n": ebitda_n,
        "ebitda_n1": ebitda_n1,
        "ebitda_reference": ebitda_reference,
        "ebitda_reference_label": ebitda_reference_label,
        "ebitda_variation": ebitda_variation,
        "score_deductions": score_deductions,
        "valorisation": valorisation_unified,
    }

    # Admin mode → return full results immediately
    if is_admin:
        return {
            "token": token,
            "is_consolidated": is_consolidated,
            "score_sante": score_sante,
            "unlocked": True,
            **multi,
            "freemium": {
                "ebitda": ratios['rentabilite']['ebitda'],
                "roe": ratios['rentabilite']['roe'],
                "liquidite_generale": ratios['liquidite']['liquidite_generale'],
                "solvabilite": ratios['structure']['solvabilite'],
            },
            "valorisation_floue": {
                "fourchette_low": ratios.get('valorisation_resume', {}).get('fourchette_equity_low'),
                "fourchette_high": ratios.get('valorisation_resume', {}).get('fourchette_equity_high'),
            },
            "full": {
                "comptes": data_n,
                "ratios": ratios,
                "ai_analysis": ai_analysis,
                "valorisation_resume": ratios.get('valorisation_resume', {}),
                "secteur": secteur,
            },
        }

    # Return freemium preview
    vr = ratios.get('valorisation_resume', {})
    return {
        "token": token,
        "is_consolidated": is_consolidated,
        "score_sante": score_sante,
        "unlocked": False,
        **multi,
        "freemium": {
            "ebitda": ratios['rentabilite']['ebitda'],
            "roe": ratios['rentabilite']['roe'],
            "liquidite_generale": ratios['liquidite']['liquidite_generale'],
            "solvabilite": ratios['structure']['solvabilite'],
        },
        "valorisation_floue": {
            "fourchette_low": vr.get('fourchette_equity_low'),
            "fourchette_high": vr.get('fourchette_equity_high'),
        },
    }


@app.get("/api/analyse/{token}")
async def get_analyse(token: str):
    """Get analysis results — full if unlocked, preview if not."""
    rows = await _supabase_select("analyses", f"token=eq.{token}&select=*")
    if not rows:
        raise HTTPException(404, "Analyse introuvable.")
    row = rows[0]
    data = row["data_json"] if isinstance(row["data_json"], dict) else json.loads(row["data_json"])
    unlocked = row.get("unlocked", False)

    ratios = data.get('ratios', {})
    ai = data.get('ai_analysis', {})
    vr = ratios.get('valorisation_resume', {})

    valo = data.get('valorisation', {})
    result = {
        "token": token,
        "annee": data.get('annee'),
        "annee_precedente": data.get('annee_precedente'),
        "annees_disponibles": data.get('annees_disponibles', [data.get('annee')]),
        "nb_exercices": data.get('nb_exercices', 1),
        "ebitda_n": data.get('ebitda_n'),
        "ebitda_n1": data.get('ebitda_n1'),
        "ebitda_reference": data.get('ebitda_reference'),
        "ebitda_reference_label": data.get('ebitda_reference_label'),
        "ebitda_variation": data.get('ebitda_variation'),
        "valorisation": valo,
        "score_deductions": data.get('score_deductions', []),
        "is_consolidated": data.get('is_consolidated', False),
        "is_structure_particuliere": data.get('is_structure_particuliere', False),
        "score_sante": data.get('score_sante') or ai.get('score_sante', 50),
        "unlocked": unlocked,
        "freemium": {
            "ebitda": ratios.get('rentabilite', {}).get('ebitda'),
            "roe": ratios.get('rentabilite', {}).get('roe'),
            "liquidite_generale": ratios.get('liquidite', {}).get('liquidite_generale'),
            "solvabilite": ratios.get('structure', {}).get('solvabilite'),
        },
        "valorisation_floue": {
            "fourchette_low": valo.get('fourchette_basse') or vr.get('fourchette_equity_low'),
            "fourchette_high": valo.get('fourchette_haute') or vr.get('fourchette_equity_high'),
        },
    }

    if unlocked:
        result["full"] = {
            "comptes": data.get('comptes'),
            "ratios": ratios,
            "ai_analysis": ai,
            "valorisation_resume": vr,
            "secteur": data.get('secteur', ''),
        }

    return result


# ── Stripe ──────────────────────────────────────────────────────────────────

@app.post("/api/stripe/checkout")
async def create_checkout(request: Request):
    body = await request.json()
    token = body.get("token")
    if not token:
        raise HTTPException(400, "Token manquant.")

    rows = await _supabase_select("analyses", f"token=eq.{token}&select=token,email,unlocked")
    if not rows:
        raise HTTPException(404, "Analyse introuvable.")
    if rows[0].get("unlocked"):
        raise HTTPException(400, "Analyse déjà débloquée.")

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price": STRIPE_PRICE_ID,
            "quantity": 1,
        }],
        mode="payment",
        success_url=f"{FRONTEND_URL}/resultats?token={token}",
        cancel_url=f"{FRONTEND_URL}/resultats?token={token}",
        customer_email=rows[0]["email"],
        metadata={"analyse_token": token},
    )
    return {"checkout_url": session.url}


@app.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(400, "Invalid signature.")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        token = session.get("metadata", {}).get("analyse_token")
        if token:
            await _supabase_update("analyses", f"token=eq.{token}", {"unlocked": True, "stripe_session_id": session["id"]})

            rows = await _supabase_select("analyses", f"token=eq.{token}&select=email")
            if rows:
                await send_unlock_email(rows[0]["email"], token)

    return {"received": True}


# ── Sectors list ────────────────────────────────────────────────────────────

@app.get("/api/secteurs")
async def list_secteurs():
    return {"secteurs": list(SECTEUR_MULTIPLES.keys())}


# ── Promo codes ─────────────────────────────────────────────────────────────

@app.post("/api/redeem-code")
async def redeem_code(request: Request):
    body = await request.json()
    code = (body.get("code") or "").strip().upper()
    analyse_token = body.get("token")

    if not code or not analyse_token:
        raise HTTPException(400, "Code et token requis.")

    # Check code exists and is valid
    rows = await _supabase_select("promo_codes", f"code=eq.{code}&select=*")
    if not rows:
        raise HTTPException(404, "Code invalide.")
    promo = rows[0]

    # Check expiry
    if promo.get("expires_at"):
        from datetime import datetime, timezone
        expires = datetime.fromisoformat(promo["expires_at"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > expires:
            raise HTTPException(410, "Code expiré.")

    # Check usage
    max_uses = promo.get("max_uses") or 0
    used = promo.get("used_count") or 0
    if max_uses > 0 and used >= max_uses:
        raise HTTPException(410, "Code déjà utilisé.")

    # Check analyse exists and not already unlocked
    analyses = await _supabase_select("analyses", f"token=eq.{analyse_token}&select=token,unlocked")
    if not analyses:
        raise HTTPException(404, "Analyse introuvable.")
    if analyses[0].get("unlocked"):
        return {"ok": True, "message": "Analyse déjà débloquée."}

    # Unlock + increment
    await _supabase_update("analyses", f"token=eq.{analyse_token}", {"unlocked": True})
    await _supabase_update("promo_codes", f"code=eq.{code}", {"used_count": used + 1})

    # Send unlock email
    email_rows = await _supabase_select("analyses", f"token=eq.{analyse_token}&select=email")
    if email_rows:
        await send_unlock_email(email_rows[0]["email"], analyse_token)

    return {"ok": True, "message": "Analyse débloquée."}


# ── Admin ───────────────────────────────────────────────────────────────────

@app.get("/api/admin/codes")
async def admin_list_codes(key: str = ""):
    if key != ADMIN_SECRET:
        raise HTTPException(403, "Accès refusé.")
    rows = await _supabase_select("promo_codes", "select=*&order=created_at.desc")
    return {"codes": rows}


@app.post("/api/admin/codes")
async def admin_create_code(request: Request, key: str = ""):
    if key != ADMIN_SECRET:
        raise HTTPException(403, "Accès refusé.")
    body = await request.json()
    code = (body.get("code") or "").strip().upper()
    max_uses = body.get("max_uses", 1)
    expires_at = body.get("expires_at")

    if not code:
        raise HTTPException(400, "Code requis.")

    record = await _supabase_insert("promo_codes", {
        "code": code,
        "max_uses": max_uses,
        "used_count": 0,
        "expires_at": expires_at,
    })
    return {"ok": True, "code": record}
