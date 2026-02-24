"""
Enhanced Product Parser for WishShare
Поддержка парсинга маркетплейсов с использованием различных техник:
- Open Graph и мета-теги
- JSON-LD структурированные данные  
- Playwright для динамических сайтов
- Специфичные селекторы для маркетплейсов
- Redis-кэширование результатов
"""

import sys
# Fix for Python 3.13+ on Windows - must be before any asyncio/playwright usage
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import json
import logging
import re
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, asdict

from bs4 import BeautifulSoup
import httpx
from playwright.async_api import async_playwright

from app.core.parse_cache import parse_cache

logger = logging.getLogger("wishshare.enhanced_parser")

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

@dataclass
class ProductInfo:
    """Структура данных о товаре"""
    title: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    brand: Optional[str] = None
    availability: Optional[str] = None
    category: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    seller: Optional[str] = None
    delivery_info: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert ProductInfo to dictionary for caching."""
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProductInfo":
        """Create ProductInfo from cached dictionary."""
        # Remove internal cache fields
        data = {k: v for k, v in data.items() if not k.startswith("_")}
        return cls(**{k: v for k, v in data.items() if k in [
            "title", "price", "currency", "image_url", "description",
            "brand", "availability", "category", "rating", "reviews_count",
            "seller", "delivery_info"
        ]})

class MarketplaceConfig:
    """Конфигурация для конкретного маркетплейса"""
    
    def __init__(self, name: str, domains: List[str], selectors: Dict[str, List[str]]):
        self.name = name
        self.domains = domains
        self.selectors = selectors

# Конфигурации для популярных маркетплейсов
MARKETPLACE_CONFIGS = {
    "wildberries": MarketplaceConfig(
        name="Wildberries",
        domains=["wildberries.ru", "wb.ru"],
        selectors={
            "title": [
                '[data-auto="product-title"]',
                '.product-title',
                'h1[itemprop="name"]',
                '.brand-and-product__title'
            ],
            "price": [
                '[data-auto="mainPrice"]',
                '[data-auto="price"]',
                '.price-block__price',
                '.final-price'
            ],
            "image": [
                '[data-auto="mainPhoto"] img',
                '.product-gallery__img',
                '.swiper-slide img'
            ],
            "description": [
                '.product-description',
                '[data-auto="description"]',
                '.collapsable-text'
            ],
            "brand": [
                '.brand-and-product__brand',
                '[data-auto="brand"]',
                '.brand-name'
            ],
            "availability": [
                '[data-auto="available"]',
                '.product-availability',
                '.stock-info'
            ]
        }
    ),
    
    "ozon": MarketplaceConfig(
        name="Ozon", 
        domains=["ozon.ru"],
        selectors={
            "title": [
                '.tsTitle450',
                'h1.tsHeadline550',
                '.product-title'
            ],
            "price": [
                '.ui-price__main',
                '.price-block__price',
                '.ui-a2'
            ],
            "image": [
                '.image-gallery__img',
                '.js-gallery-image',
                '.product-image'
            ],
            "description": [
                '.product-description-text',
                '.collapse-content',
                '.description-text'
            ],
            "brand": [
                '.brand-name',
                '.product-brand',
                '.tsCaption500'
            ],
            "availability": [
                '.availability-info',
                '.stock-status',
                '.product-available'
            ]
        }
    ),
    
    "lamoda": MarketplaceConfig(
        name="Lamoda",
        domains=["lamoda.ru"],
        selectors={
            "title": [
                '.product-title__brand-name',
                'h1.product-title__model-name',
                '.product-title'
            ],
            "price": [
                '.product-prices__price',
                '.price-block__price',
                '.product-price'
            ],
            "image": [
                '.product-gallery__img',
                '.product-image__img',
                '.gallery__img'
            ],
            "description": [
                '.product-description',
                '.product-details',
                '.description-text'
            ],
            "brand": [
                '.product-title__brand-name',
                '.brand-name'
            ],
            "availability": [
                '.product-availability',
                '.stock-info',
                '.availability-status'
            ]
        }
    ),

    "dns_shop": MarketplaceConfig(
        name="DNS",
        domains=["dns-shop.ru"],
        selectors={
            "title": [
                "h1.product-card-top__title",
                "h1[data-qa='product-name']",
                "h1",
                ".product-card-top__title"
            ],
            "price": [
                ".product-buy__price",
                ".product-buy__price-number",
                "[data-qa='product-price']",
                ".product-card-top__price"
            ],
            "image": [
                ".product-images__main-img img",
                ".product-images__main-image img",
                ".product-card-top__img img",
                ".product-images__preview img"
            ],
            "description": [
                ".product-card-description__text",
                "[data-qa='product-description']",
                ".product-card-description",
                ".product-card-top__description"
            ],
            "brand": [
                ".product-card-top__brand",
                "[data-qa='product-brand']",
                ".product-card__brand"
            ],
            "availability": [
                ".available-amount",
                "[data-qa='product-availability']",
                ".product-buy__availability"
            ]
        }
    ),
    
    "yandex_market": MarketplaceConfig(
        name="Yandex Market",
        domains=["market.yandex.ru", "yandex.ru"],
        selectors={
            "title": [
                'h1._2B2oh',
                '.offer-title',
                '.product-title'
            ],
            "price": [
                '._3f2ZU',
                '.price',
                '.offer-price'
            ],
            "image": [
                '.n-gallery__img',
                '.product-image',
                '.gallery-image'
            ],
            "description": [
                '.offer-description',
                '.product-description',
                '.description-text'
            ],
            "brand": [
                '.offer-brand',
                '.brand-name'
            ],
            "availability": [
                '.offer-availability',
                '.stock-info'
            ]
        }
    ),
    
    "amazon": MarketplaceConfig(
        name="Amazon",
        domains=["amazon.com", "amazon.ru"],
        selectors={
            "title": [
                '#productTitle',
                '.product-title',
                'h1#title'
            ],
            "price": [
                '.a-price-whole',
                '.a-price .a-offscreen',
                '.priceBlockBuyingPriceString'
            ],
            "image": [
                '#landingImage',
                '.a-dynamic-image',
                '.product-image'
            ],
            "description": [
                '#feature-bullets ul',
                '.product-description',
                '.a-section.a-spacing-small'
            ],
            "brand": [
                '#bylineInfo',
                '.po-brand',
                '.brand-name'
            ],
            "availability": [
                '#availability',
                '.a-color-success',
                '.availability'
            ]
        }
    ),
    
    "aliexpress": MarketplaceConfig(
        name="AliExpress",
        domains=["aliexpress.com", "aliexpress.ru"],
        selectors={
            "title": [
                '.product-title-text',
                'h1.product-title',
                '.title-text'
            ],
            "price": [
                '.product-price-current',
                '.uniform-banner-box-price',
                '.price-current'
            ],
            "image": [
                '.image-viewer img',
                '.product-gallery img',
                '.ui-image-viewer-thumb-frame img'
            ],
            "description": [
                '.product-description',
                '.description-content',
                '.ui-box-body'
            ],
            "brand": [
                '.product-brand',
                '.brand-name'
            ],
            "availability": [
                '.product-delivery',
                '.availability-info',
                '.stock-info'
            ]
        }
    )
}

class EnhancedProductParser:
    """Улучшенный парсер товаров с поддержкой маркетплейсов"""
    
    def __init__(self, timeout: int = 30, use_playwright: bool = True):
        self.timeout = timeout
        self.use_playwright = use_playwright
        self.session = None
        
    async def __aenter__(self):
        self.session = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Upgrade-Insecure-Requests": "1",
                "sec-ch-ua": '"Google Chrome";v="132", "Chromium";v="132", "Not_A Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()
    
    def _get_marketplace_config(self, url: str) -> Optional[MarketplaceConfig]:
        """Определение конфигурации маркетплейса по URL"""
        hostname = urlparse(url).hostname or ""
        hostname = hostname.lower().replace("www.", "")
        
        for config in MARKETPLACE_CONFIGS.values():
            for domain in config.domains:
                if hostname == domain or hostname.endswith(f".{domain}"):
                    return config
        return None
    
    def _extract_price(self, text: Optional[str]) -> Optional[float]:
        """Извлечение цены из текста"""
        if not text:
            return None
            
        # Удаляем символы валют и пробелы
        cleaned = (
            text.replace("\u00a0", " ")  # неразрывный пробел
            .replace("₽", "").replace("$", "").replace("€", "")
            .replace("RUB", "").replace("USD", "").replace("EUR", "")
        )
        
        # Удаляем все символы кроме цифр, точек и запятых
        cleaned = re.sub(r"[^0-9,.\s]", "", cleaned)
        
        # Находим числа в тексте
        numbers = re.findall(r"\d[\d\s.,]*", cleaned)
        if not numbers:
            return None
            
        # Берем первое число (обычно это цена)
        price_str = numbers[0].replace(" ", "")
        
        # Обработка десятичных разделителей
        if price_str.count(",") > 1 and "." not in price_str:
            price_str = price_str.replace(",", "")
        elif price_str.count(".") > 1 and "," not in price_str:
            price_str = price_str.replace(".", "")
        elif "," in price_str and "." in price_str:
            if price_str.rfind(",") > price_str.rfind("."):
                price_str = price_str.replace(".", "").replace(",", ".")
            else:
                price_str = price_str.replace(",", "")
        else:
            price_str = price_str.replace(",", ".")
        
        try:
            return float(price_str)
        except ValueError:
            return None
    
    def _extract_text_content(self, element) -> Optional[str]:
        """Извлечение текста из элемента"""
        if not element:
            return None
            
        # Пробуем разные атрибуты
        for attr in ['content', 'data-price', 'data-value']:
            if element.has_attr(attr):
                text = element[attr].strip()
                if text:
                    return text
        
        # Пробуем текст элемента
        text = element.get_text(strip=True)
        return text if text else None
    
    def _extract_image_url(self, element, base_url: str) -> Optional[str]:
        """Извлечение URL изображения из элемента"""
        if not element:
            return None
            
        # Пробуем разные атрибуты
        for attr in ['src', 'data-src', 'data-lazy-src', 'content']:
            if element.has_attr(attr):
                img_url = element[attr].strip()
                if img_url:
                    return urljoin(base_url, img_url)
        
        return None
    
    def _extract_jsonld_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Извлечение данных из JSON-LD скриптов"""
        data = {}
        
        scripts = soup.find_all("script", {"type": "application/ld+json"})
        for script in scripts:
            try:
                json_data = json.loads(script.string or "")
                self._extract_from_jsonld_recursive(json_data, data)
            except (json.JSONDecodeError, AttributeError):
                continue
                
        return data
    
    def _extract_from_jsonld_recursive(self, obj: Any, result: Dict[str, Any]):
        """Рекурсивное извлечение данных из JSON-LD"""
        if isinstance(obj, dict):
            # Проверяем, является ли это продуктом
            if self._is_product_object(obj):
                self._extract_product_data(obj, result)
            
            # Рекурсивный обход
            for value in obj.values():
                self._extract_from_jsonld_recursive(value, result)
                
        elif isinstance(obj, list):
            for item in obj:
                self._extract_from_jsonld_recursive(item, result)
    
    def _is_product_object(self, obj: Dict[str, Any]) -> bool:
        """Проверка, является ли объект продуктом"""
        obj_type = obj.get("@type", "")
        if isinstance(obj_type, str):
            return "product" in obj_type.lower()
        elif isinstance(obj_type, list):
            return any("product" in str(t).lower() for t in obj_type)
        return False
    
    def _extract_product_data(self, obj: Dict[str, Any], result: Dict[str, Any]):
        """Извлечение данных о продукте из объекта"""
        if "name" in obj and not result.get("title"):
            result["title"] = obj["name"]
        
        if "description" in obj and not result.get("description"):
            result["description"] = obj["description"]
        
        if "brand" in obj and not result.get("brand"):
            brand = obj["brand"]
            if isinstance(brand, dict):
                result["brand"] = brand.get("name")
            else:
                result["brand"] = brand
        
        # Извлечение цены и валюты
        offers = obj.get("offers") or obj.get("aggregateOffer")
        if offers and not result.get("price"):
            if isinstance(offers, dict):
                if "price" in offers:
                    result["price"] = float(offers["price"])
                if "priceCurrency" in offers:
                    result["currency"] = offers["priceCurrency"]
        
        # Извлечение изображения
        if "image" in obj and not result.get("image_url"):
            image = obj["image"]
            if isinstance(image, str):
                result["image_url"] = image
            elif isinstance(image, list) and image:
                result["image_url"] = image[0]
            elif isinstance(image, dict) and "url" in image:
                result["image_url"] = image["url"]
    
    async def _parse_with_selectors(self, soup: BeautifulSoup, config: MarketplaceConfig, base_url: str) -> ProductInfo:
        """Парсинг с использованием специфичных селекторов маркетплейса"""
        product = ProductInfo()
        
        # Извлечение данных с селекторов
        for field, selectors in config.selectors.items():
            for selector in selectors:
                try:
                    element = soup.select_one(selector)
                    if element:
                        if field == "title":
                            text = self._extract_text_content(element)
                            if text:
                                product.title = text
                                break
                        elif field == "price":
                            text = self._extract_text_content(element)
                            if text:
                                price = self._extract_price(text)
                                if price is not None:
                                    product.price = price
                                    break
                        elif field == "image":
                            img_url = self._extract_image_url(element, base_url)
                            if img_url:
                                product.image_url = img_url
                                break
                        elif field == "description":
                            text = self._extract_text_content(element)
                            if text:
                                product.description = text
                                break
                        elif field == "brand":
                            text = self._extract_text_content(element)
                            if text:
                                product.brand = text
                                break
                        elif field == "availability":
                            text = self._extract_text_content(element)
                            if text:
                                product.availability = text.lower()
                                break
                except Exception as e:
                    logger.debug(f"Error parsing {field} with selector {selector}: {e}")
                    continue
        
        return product
    
    async def _parse_with_playwright(self, url: str, config: Optional[MarketplaceConfig] = None) -> Optional[ProductInfo]:
        """Парсинг с использованием Playwright для динамических сайтов"""
        if not self.use_playwright:
            return None
            
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
                )
                
                page = await context.new_page()
                
                # Добавляем скрипт для маскировки автоматизации
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
                """)
                
                await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout * 1000)
                await page.wait_for_load_state("networkidle", timeout=10000)
                await page.wait_for_timeout(2000)  # Дополнительное ожидание для JS
                
                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")
                
                # Сначала пробуем JSON-LD
                jsonld_data = self._extract_jsonld_data(soup)
                product = ProductInfo()
                
                if jsonld_data:
                    product.title = jsonld_data.get("title")
                    product.price = jsonld_data.get("price")
                    product.currency = jsonld_data.get("currency")
                    product.image_url = jsonld_data.get("image_url")
                    product.description = jsonld_data.get("description")
                    product.brand = jsonld_data.get("brand")
                
                # Если есть конфигурация маркетплейса, используем специфичные селекторы
                if config:
                    marketplace_product = await self._parse_with_selectors(soup, config, url)
                    # Комбинируем данные (селекторы имеют приоритет)
                    product.title = marketplace_product.title or product.title
                    product.price = marketplace_product.price or product.price
                    product.image_url = marketplace_product.image_url or product.image_url
                    product.description = marketplace_product.description or product.description
                    product.brand = marketplace_product.brand or product.brand
                    product.availability = marketplace_product.availability or product.availability
                else:
                    # Универсальные селекторы
                    await self._parse_with_universal_selectors(page, product, url)
                
                await browser.close()
                return product
                
        except Exception as e:
            logger.warning(f"Playwright parsing failed for {url}: {e}")
            return None
    
    async def _parse_with_universal_selectors(self, page, product: ProductInfo, base_url: str):
        """Парсинг с универсальными селекторами"""
        try:
            # Универсальные селекторы для разных полей
            selectors = {
                "title": [
                    'meta[property="og:title"]',
                    'meta[name="twitter:title"]',
                    'h1',
                    '[itemprop="name"]',
                    '.product-title',
                    '.title'
                ],
                "price": [
                    'meta[property="product:price:amount"]',
                    'meta[property="og:price:amount"]',
                    '[itemprop="price"]',
                    '.price',
                    '.product-price',
                    '[class*="price"]'
                ],
                "image": [
                    'meta[property="og:image"]',
                    'meta[name="twitter:image"]',
                    '[itemprop="image"]',
                    '.product-image img',
                    '.main-image img'
                ],
                "description": [
                    'meta[property="og:description"]',
                    'meta[name="twitter:description"]',
                    '[itemprop="description"]',
                    '.description',
                    '.product-description'
                ]
            }
            
            for field, field_selectors in selectors.items():
                for selector in field_selectors:
                    try:
                        if selector.startswith('meta'):
                            element = await page.query_selector(selector)
                            if element:
                                content = await element.get_attribute('content')
                                if content:
                                    content = content.strip()
                                    if field == "price":
                                        price = self._extract_price(content)
                                        if price is not None:
                                            product.price = price
                                    elif field == "image":
                                        product.image_url = urljoin(base_url, content)
                                    else:
                                        setattr(product, field, content)
                                    break
                        else:
                            element = await page.query_selector(selector)
                            if element:
                                if field == "price":
                                    text = await element.inner_text()
                                    price = self._extract_price(text)
                                    if price is not None:
                                        product.price = price
                                        break
                                elif field == "image":
                                    src = await element.get_attribute('src')
                                    if src:
                                        product.image_url = urljoin(base_url, src)
                                        break
                                else:
                                    text = await element.inner_text()
                                    if text:
                                        setattr(product, field, text.strip())
                                        break
                    except Exception:
                        continue
                        
        except Exception as e:
            logger.debug(f"Universal selectors parsing failed: {e}")
    
    async def parse_product(self, url: str, use_cache: bool = True) -> ProductInfo:
        """Основной метод парсинга товара.
        
        Args:
            url: URL товара для парсинга
            use_cache: Использовать кэш Redis (по умолчанию True)
        
        Returns:
            ProductInfo с данными о товаре
        """
        try:
            url = _normalize_url(url)
            if not url:
                return ProductInfo()

            # Проверяем кэш
            if use_cache:
                cached = await parse_cache.get(url)
                if cached:
                    logger.info("Cache hit for URL: %s", url[:50])
                    return ProductInfo.from_dict(cached)
                else:
                    logger.debug("Cache miss for URL: %s", url[:50])

            # Определяем маркетплейс
            config = self._get_marketplace_config(url)
            
            try:
                response = await self.session.get(url)
                if response.status_code in (401, 403) and self.use_playwright:
                    playwright_product = await self._parse_with_playwright(url, config)
                    if playwright_product:
                        # Сохраняем в кэш
                        if use_cache:
                            await parse_cache.set(url, playwright_product.to_dict())
                        return playwright_product
                response.raise_for_status()
            except Exception as exc:
                if self.use_playwright:
                    playwright_product = await self._parse_with_playwright(url, config)
                    if playwright_product:
                        # Сохраняем в кэш
                        if use_cache:
                            await parse_cache.set(url, playwright_product.to_dict())
                        return playwright_product
                raise exc

            soup = BeautifulSoup(response.text, "html.parser")
            
            # Извлекаем JSON-LD данные
            jsonld_data = self._extract_jsonld_data(soup)
            product = ProductInfo()
            
            if jsonld_data:
                product.title = jsonld_data.get("title")
                product.price = jsonld_data.get("price")
                product.currency = jsonld_data.get("currency")
                product.image_url = jsonld_data.get("image_url")
                product.description = jsonld_data.get("description")
                product.brand = jsonld_data.get("brand")
            
            # Если есть конфигурация маркетплейса, используем её
            if config:
                marketplace_product = await self._parse_with_selectors(soup, config, url)
                # Комбинируем данные (селекторы имеют приоритет над JSON-LD)
                product.title = marketplace_product.title or product.title
                product.price = marketplace_product.price or product.price
                product.image_url = marketplace_product.image_url or product.image_url
                product.description = marketplace_product.description or product.description
                product.brand = marketplace_product.brand or product.brand
                product.availability = marketplace_product.availability or product.availability
            else:
                # Универсальный парсинг мета-тегов
                await self._parse_meta_tags(soup, product, url)
            
            # Если данных недостаточно и включен Playwright, пробуем его
            if (not product.title or (not product.price and not product.image_url)) and self.use_playwright:
                logger.info("Insufficient data from HTTP request, trying Playwright for %s", url[:50])
                playwright_product = await self._parse_with_playwright(url, config)
                if playwright_product:
                    # Playwright имеет приоритет
                    product.title = playwright_product.title or product.title
                    product.price = playwright_product.price or product.price
                    product.image_url = playwright_product.image_url or product.image_url
                    product.description = playwright_product.description or product.description
                    product.brand = playwright_product.brand or product.brand
                    product.availability = playwright_product.availability or product.availability
            
            # Сохраняем в кэш если есть полезные данные
            if use_cache and (product.title or product.price or product.image_url):
                await parse_cache.set(url, product.to_dict())
            
            return product
            
        except Exception as e:
            logger.error("Error parsing product from %s: %s", url[:50], e)
            return ProductInfo()
    
    async def _parse_meta_tags(self, soup: BeautifulSoup, product: ProductInfo, base_url: str):
        """Парсинг универсальных мета-тегов"""
        # Open Graph теги
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            product.title = og_title["content"].strip()
        
        og_price = soup.find("meta", property="og:price:amount")
        if og_price and og_price.get("content"):
            price = self._extract_price(og_price["content"])
            if price is not None:
                product.price = price
        
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            product.image_url = urljoin(base_url, og_image["content"].strip())
        
        og_description = soup.find("meta", property="og:description")
        if og_description and og_description.get("content"):
            product.description = og_description["content"].strip()
        
        # Twitter Card теги
        twitter_title = soup.find("meta", attrs={"name": "twitter:title"})
        if twitter_title and twitter_title.get("content") and not product.title:
            product.title = twitter_title["content"].strip()
        
        twitter_image = soup.find("meta", attrs={"name": "twitter:image"})
        if twitter_image and twitter_image.get("content") and not product.image_url:
            product.image_url = urljoin(base_url, twitter_image["content"].strip())
        
        # Микроформаты
        title_elem = soup.find("h1")
        if title_elem and title_elem.get_text(strip=True) and not product.title:
            product.title = title_elem.get_text(strip=True)
        
        price_elem = soup.find("meta", attrs={"itemprop": "price"})
        if price_elem and price_elem.get("content") and not product.price:
            price = self._extract_price(price_elem["content"])
            if price is not None:
                product.price = price
        
        image_elem = soup.find("meta", attrs={"itemprop": "image"})
        if image_elem and image_elem.get("content") and not product.image_url:
            product.image_url = urljoin(base_url, image_elem["content"].strip())
        
        description_elem = soup.find("meta", attrs={"name": "description"})
        if description_elem and description_elem.get("content") and not product.description:
            product.description = description_elem["content"].strip()

# Удобная функция для использования
async def parse_product_from_url(
    url: str, 
    timeout: int = 30, 
    use_playwright: bool = True,
    use_cache: bool = True
) -> ProductInfo:
    """Парсинг товара по URL с использованием улучшенного парсера.
    
    Args:
        url: URL страницы товара
        timeout: Таймаут запроса в секундах
        use_playwright: Использовать Playwright для динамических сайтов
        use_cache: Использовать Redis кэш (по умолчанию True)
    
    Returns:
        ProductInfo с данными о товаре
        
    Raises ValueError if the URL domain is not in the configured allowlist,
    preventing SSRF attacks against internal services.
    """
    from app.core.config import settings
    normalized = _normalize_url(url)
    parsed = urlparse(normalized)
    hostname = (parsed.hostname or "").lower()

    # Strip 'www.' prefix for matching
    bare_hostname = hostname.removeprefix("www.")

    allowed = settings.allowed_parser_domains
    if not any(bare_hostname == d or bare_hostname.endswith("." + d) for d in allowed):
        raise ValueError(
            f"Domain '{hostname}' is not in the allowed parser domains list. "
            "Add it to PARSER_BROWSER_DOMAINS in your environment configuration."
        )

    async with EnhancedProductParser(timeout=timeout, use_playwright=use_playwright) as parser:
        return await parser.parse_product(normalized, use_cache=use_cache)
