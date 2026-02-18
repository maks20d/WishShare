import json
import logging
import re
from urllib.parse import urljoin, urlparse

from fastapi import APIRouter
from pydantic import BaseModel
from bs4 import BeautifulSoup
import httpx

from app.core.enhanced_parser import parse_product_from_url
from app.core.config import settings


router = APIRouter(tags=["og"])
logger = logging.getLogger("wishshare.og")


class OgPreviewRequest(BaseModel):
    url: str


class OgPreviewResponse(BaseModel):
    url: str
    title: str | None = None
    price: float | None = None
    image_url: str | None = None
    description: str | None = None
    brand: str | None = None
    currency: str | None = None
    availability: str | None = None


_REJECT_TITLE_PARTS = (
    "почти готово",
    "загрузка",
    "just a moment",
    "loading",
    "attention required",
    "access denied",
    "captcha",
    "robot check",
    "проверка, что вы человек",
    "cloudflare",
    "enable javascript",
    "доступ ограничен",
    "проверка безопасности",
    "подозрительная активность",
    "подтвердите, что вы не робот",
    "antibot challenge",
    "challenge page",
)

_GENERIC_MARKETPLACE_TITLES = (
    "wildberries",
    "ozon",
    "lamoda",
    "яндекс маркет",
    "яндекс.маркет",
    "market.yandex",
    "интернет-магазин",
    "маркетплейс",
)


def _configured_browser_domains() -> list[str]:
    return [
        domain.strip().lower()
        for domain in settings.parser_browser_domains.split(",")
        if domain.strip()
    ]


