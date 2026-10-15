"""Search fields that stay tied to the text already on the page."""

from __future__ import annotations

from urllib.parse import urlparse

from flask import request


def clip(text: str, limit: int = 155) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= limit:
        return clean
    cut = clean[:limit].rsplit(" ", 1)[0].rstrip(".,;:")
    return (cut or clean[:limit]) + "…"


def clean_site_url(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or any(char.isspace() for char in raw):
        raise ValueError("Die öffentliche Adresse muss wie https://example.de aussehen.")
    return f"{parsed.scheme}://{parsed.netloc}"


def site_base(settings: dict) -> str:
    try:
        saved = clean_site_url(settings.get("site_url") or "")
    except ValueError:
        saved = ""
    if saved:
        return saved
    return request.url_root.rstrip("/")


def absolute(base: str, path: str) -> str:
    if not path:
        return base + "/"
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if not path.startswith("/"):
        path = "/" + path
    return base + path


def organization(settings: dict, base: str) -> dict:
    node = {
        "@type": "Organization",
        "@id": base + "/#organization",
        "name": settings.get("company_name") or "Saunacore",
        "url": base + "/",
        "email": settings.get("email") or "",
        "telephone": settings.get("phone") or "",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": settings.get("street") or "",
            "postalCode": settings.get("postal_code") or "",
            "addressLocality": settings.get("city") or "",
            "addressCountry": "DE",
        },
    }
    vat_id = (settings.get("vat_id") or "").strip()
    if vat_id:
        node["vatID"] = vat_id
    return node


def website(settings: dict, base: str) -> dict:
    return {
        "@type": "WebSite",
        "@id": base + "/#website",
        "url": base + "/",
        "name": settings.get("company_name") or "Saunacore",
        "inLanguage": "de",
        "publisher": {"@id": base + "/#organization"},
    }


def webpage(title: str, description: str, url: str, base: str, kind: str = "WebPage") -> dict:
    return {
        "@type": kind,
        "name": title,
        "description": description,
        "url": url,
        "inLanguage": "de",
        "isPartOf": {"@id": base + "/#website"},
    }


def breadcrumb_list(crumbs: list[dict], base: str, current: str) -> dict:
    elements = []
    for index, crumb in enumerate(crumbs, start=1):
        target = crumb.get("url") or current
        elements.append(
            {
                "@type": "ListItem",
                "position": index,
                "name": crumb["name"],
                "item": absolute(base, target),
            }
        )
    return {"@type": "BreadcrumbList", "itemListElement": elements}


def item_list(models: list[dict], base: str) -> dict:
    return {
        "@type": "ItemList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": index,
                "name": model["name"],
                "url": f"{base}/flotte/{model['slug']}",
            }
            for index, model in enumerate(models, start=1)
        ],
    }


def service_node(model: dict, base: str) -> dict:
    cents = int(model["price_cents"])
    price = f"{cents // 100}.{cents % 100:02d}"
    url = f"{base}/flotte/{model['slug']}"
    return {
        "@type": "Service",
        "@id": url + "#service",
        "name": model["name"],
        "serviceType": "Mobile Sauna mieten",
        "description": clip(model.get("summary") or model.get("subtitle") or model["name"], 300),
        "image": [absolute(base, image) for image in model.get("images") or []],
        "url": url,
        "provider": {"@id": base + "/#organization"},
        "areaServed": {"@type": "Country", "name": "Deutschland"},
        "offers": {
            "@type": "Offer",
            "price": price,
            "priceCurrency": "EUR",
            "url": url,
            "priceSpecification": {
                "@type": "UnitPriceSpecification",
                "price": price,
                "priceCurrency": "EUR",
                "unitText": "Tag",
                "valueAddedTaxIncluded": True,
            },
        },
    }


def faq_page(items: list[dict]) -> dict:
    return {
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": item["q"],
                "acceptedAnswer": {"@type": "Answer", "text": item["a"]},
            }
            for item in items
            if item.get("q") and item.get("a")
        ],
    }


def graph(settings: dict, base: str, nodes: list[dict]) -> dict:
    return {
        "@context": "https://schema.org",
        "@graph": [organization(settings, base), website(settings, base), *[node for node in nodes if node]],
    }
