from bs4 import BeautifulSoup

from app.api.routes.og import _extract_product_details_from_jsonld


def test_extract_product_details_from_jsonld() -> None:
    html = """
    <html>
      <head>
        <script type="application/ld+json">
        {
          "@context":"https://schema.org",
          "@type":"Product",
          "name":"Apple iPhone 16 Pro 256GB",
          "description":"Смартфон с OLED экраном",
          "brand":{"@type":"Brand","name":"Apple"},
          "image":["https://cdn.example.com/iphone.jpg"],
          "offers":{
            "@type":"Offer",
            "price":"129990",
            "priceCurrency":"RUB",
            "availability":"https://schema.org/InStock"
          }
        }
        </script>
      </head>
      <body></body>
    </html>
    """

    soup = BeautifulSoup(html, "html.parser")
    details = _extract_product_details_from_jsonld(soup)

    assert details["title"] == "Apple iPhone 16 Pro 256GB"
    assert details["description"] == "Смартфон с OLED экраном"
    assert details["brand"] == "Apple"
    assert details["price"] == 129990.0
    assert details["currency"] == "RUB"
    assert details["availability"] == "InStock"
    assert details["image_url"] == "https://cdn.example.com/iphone.jpg"


if __name__ == "__main__":
    test_extract_product_details_from_jsonld()
    print("ok")