def _is_browser_fallback_target(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower().lstrip("www.")
    if not host:
        return False
    for domain in _configured_browser_domains():
        if host == domain or host.endswith(f".{domain}"):
            return True
    return False


def _normalize_url(raw: str) -> str:
    value = re.sub(r"\s+", "", (raw or "").strip())
    if not value:
        return ""

    if value.startswith("https:") and not value.startswith("https://"):
        value = "https://" + value.removeprefix("https:").lstrip("/")
    elif value.startswith("http:") and not value.startswith("http://"):
        value = "http://" + value.removeprefix("http:").lstrip("/")
    elif value.startswith("//"):
        value = "https:" + value
    elif not value.startswith(("http://", "https://")):
        value = "https://" + value

    value = re.sub(r"^(https?://)(https?://)+", r"\1", value)
    return value


def _extract_price(value: str | None) -> float | None:
    if not value:
        return None
    candidate = value.strip()
    if not candidate:
        return None

    compact = (
        candidate.replace("\u00a0", " ")
        .replace("₽", "")
        .replace("$", "")
        .replace("€", "")
    )
    compact = re.sub(r"[^0-9,.\s]", "", compact)

    parts = re.findall(r"\d[\d\s.,]*", compact)
    if not parts:
        return None

    numeric = parts[0].replace(" ", "")
    if numeric.count(",") > 1 and "." not in numeric:
        numeric = numeric.replace(",", "")
    if numeric.count(".") > 1 and "," not in numeric:
        numeric = numeric.replace(".", "")
    if "," in numeric and "." in numeric:
        if numeric.rfind(",") > numeric.rfind("."):
            numeric = numeric.replace(".", "").replace(",", ".")
        else:
            numeric = numeric.replace(",", "")
    else:
        numeric = numeric.replace(",", ".")

    try:
        value = float(numeric)
    except ValueError:
        return None
    return value if value > 0 else None


def _iter_jsonld_payloads(soup: BeautifulSoup):
    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    for script in scripts:
        raw = script.string or script.get_text(strip=True)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        yield data


def _is_product_like_type(value: object) -> bool:
    if isinstance(value, str):
        return "product" in value.lower()
    if isinstance(value, list):
        return any(isinstance(item, str) and "product" in item.lower() for item in value)
    return False


def _clean_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _extract_first_string(value: object) -> str | None:
    if isinstance(value, str):
        return _clean_text(value)
    if isinstance(value, list):
        for item in value:
            cleaned = _extract_first_string(item)
            if cleaned:
                return cleaned
    if isinstance(value, dict):
        for key in ("url", "contentUrl", "name", "text"):
            cleaned = _extract_first_string(value.get(key))
            if cleaned:
                return cleaned
    return None


def _normalize_currency(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r"[^A-Za-z]", "", value).upper()
    if len(cleaned) == 3:
        return cleaned
    return None


def _normalize_availability(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if "/" in cleaned:
        cleaned = cleaned.rstrip("/").split("/")[-1]
    if "#" in cleaned:
        cleaned = cleaned.split("#")[-1]
    cleaned = re.sub(r"[^A-Za-z_]", "", cleaned)
    return cleaned or None


def _extract_brand(value: object) -> str | None:
    if isinstance(value, str):
        return _clean_text(value)
    if isinstance(value, dict):
        return _clean_text(value.get("name")) or _clean_text(value.get("brand"))
    if isinstance(value, list):
        for item in value:
            brand = _extract_brand(item)
            if brand:
                return brand
    return None


def _extract_offer_details(value: object) -> tuple[float | None, str | None, str | None]:
    price: float | None = None
    currency: str | None = None
    availability: str | None = None
    stack = [value]
    visited = set()
    
    while stack:
        current = stack.pop()
        if id(current) in visited:
            continue
        visited.add(id(current))
        
        if isinstance(current, dict):
            # Try to extract price from various keys
            if price is None:
                for key in ("price", "lowPrice", "highPrice", "priceSpecification", "value"):
                    candidate_value = current.get(key)
                    if candidate_value is None:
                        continue
                    # Handle nested price objects
                    if isinstance(candidate_value, dict):
                        nested_price = candidate_value.get("price") or candidate_value.get("value")
                        if nested_price:
                            candidate = _extract_price(_clean_text(str(nested_price)))
                            if candidate is not None:
                                price = candidate
                                break
                    else:
                        candidate = _extract_price(_clean_text(str(candidate_value)))
                        if candidate is not None:
                            price = candidate
                            break
            
            # Try to extract currency
            if currency is None:
                currency = _normalize_currency(
                    current.get("priceCurrency") 
                    or current.get("pricecurrency")
                    or current.get("currency")
                )
            
            # Try to extract availability
            if availability is None:
                availability = _normalize_availability(
                    current.get("availability")
                    or current.get("inStock")
                    or current.get("availabilityStatus")
                )
            
            # Continue traversing
            for val in current.values():
                if isinstance(val, (dict, list)) and id(val) not in visited:
                    stack.append(val)
        elif isinstance(current, list):
            for item in current:
                if isinstance(item, (dict, list)) and id(item) not in visited:
                    stack.append(item)
    
    return price, currency, availability


def _iter_product_nodes(data: object):
    stack = [data]
    visited = set()
    
    while stack:
        current = stack.pop()
        if id(current) in visited:
            continue
        visited.add(id(current))
        
        if isinstance(current, dict):
            has_product_type = _is_product_like_type(current.get("@type"))
            has_product_shape = bool(current.get("name")) and (
                bool(current.get("offers"))
                or bool(current.get("brand"))
                or bool(current.get("image"))
                or bool(current.get("sku"))
                or bool(current.get("mpn"))
                or bool(current.get("gtin"))  # Global Trade Item Number
                or bool(current.get("aggregateRating"))  # Product reviews signal
            )
            # Also check for ProductGroup, ItemList with products
            is_product_group = current.get("@type") == "ProductGroup" or "ProductGroup" in str(current.get("@type", ""))
            is_item_list = current.get("@type") == "ItemList" and bool(current.get("itemListElement"))
            
            if has_product_type or has_product_shape:
                yield current
            elif is_product_group or is_item_list:
                # Extract products from groups/lists
                for item in current.get("itemListElement", []):
                    if isinstance(item, dict) and id(item) not in visited:
                        stack.append(item)
            
            # Continue traversing
            for val in current.values():
                if isinstance(val, (dict, list)) and id(val) not in visited:
                    stack.append(val)
        elif isinstance(current, list):
            for item in current:
                if isinstance(item, (dict, list)) and id(item) not in visited:
                    stack.append(item)


def _extract_product_details_from_jsonld(soup: BeautifulSoup) -> dict[str, object]:
    best: dict[str, object] | None = None
    best_score = -1

    for payload in _iter_jsonld_payloads(soup):
        for product in _iter_product_nodes(payload):
            title = _clean_text(product.get("name"))
            description = _clean_text(product.get("description"))
            brand = _extract_brand(product.get("brand") or product.get("manufacturer"))
            image_url = _extract_first_string(product.get("image") or product.get("thumbnailUrl"))
            price, currency, availability = _extract_offer_details(
                product.get("offers") or product.get("aggregateOffer") or product
            )

            score = 0
            if title:
                score += 4
            if price is not None:
                score += 4
            if image_url:
                score += 2
            if description:
                score += 1
            if brand:
                score += 1
            if currency:
                score += 1
            if availability:
                score += 1
            if _is_product_like_type(product.get("@type")):
                score += 2

            candidate = {
                "title": title,
                "description": description,
                "brand": brand,
                "price": price,
                "currency": currency,
                "availability": availability,
                "image_url": image_url,
            }

            if score > best_score:
                best = candidate
                best_score = score

    return best or {
        "title": None,
        "description": None,
        "brand": None,
        "price": None,
        "currency": None,
        "availability": None,
        "image_url": None,
    }


def _extract_title_from_jsonld(soup: BeautifulSoup) -> str | None:
    details = _extract_product_details_from_jsonld(soup)
    title = details.get("title")
    return title if isinstance(title, str) else None


def _extract_price_from_jsonld(soup: BeautifulSoup) -> float | None:
    details = _extract_product_details_from_jsonld(soup)
    price = details.get("price")
    return price if isinstance(price, (int, float)) else None


def _is_rejected_title(title: str) -> bool:
    text = " ".join(title.strip().lower().split())
    if not text:
        return True
    if any(part in text for part in _REJECT_TITLE_PARTS):
        return True
    if len(text) <= 4:
        return True
    if any(text == value for value in _GENERIC_MARKETPLACE_TITLES):
        return True
    if any(text.startswith(value + " ") for value in _GENERIC_MARKETPLACE_TITLES):
        return True
    return False


def _has_product_signals(soup: BeautifulSoup) -> bool:
    og_type = soup.find("meta", attrs={"property": "og:type"})
    if og_type and og_type.has_attr("content") and "product" in og_type["content"].lower():
        return True
    if soup.find("meta", attrs={"property": "product:price:amount"}):
        return True
    if soup.find("meta", attrs={"itemprop": "price"}):
        return True
    if _extract_title_from_jsonld(soup):
        return True
    return False


def _looks_like_home_or_block_page(final_url: str) -> bool:
    path = (urlparse(final_url).path or "").strip().lower()
    return path in {"", "/"} or "captcha" in path or "challenge" in path


async def _preview_with_playwright(target_url: str) -> OgPreviewResponse | None:
    try:
        from playwright.async_api import async_playwright
    except Exception:
        logger.info("Playwright is not available, skip browser fallback for %s", target_url)
        return None

    browser = None
    context = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                locale="ru-RU",
                timezone_id="Europe/Moscow",
                viewport={"width": 1366, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
                ),
                extra_http_headers={
                    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
                    "sec-ch-ua": '"Google Chrome";v="132", "Chromium";v="132", "Not_A Brand";v="24"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                },
            )
            page = await context.new_page()
            await page.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
                """
            )

            try:
                await page.goto(
                    target_url,
                    wait_until="domcontentloaded",
                    timeout=settings.parser_browser_timeout_ms,
                )
            except Exception:
                # Some protected pages never reach DOMContentLoaded.
                # Retry with a softer wait condition to still capture meta/title.
                await page.goto(
                    target_url,
                    wait_until="commit",
                    timeout=min(settings.parser_browser_timeout_ms, 20_000),
                )
            try:
                await page.wait_for_load_state("networkidle", timeout=12_000)
            except Exception:
                pass
            await page.wait_for_timeout(1_500)
            host = (urlparse(target_url).hostname or "").lower()
            if host.endswith(("ozon.ru", "wildberries.ru", "wb.ru")):
                await page.wait_for_timeout(6_000)

            final_url = page.url or target_url
            page_html = await page.content()
            soup = BeautifulSoup(page_html, "html.parser")
            jsonld_details = _extract_product_details_from_jsonld(soup)

            async def _meta_content(selector: str) -> str | None:
                try:
                    value = await page.eval_on_selector(selector, "el => el.getAttribute('content')")
                except Exception:
                    return None
                if isinstance(value, str):
                    cleaned = value.strip()
                    return cleaned or None
                return None

            title = await _meta_content('meta[property="og:title"]')
            if not title:
                title = await _meta_content('meta[name="twitter:title"]')
            if not title:
                try:
                    page_title = await page.title()
                    title = page_title.strip() if page_title else None
                except Exception:
                    title = None
            if not title:
                raw_title = jsonld_details.get("title")
                title = raw_title if isinstance(raw_title, str) else None
            if title and _is_rejected_title(title):
                title = None

            image_url = await _meta_content('meta[property="og:image"]')
            if not image_url:
                image_url = await _meta_content('meta[name="twitter:image"]')
            if not image_url:
                raw_image = jsonld_details.get("image_url")
                image_url = raw_image if isinstance(raw_image, str) else None
            if image_url:
                image_url = urljoin(final_url, image_url)

            price_text = await _meta_content('meta[property="product:price:amount"]')
            if not price_text:
                price_text = await _meta_content('meta[property="og:price:amount"]')
            if not price_text:
                price_text = await _meta_content('meta[itemprop="price"]')
            if not price_text:
                # Try common price selectors for popular marketplaces
                for selector in (
                    '[data-auto="mainPrice"]',  # Wildberries
                    '[data-auto="price"]',  # Wildberries
                    "[itemprop='price']",
                    ".ui-price__main",  # Ozon
                    ".price",  # Generic
                    ".product-price",  # Generic
                    '[class*="price"]',  # Generic
                    '[data-price]',  # Generic
                    '.price-block__price',  # Lamoda
                    '.product-card-price',  # Generic
                ):
                    try:
                        value = await page.eval_on_selector(selector, "el => el.textContent || el.getAttribute('data-price')")
                    except Exception:
                        value = None
                    if isinstance(value, str) and value.strip():
                        price_text = value.strip()
                        break
            price = _extract_price(price_text)
            if price is None:
                raw_price = jsonld_details.get("price")
                if isinstance(raw_price, (int, float)):
                    price = float(raw_price)

            description = (
                await _meta_content('meta[property="og:description"]')
                or await _meta_content('meta[name="twitter:description"]')
                or _clean_text(jsonld_details.get("description"))
            )
            brand = _clean_text(jsonld_details.get("brand"))
            currency = (
                _normalize_currency(await _meta_content('meta[property="product:price:currency"]'))
                or _normalize_currency(await _meta_content('meta[itemprop="priceCurrency"]'))
                or _normalize_currency(jsonld_details.get("currency"))
            )
            availability = (
                _normalize_availability(await _meta_content('meta[property="product:availability"]'))
                or _normalize_availability(await _meta_content('meta[property="og:availability"]'))
                or _normalize_availability(jsonld_details.get("availability"))
            )

            if not title and price is None and not image_url and not description and not brand:
                return None

            return OgPreviewResponse(
                url=final_url,
                title=title,
                price=price,
                image_url=image_url,
                description=description,
                brand=brand,
                currency=currency,
                availability=availability,
            )
    except Exception as exc:
        logger.warning("Playwright fallback failed for %s: %s", target_url, exc)
        return None
    finally:
        try:
            if context:
                await context.close()
        except Exception:
            pass
        try:
            if browser:
                await browser.close()
        except Exception:
            pass


async def _preview_url_impl(payload: OgPreviewRequest) -> OgPreviewResponse:
    try:
        target_url = _normalize_url(payload.url)
        if not target_url:
            logger.warning("Invalid URL provided: %s", payload.url)
            return OgPreviewResponse(
                url=payload.url,
                title=None,
                price=None,
                image_url=None,
                description=None,
                brand=None,
                currency=None,
                availability=None,
            )
    except Exception as exc:
        logger.warning("Error normalizing URL %s: %s", payload.url, exc)
        return OgPreviewResponse(
            url=payload.url,
            title=None,
            price=None,
            image_url=None,
            description=None,
            brand=None,
            currency=None,
            availability=None,
        )

    prefer_browser = settings.parser_browser_fallback and _is_browser_fallback_target(target_url)
    if prefer_browser:
        browser_response = await _preview_with_playwright(target_url)
        if browser_response and (
            browser_response.title
            or browser_response.price is not None
            or browser_response.image_url
        ):
            return OgPreviewResponse(
                url=browser_response.url or target_url,
                title=browser_response.title,
                price=browser_response.price,
                image_url=browser_response.image_url,
                description=browser_response.description,
                brand=browser_response.brand,
                currency=browser_response.currency,
                availability=browser_response.availability,
            )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Upgrade-Insecure-Requests": "1",
        "sec-ch-ua": '"Google Chrome";v="132", "Chromium";v="132", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }

    resp = None
    fetch_attempts = (
        {"trust_env": True, "verify": True, "name": "env-proxy"},
        {"trust_env": False, "verify": True, "name": "direct"},
        {"trust_env": False, "verify": False, "name": "direct-insecure"},
    )
    attempt_errors: list[str] = []
    for attempt in fetch_attempts:
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=8.0,
                trust_env=attempt["trust_env"],
                verify=attempt["verify"],
            ) as client:
                resp = await client.get(target_url, headers=headers)
            break
        except Exception as exc:
            attempt_errors.append(f"{attempt['name']}: {exc}")

    if resp is None:
        logger.warning(
            "OG parse failed for %s. Attempts: %s",
            target_url,
            " | ".join(attempt_errors),
        )
        return OgPreviewResponse(
            url=target_url,
            title=None,
            price=None,
            image_url=None,
            description=None,
            brand=None,
            currency=None,
            availability=None,
        )

    final_url = str(resp.url)
    if resp.status_code in (401, 403, 429) and settings.parser_browser_fallback:
        browser_response = await _preview_with_playwright(final_url)
        if browser_response:
            return OgPreviewResponse(
                url=browser_response.url or final_url,
                title=browser_response.title,
                price=browser_response.price,
                image_url=browser_response.image_url,
                description=browser_response.description,
                brand=browser_response.brand,
                currency=browser_response.currency,
                availability=browser_response.availability,
            )
    try:
        soup = BeautifulSoup(resp.text, "html.parser")
        jsonld_details = _extract_product_details_from_jsonld(soup)
    except Exception as exc:
        logger.warning("Error parsing HTML for %s: %s", final_url, exc)
        return OgPreviewResponse(
            url=final_url,
            title=None,
            price=None,
            image_url=None,
            description=None,
            brand=None,
            currency=None,
            availability=None,
        )

    title = None
    # Try meta tags first (highest priority)
    title_meta = (
        soup.find("meta", property="og:title")
        or soup.find("meta", attrs={"name": "twitter:title"})
        or soup.find("meta", attrs={"name": "title"})
        or soup.find("meta", attrs={"itemprop": "name"})
    )
    if title_meta and title_meta.has_attr("content"):
        title = title_meta["content"].strip() or None
    
    # Try JSON-LD
    if not title:
        raw_title = jsonld_details.get("title")
        title = raw_title if isinstance(raw_title, str) else None
    
    # Try h1 with product signals
    if not title:
        h1_elem = soup.find("h1")
        if h1_elem and h1_elem.string:
            h1_title = h1_elem.string.strip()
            if h1_title and _has_product_signals(soup):
                title = h1_title
    
    # Try page title as fallback
    if not title and soup.title and soup.title.string:
        fallback_title = soup.title.string.strip()
        if fallback_title and (
            _has_product_signals(soup)
            or not _looks_like_home_or_block_page(final_url)
            or not _is_browser_fallback_target(final_url)
        ):
            title = fallback_title
    
    # Try common title selectors
    if not title:
        title_selectors = [
            '[itemprop="name"]',
            '.product-title',
            '.product-name',
            'h1.product-title',
            '[class*="product-title"]',
            '[class*="product-name"]',
        ]
        for selector in title_selectors:
            try:
                title_elem = soup.select_one(selector)
                if title_elem:
                    title_text = title_elem.get_text(strip=True)
                    if title_text and not _is_rejected_title(title_text):
                        title = title_text
                        break
            except Exception:
                continue
    
    if title and _is_rejected_title(title):
        title = None

    image_url = None
    # Try meta tags first
    image_meta = (
        soup.find("meta", property="og:image")
        or soup.find("meta", attrs={"name": "twitter:image"})
        or soup.find("meta", attrs={"itemprop": "image"})
        or soup.find("meta", attrs={"name": "image"})
    )
    if image_meta and image_meta.has_attr("content"):
        raw_image = image_meta["content"].strip()
        image_url = urljoin(str(resp.url), raw_image) if raw_image else None
    
    # Try JSON-LD
    if not image_url:
        raw_image = jsonld_details.get("image_url")
        if isinstance(raw_image, str):
            image_url = urljoin(final_url, raw_image)
    
    # Try common image selectors in HTML
    if not image_url:
        image_selectors = [
            'img[itemprop="image"]',
            'img.product-image',
            'img[class*="product"]',
            'img[class*="main"]',
            '.product-image img',
            '.main-image img',
            'meta[property="og:image:secure_url"]',
        ]
        for selector in image_selectors:
            try:
                if selector.startswith('meta'):
                    img_elem = soup.select_one(selector)
                    if img_elem and img_elem.has_attr("content"):
                        raw_image = img_elem["content"].strip()
                        if raw_image:
                            image_url = urljoin(final_url, raw_image)
                            break
                else:
                    img_elem = soup.select_one(selector)
                    if img_elem:
                        raw_image = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-lazy-src')
                        if raw_image:
                            image_url = urljoin(final_url, raw_image)
                            break
            except Exception:
                continue

    price = None
    # Try meta tags first
    for selector in (
        ("meta", {"property": "product:price:amount"}),
        ("meta", {"property": "product:price"}),
        ("meta", {"property": "og:price:amount"}),
        ("meta", {"name": "price"}),
        ("meta", {"itemprop": "price"}),
        ("meta", {"property": "product:price:currency", "content": re.compile(r".*")}),  # Sometimes price is in currency tag
    ):
        node = soup.find(selector[0], attrs=selector[1])
        if node and node.has_attr("content"):
            price = _extract_price(node["content"])
            if price is not None:
                break
    
    # Try JSON-LD
    if price is None:
        raw_price = jsonld_details.get("price")
        if isinstance(raw_price, (int, float)):
            price = float(raw_price)
    
    # Try common price selectors in HTML (for sites without meta tags)
    if price is None:
        price_selectors = [
            '[data-price]',
            '[itemprop="price"]',
            '.price',
            '.product-price',
            '[class*="price"]',
            '[id*="price"]',
        ]
        for selector in price_selectors:
            try:
                price_elem = soup.select_one(selector)
                if price_elem:
                    price_text = price_elem.get('data-price') or price_elem.get('content') or price_elem.get_text(strip=True)
                    if price_text:
                        price = _extract_price(price_text)
                        if price is not None:
                            break
            except Exception:
                continue

    if prefer_browser and not title and price is None and not image_url:
        browser_response = await _preview_with_playwright(final_url)
        if browser_response and (
            browser_response.title
            or browser_response.price is not None
            or browser_response.image_url
        ):
            return OgPreviewResponse(
                url=browser_response.url or final_url,
                title=browser_response.title,
                price=browser_response.price,
                image_url=browser_response.image_url,
                description=browser_response.description,
                brand=browser_response.brand,
                currency=browser_response.currency,
                availability=browser_response.availability,
            )

    description = _clean_text(jsonld_details.get("description"))
    if not description:
        description_meta = (
            soup.find("meta", property="og:description")
            or soup.find("meta", attrs={"name": "twitter:description"})
            or soup.find("meta", attrs={"name": "description"})
        )
        if description_meta and description_meta.has_attr("content"):
            description = _clean_text(description_meta["content"])

    brand = _clean_text(jsonld_details.get("brand"))

    currency = _normalize_currency(jsonld_details.get("currency"))
    if not currency:
        currency_meta = (
            soup.find("meta", attrs={"property": "product:price:currency"})
            or soup.find("meta", attrs={"itemprop": "priceCurrency"})
        )
        if currency_meta and currency_meta.has_attr("content"):
            currency = _normalize_currency(currency_meta["content"])

    availability = _normalize_availability(jsonld_details.get("availability"))
    if not availability:
        availability_meta = (
            soup.find("meta", attrs={"property": "product:availability"})
            or soup.find("meta", attrs={"property": "og:availability"})
        )
        if availability_meta and availability_meta.has_attr("content"):
            availability = _normalize_availability(availability_meta["content"])

    response = OgPreviewResponse(
        url=final_url,
        title=title,
        price=price,
        image_url=image_url,
        description=description,
        brand=brand,
        currency=currency,
        availability=availability,
    )

    needs_browser_fallback = (
        settings.parser_browser_fallback
        and _is_browser_fallback_target(final_url)
        and (response.title is None or (response.price is None and response.image_url is None))
    )
    if needs_browser_fallback:
        browser_response = await _preview_with_playwright(final_url)
        if browser_response:
            return OgPreviewResponse(
                url=browser_response.url or response.url,
                title=browser_response.title or response.title,
                price=browser_response.price if browser_response.price is not None else response.price,
                image_url=browser_response.image_url or response.image_url,
                description=browser_response.description or response.description,
                brand=browser_response.brand or response.brand,
                currency=browser_response.currency or response.currency,
                availability=browser_response.availability or response.availability,
            )

    return response


@router.post("/og/preview", response_model=OgPreviewResponse)
async def preview_url(payload: OgPreviewRequest) -> OgPreviewResponse:
    try:
        logger.info("OG preview request for URL: %s", payload.url)
        result = await _preview_url_impl(payload)
        logger.info("OG preview result for %s: title=%s, price=%s", payload.url, result.title, result.price)
        return result
    except Exception as exc:
        logger.exception("Error in preview_url for %s: %s", payload.url, exc)
        return OgPreviewResponse(
            url=payload.url,
            title=None,
            price=None,
            image_url=None,
            description=None,
            brand=None,
            currency=None,
            availability=None,
        )


@router.post("/parse-url", response_model=OgPreviewResponse)
async def parse_url(payload: OgPreviewRequest) -> OgPreviewResponse:
    """
    Универсальный эндпоинт для парсинга URL товаров.
    Сначала пытается использовать встроенный OG-парсер, затем fallback на enhanced_parser.
    """
    try:
        logger.info("Parse URL request for: %s", payload.url)

        try:
            target_url = _normalize_url(payload.url)
            if not target_url:
                return OgPreviewResponse(
                    url=payload.url,
                    title=None,
                    price=None,
                    image_url=None,
                    description=None,
                    brand=None,
                    currency=None,
                    availability=None,
                )
        except Exception as exc:
            logger.warning("Error normalizing URL %s: %s", payload.url, exc)
            return OgPreviewResponse(
                url=payload.url,
                title=None,
                price=None,
                image_url=None,
                description=None,
                brand=None,
                currency=None,
                availability=None,
            )

        result = await _preview_url_impl(OgPreviewRequest(url=target_url))
        
        if result.title or result.price is not None or result.image_url:
            logger.info("OG parser success for %s: title=%s, price=%s", payload.url, result.title, result.price)
            return result
        
        logger.info("OG parser returned empty, trying enhanced parser for %s", payload.url)
        
        try:
            product_info = await parse_product_from_url(
                url=target_url,
                timeout=settings.parser_browser_timeout_ms / 1000 if hasattr(settings, 'parser_browser_timeout_ms') else 30,
                use_playwright=settings.parser_browser_fallback if hasattr(settings, 'parser_browser_fallback') else True
            )
            
            if product_info.title or product_info.price is not None or product_info.image_url:
                enhanced_result = OgPreviewResponse(
                    url=target_url,
                    title=product_info.title,
                    price=product_info.price,
                    image_url=product_info.image_url,
                    description=product_info.description,
                    brand=product_info.brand,
                    currency=product_info.currency,
                    availability=product_info.availability,
                )
                logger.info("Enhanced parser success for %s: title=%s, price=%s", payload.url, enhanced_result.title, enhanced_result.price)
                return enhanced_result
        except ImportError as e:
            logger.warning("Enhanced parser not available (missing dependency): %s", e)
        except Exception as e:
            logger.warning("Enhanced parser failed for %s: %s", payload.url, e)
        
        logger.info("Parse URL final result for %s: title=%s, price=%s", payload.url, result.title, result.price)
        return result
        
    except Exception as exc:
        logger.exception("Error in parse_url for %s: %s", payload.url, exc)
        return OgPreviewResponse(
            url=payload.url,
            title=None,
            price=None,
            image_url=None,
            description=None,
            brand=None,
            currency=None,
            availability=None,
        )
