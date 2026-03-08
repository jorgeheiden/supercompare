import asyncio
import sys
import re

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SuperCompare API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def root():
    return {"message": "SuperCompare API running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/search")
async def search_products(q: str = Query(..., min_length=2)):
    return await do_search(q)

@app.get("/search")
async def search_products_alt(q: str = Query(..., min_length=2)):
    return await do_search(q)

async def do_search(q: str):
    logger.info(f"Searching: {q}")
    try:
        from scraper import scrape_dia, scrape_coto
        dia_products, coto_products = await asyncio.gather(
            scrape_dia(q.strip()), scrape_coto(q.strip()), return_exceptions=True
        )
        if isinstance(dia_products, Exception):
            logger.error(f"DIA: {dia_products}"); dia_products = []
        if isinstance(coto_products, Exception):
            logger.error(f"COTO: {coto_products}"); coto_products = []
    except Exception as e:
        logger.error(f"Error: {e}"); dia_products = []; coto_products = []

    comparisons = build_smart_comparisons(dia_products, coto_products)
    return {
        "query": q,
        "dia_products": dia_products,
        "coto_products": coto_products,
        "comparisons": comparisons,
        "total_dia": len(dia_products),
        "total_coto": len(coto_products)
    }


# ═══════════════════════════════════════════════════════════════════
#  KNOWN BRANDS — if a brand token is detected, it MUST match
# ═══════════════════════════════════════════════════════════════════

# Each entry: set of aliases that all map to the same canonical brand
BRANDS = [
    {'gallo'},
    {'ala', 'molinos ala', 'molinos'},
    {'luchetti', 'lucchetti'},
    {'canuelas', 'cañuelas'},
    {'marolio'},
    {'arcor'},
    {'ledesma'},
    {'chango'},
    {'dos hermanos', 'dos hnos', 'hnos'},
    {'carmabe'},
    {'cuquets'},
    {'maximo', 'máximo'},
    {'ciudad del lago'},
    {'vanguardia'},
    {'tregar'},
    {'dia', 'super dia'},
    {'la serenisima', 'serenisima'},
    {'sancor'},
    {'ilolay'},
    {'knorr'},
    {'maggi'},
    {'nestle', 'nestlé'},
    {'coca cola', 'coca-cola'},
    {'colgate'},
    {'dove'},
    {'nivea'},
]

# Build lookup: alias -> canonical brand id (index in BRANDS list)
_BRAND_LOOKUP: dict[str, int] = {}
for _idx, _aliases in enumerate(BRANDS):
    for _alias in _aliases:
        _BRAND_LOOKUP[_alias] = _idx

# Words to strip before comparing (decorative / packaging / stopwords)
REMOVE_WORDS = {
    'seleccion', 'premium', 'clasico', 'especial', 'tradicional', 'natural',
    'original', 'light', 'extra', 'super', 'ultra', 'nuevo', 'nueva',
    'dorado', 'dorada', 'enriquecido', 'enriquecida', 'bolsa', 'paquete',
    'caja', 'pack', 'sobre', 'sachet', 'brik', 'lata', 'frasco', 'botella',
    'de', 'la', 'el', 'en', 'con', 'sin', 'para', 'por', 'los', 'las',
    'un', 'una', 'y', 'e', 'x', 'paq',
}


def _accent_strip(s: str) -> str:
    return s.translate(str.maketrans('áéíóúüñ', 'aeiouun'))


def normalize_weight(s: str) -> str:
    s = s.lower()
    s = re.sub(r'(\d+),(\d+)', r'\1.\2', s)
    for pat, fn in [
        (r'(\d+(?:\.\d+)?)\s*kg\b',      lambda m: f"{int(float(m.group(1))*1000)}g"),
        (r'(\d+(?:\.\d+)?)\s*gr?\b',     lambda m: f"{int(float(m.group(1)))}g"),
        (r'(\d+(?:\.\d+)?)\s*litros?\b', lambda m: f"{int(float(m.group(1))*1000)}ml"),
        (r'(\d+(?:\.\d+)?)\s*lt?\b',     lambda m: f"{int(float(m.group(1))*1000)}ml"),
        (r'(\d+(?:\.\d+)?)\s*ml\b',      lambda m: f"{int(float(m.group(1)))}ml"),
        (r'(\d+(?:\.\d+)?)\s*cc\b',      lambda m: f"{int(float(m.group(1)))}ml"),
    ]:
        m = re.search(pat, s)
        if m:
            try: return fn(m)
            except: pass
    return ''


