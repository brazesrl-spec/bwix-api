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
from ratios import compute_ratios, compute_dcf, compute_score, SECTEUR_MULTIPLES

# ── Config ──────────────────────────────────────────────────────────────────
SUPABASE_URL = os.environ["SUPABASE_URL"].strip()
SUPABASE_KEY = os.environ["SUPABASE_KEY"].strip()
STRIPE_SECRET = os.environ["STRIPE_SECRET_KEY"].strip()
STRIPE_WEBHOOK_SECRET = os.environ["STRIPE_WEBHOOK_SECRET"].strip()
RESEND_API_KEY = os.environ["RESEND_API_KEY"].strip()
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"].strip()
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://bwixapp.vercel.app").strip()
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "").strip()

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
def run_claude_analysis(ratios_data: dict, comptes_data: dict, secteur: str) -> dict:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    vr = ratios_data.get('valorisation_resume', {})
    ia_summary = {
        'secteur': secteur,
        'schema_abrege': ratios_data.get('schema_abrege', False),
        'rentabilite': ratios_data.get('rentabilite', {}),
        'structure': ratios_data.get('structure', {}),
        'liquidite': ratios_data.get('liquidite', {}),
        'valorisation': {
            'ebitda': vr.get('ebitda'),
            'multiple_sectoriel': vr.get('multiple'),
            'ev_ebitda': vr.get('ev_ebitda'),
            'dette_nette': vr.get('dette_nette'),
            'equity_ev_ebitda': vr.get('equity_ev_ebitda'),
            'capitaux_propres_comptables': vr.get('capitaux_propres_comptables'),
            'fourchette_equity': f"{vr.get('fourchette_equity_low', 0):,.0f} — {vr.get('fourchette_equity_high', 0):,.0f}",
            'dcf_ev': vr.get('dcf_ev'),
            'dcf_equity': vr.get('dcf_equity'),
        },
        'indicators': ratios_data.get('indicators', {}),
    }

    context = (
        f"Données comptables :\n{json.dumps(comptes_data, indent=2, ensure_ascii=False)}\n\n"
        f"Ratios et valorisation :\n{json.dumps(ia_summary, indent=2, ensure_ascii=False)}"
    )

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system="""Tu es un analyste financier expert en PME belges.
Analyse ces données financières de façon claire, structurée et actionnable pour le dirigeant.
Pas de jargon inutile. Sois direct sur les points forts, les risques et les recommandations prioritaires.

IMPORTANT :
- Utilise EXACTEMENT les valeurs de valorisation fournies dans le JSON. Ne recalcule pas.
- Si schema_abrege=true, ne commente pas les marges (EBITDA, nette).
- La dette nette fournie est la dette nette BANCAIRE retraitée.

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


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/health")
@app.get("/api/health")
async def health():
    return {"status": "ok"}


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

    # Compute ratios for current year
    ratios = compute_ratios(data_n, secteur)

    # Compute DCF if we have 2 years
    if data_n1 and any(v for k, v in data_n1.items() if k not in ('_ca_is_marge_brute',) and v):
        dcf = compute_dcf([data_n1, data_n])
        if dcf:
            ratios['valorisation']['dcf'] = dcf
            dette_nette = ratios['structure']['dette_nette']
            ratios['valorisation_resume']['dcf_ev'] = dcf['valeur_dcf']
            ratios['valorisation_resume']['dcf_equity'] = round(dcf['valeur_dcf'] - dette_nette, 2)

    # Claude AI analysis
    try:
        ai_analysis = run_claude_analysis(ratios, data_n, secteur)
    except Exception:
        ai_analysis = {
            'synthese': 'Analyse IA indisponible.',
            'points_forts': [], 'points_attention': [], 'risques': [],
            'recommandations': [], 'valorisation_commentaire': '',
            'score_sante': 50,
        }

    # Deterministic score from ratios (not Claude)
    score_sante = compute_score(ratios)

    # Build full analysis payload
    token = str(uuid.uuid4())
    full_data = {
        'comptes': data_n,
        'comptes_precedent': data_n1,
        'annee': extracted.get('annee_exercice'),
        'annee_precedente': extracted.get('annee_precedente'),
        'ratios': ratios,
        'score_sante': score_sante,
        'ai_analysis': ai_analysis,
        'secteur': secteur,
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

    # Admin mode → return full results immediately
    if is_admin:
        return {
            "token": token,
            "is_consolidated": is_consolidated,
            "annee": extracted.get('annee_exercice'),
            "score_sante": score_sante,
            "unlocked": True,
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
    preview = {
        "token": token,
        "is_consolidated": is_consolidated,
        "annee": extracted.get('annee_exercice'),
        "score_sante": score_sante,
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
        "unlocked": False,
    }
    return preview


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

    result = {
        "token": token,
        "annee": data.get('annee'),
        "is_consolidated": data.get('is_consolidated', False),
        "score_sante": data.get('score_sante') or ai.get('score_sante', 50),
        "unlocked": unlocked,
        "freemium": {
            "ebitda": ratios.get('rentabilite', {}).get('ebitda'),
            "roe": ratios.get('rentabilite', {}).get('roe'),
            "liquidite_generale": ratios.get('liquidite', {}).get('liquidite_generale'),
            "solvabilite": ratios.get('structure', {}).get('solvabilite'),
        },
        "valorisation_floue": {
            "fourchette_low": vr.get('fourchette_equity_low'),
            "fourchette_high": vr.get('fourchette_equity_high'),
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
            "price": "price_1TJK3M1XczkPkPz652TlUn4J",
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

            # Send email with link
            rows = await _supabase_select("analyses", f"token=eq.{token}&select=email")
            if rows:
                email = rows[0]["email"]
                link = f"{FRONTEND_URL}/analyse.html?token={token}"
                await send_email(
                    email,
                    "Votre analyse BWIX est prête",
                    f"""<div style="font-family:Inter,sans-serif;max-width:600px;margin:0 auto;padding:40px 20px">
                    <h1 style="color:#1e3a5f">Votre analyse BWIX</h1>
                    <p>Merci pour votre achat. Votre analyse financière complète est désormais accessible.</p>
                    <p><a href="{link}" style="display:inline-block;background:#00c896;color:#0b1929;padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:600">
                    Voir mon analyse complète</a></p>
                    <p style="color:#8fa3bf;font-size:14px;margin-top:24px">
                    Ce lien est unique et reste accessible à tout moment.</p>
                    <hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0">
                    <p style="color:#8fa3bf;font-size:12px">
                    BWIX est un outil d'aide à la décision indicatif. Les résultats ne constituent pas un conseil financier ou comptable.</p>
                    </div>""",
                )

    return {"received": True}


# ── Sectors list ────────────────────────────────────────────────────────────

@app.get("/api/secteurs")
async def list_secteurs():
    return {"secteurs": list(SECTEUR_MULTIPLES.keys())}
