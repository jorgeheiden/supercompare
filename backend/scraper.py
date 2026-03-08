import httpx
import asyncio
import re
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS_DIA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-AR,es;q=0.9",
    "Referer": "https://diaonline.supermercadosdia.com.ar/",
}


def parse_price(price_str) -> Optional[float]:
    if price_str is None:
        return None
    if isinstance(price_str, (int, float)):
        return float(price_str)
    try:
        cleaned = re.sub(r'[^\d,.]', '', str(price_str))
        if not cleaned:
            return None

        # Format: 1.234,56 → thousands=dot, decimal=comma
        if ',' in cleaned and '.' in cleaned:
            # dot comes before comma → Argentine format: 1.234,56
            if cleaned.index('.') < cleaned.index(','):
                return float(cleaned.replace('.', '').replace(',', '.'))
            # comma before dot → English format: 1,234.56
            else:
                return float(cleaned.replace(',', ''))

        # Only comma → decimal comma: 682,50
        elif ',' in cleaned:
            return float(cleaned.replace(',', '.'))

        # Only dot → decimal dot: 682.50
        elif '.' in cleaned:
            return float(cleaned)

        return float(cleaned)
    except (ValueError, AttributeError):
        logger.warning(f"Failed to parse price: {price_str}")
        return None


async def scrape_dia(query: str) -> List[Dict]:
    products = []
    try:
        url = "https://diaonline.supermercadosdia.com.ar/api/catalog_system/pub/products/search"
        params = {"ft": query, "_from": "0", "_to": "23"}
        async with httpx.AsyncClient(headers=HEADERS_DIA, timeout=25, follow_redirects=True) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        for item in data[:24]:
            try:
                name = item.get("productName", "")
                link = item.get("link", "")
                price = None
                original_price = None
                image = None
                items = item.get("items", [])
                if items:
                    first_item = items[0]
                    images = first_item.get("images", [])
                    if images:
                        image = images[0].get("imageUrl")
                    sellers = first_item.get("sellers", [])
                    if sellers:
                        comm_offer = sellers[0].get("commertialOffer", {})
                        price = comm_offer.get("Price")
                        original_price = comm_offer.get("ListPrice")
                        if original_price == price:
                            original_price = None
                discount = None
                if price and original_price and original_price > price:
                    discount = round(((original_price - price) / original_price) * 100, 1)
                if name and price:
                    products.append({
                        "name": name,
                        "price": float(price),
                        "original_price": float(original_price) if original_price else None,
                        "image": image,
                        "discount": discount,
                        "on_sale": discount is not None and discount > 0,
                        "url": f"https://diaonline.supermercadosdia.com.ar{link}" if link.startswith("/") else link,
                        "store": "dia"
                    })
            except Exception as e:
                logger.warning(f"DIA item error: {e}")
        logger.info(f"DIA: {len(products)} products for '{query}'")
    except Exception as e:
        logger.error(f"DIA error: {e}")
    return products


def _run_coto_sync(query: str) -> List[Dict]:
    from playwright.sync_api import sync_playwright
    products = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="es-AR",
                viewport={"width": 1280, "height": 900},
            )
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
            page = context.new_page()
            search_url = f"https://www.cotodigital.com.ar/sitios/cdigi/productos/{query.replace(' ', '%20')}"
            logger.info(f"COTO: navigating to {search_url}")
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            try:
                page.wait_for_selector('.card-container', timeout=15000)
            except Exception:
                logger.warning("COTO: .card-container timeout")
            time.sleep(2)
            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, 'lxml')
        products = parse_coto_html(soup)
        logger.info(f"COTO: {len(products)} products for '{query}'")
    except Exception as e:
        logger.error(f"COTO sync error: {e}")
    return products


async def scrape_coto(query: str) -> List[Dict]:
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as executor:
        products = await loop.run_in_executor(executor, _run_coto_sync, query)
    return products


def parse_coto_html(soup: BeautifulSoup) -> List[Dict]:
    products = []
    cards = soup.select('.card-container')
    logger.info(f"COTO HTML: {len(cards)} cards found")

    for card in cards[:24]:
        try:
            name = card.get('data-cnstrc-item-name', '').strip()
            if not name:
                name_el = card.select_one('.nombre-producto')
                name = name_el.get_text(strip=True) if name_el else None

            # data-cnstrc-item-price is always a plain number e.g. "682.5" or "1163.5"
            price_raw = card.get('data-cnstrc-item-price')
            try:
                price = float(price_raw) if price_raw else None
            except (ValueError, TypeError):
                price = None
            # Fallback to h4 text (Argentine format e.g. "$682,50")
            if not price:
                price_el = card.select_one('h4.card-title')
                price = parse_price(price_el.get_text(strip=True)) if price_el else None

            if not name or not price or price <= 0:
                continue

            original_price = None
            for small in card.select('small'):
                text = small.get_text(strip=True)
                if 'Precio regular' in text:
                    orig_val = parse_price(text)
                    if orig_val and orig_val > price:
                        original_price = orig_val
                    break

            img_el = card.select_one('.product-image, img')
            image = None
            if img_el:
                image = img_el.get('src') or img_el.get('data-src')
                if image and not image.startswith('http'):
                    image = f"https://www.cotodigital.com.ar{image}"

            link_el = card.select_one('a[href]:not([href="javascript:void(0)"])')
            href = link_el.get('href', '') if link_el else ''
            url_p = f"https://www.cotodigital.com.ar{href}" if href.startswith('/') else href

            discount = None
            if original_price and original_price > price:
                discount = round(((original_price - price) / original_price) * 100, 1)

            products.append({
                "name": name,
                "price": price,
                "original_price": original_price,
                "image": image,
                "discount": discount,
                "on_sale": discount is not None and discount > 0,
                "url": url_p or None,
                "store": "coto"
            })
        except Exception as e:
            logger.warning(f"COTO card error: {e}")
    return products