def parse_product(name: str) -> dict:
    """
    Parse a product name into structured fields:
    - brand_id: canonical brand index (or None)
    - weight: normalized weight string (or '')
    - tokens: remaining descriptive tokens (sorted set)
    """
    s = _accent_strip(name.lower().strip())
    s = re.sub(r'[^\w\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()

    # Detect brand (longest match first)
    brand_id = None
    matched_brand_tokens = set()
    for alias in sorted(_BRAND_LOOKUP.keys(), key=len, reverse=True):
        if re.search(r'\b' + re.escape(alias) + r'\b', s):
            brand_id = _BRAND_LOOKUP[alias]
            # Mark brand tokens for removal
            for t in alias.split():
                matched_brand_tokens.add(t)
            break

    weight = normalize_weight(s)

    # Remove weight tokens, numbers, brand tokens, stopwords
    s = re.sub(r'\d+(?:\.\d+)?\s*(?:kg|gr?|litros?|lt?|ml|cc)\b', '', s)
    s = re.sub(r'\b\d+\b', '', s)
    tokens = s.split()
    tokens = [t for t in tokens
              if t not in REMOVE_WORDS
              and t not in matched_brand_tokens
              and len(t) > 1]
    tokens = sorted(set(tokens))

    return {'brand_id': brand_id, 'weight': weight, 'tokens': tokens}


def similarity(a: str, b: str) -> float:
    pa = parse_product(a)
    pb = parse_product(b)

    # ── HARD DISQUALIFIERS ───────────────────────────────────────────
    # 1. Both have a known brand → brands MUST match
    if pa['brand_id'] is not None and pb['brand_id'] is not None:
        if pa['brand_id'] != pb['brand_id']:
            logger.debug(f"BRAND MISMATCH: '{a}' vs '{b}'")
            return 0.0

    # 2. Both have weight → weights MUST match
    if pa['weight'] and pb['weight']:
        if pa['weight'] != pb['weight']:
            logger.debug(f"WEIGHT MISMATCH: {pa['weight']} vs {pb['weight']}")
            return 0.0

    # ── SOFT SCORE on remaining descriptive tokens ───────────────────
    ta = set(pa['tokens'])
    tb = set(pb['tokens'])

    if not ta and not tb:
        # Only brand/weight, already matched above
        return 1.0

    inter = ta & tb
    union = ta | tb
    jaccard = len(inter) / len(union) if union else 0.0

    smaller = ta if len(ta) <= len(tb) else tb
    larger  = tb if len(ta) <= len(tb) else ta
    coverage = len(smaller & larger) / len(smaller) if smaller else 0.0

    score = 0.5 * jaccard + 0.5 * coverage

    logger.debug(
        f"SIM '{a}' vs '{b}': "
        f"brand={pa['brand_id']}=={pb['brand_id']} "
        f"weight={pa['weight']}=={pb['weight']} "
        f"tokens={ta}&{tb} score={score:.2f}"
    )
    return score


# ═══════════════════════════════════════════════════════════════════
#  COMPARISON BUILDER
# ═══════════════════════════════════════════════════════════════════

MATCH_THRESHOLD = 0.45  # Lower threshold is fine now that hard rules block bad matches

def build_smart_comparisons(dia: list, coto: list) -> list:
    comparisons = []
    coto_used = set()

    for dia_p in dia:
        best_score = 0.0
        best_coto  = None
        best_idx   = -1

        for i, coto_p in enumerate(coto):
            if i in coto_used:
                continue
            s = similarity(dia_p['name'], coto_p['name'])
            if s > best_score:
                best_score = s
                best_coto  = coto_p
                best_idx   = i

        logger.info(
            f"DIA '{dia_p['name']}' → "
            f"COTO '{best_coto['name'] if best_coto else 'none'}' "
            f"score={best_score:.2f} {'✓' if best_score >= MATCH_THRESHOLD else '✗'}"
        )

        if best_score >= MATCH_THRESHOLD and best_coto:
            coto_used.add(best_idx)
            comparisons.append(make_comparison(dia_p, best_coto))
        else:
            comparisons.append(make_comparison(dia_p, None))

    for i, coto_p in enumerate(coto):
        if i not in coto_used:
            comparisons.append(make_comparison(None, coto_p))

    comparisons.sort(key=lambda c: (
        0 if (c['dia'] and c['coto']) else 1,
        -(c['savings'] or 0)
    ))
    return comparisons


def make_comparison(dia_p, coto_p) -> dict:
    dia_price  = dia_p.get('price')  if dia_p  else None
    coto_price = coto_p.get('price') if coto_p else None
    cheaper = savings = savings_pct = None

    if dia_price and coto_price:
        if dia_price < coto_price:
            cheaper = "dia"
            savings = round(coto_price - dia_price, 2)
            savings_pct = round(savings / coto_price * 100, 1)
        elif coto_price < dia_price:
            cheaper = "coto"
            savings = round(dia_price - coto_price, 2)
            savings_pct = round(savings / dia_price * 100, 1)
        else:
            cheaper = "equal"
            savings = 0
    elif dia_price:
        cheaper = "dia"
    elif coto_price:
        cheaper = "coto"

    return {
        "name": (dia_p or coto_p or {}).get('name', ''),
        "dia": dia_p,
        "coto": coto_p,
        "cheaper": cheaper,
        "savings": savings,
        "savings_pct": savings_pct,
    }
