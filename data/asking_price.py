# -*- coding: utf-8 -*-
"""The asking price of a work a gallery has for sale, from a WooCommerce Store API product.

Current stock only: a work that is sold, out of stock or reserved gets no price, and
merge.py drops any price from a past listing. What a work sold for stays between the
gallery and the buyer; what the gallery asks for it is on its own shop page.
Whole euros; nothing for a price in another currency, a price range or a zero.
"""

def asking(p, sold=False):
    pr = p.get("prices") or {}
    if sold or not p.get("is_in_stock", True) or pr.get("currency_code") != "EUR" or pr.get("price_range"): return {}
    try: n = int(pr.get("price") or 0) / 10 ** int(pr.get("currency_minor_unit") or 0)
    except (TypeError, ValueError): return {}
    return {"price": round(n)} if n >= 1 else {}


import re
_EUR = re.compile(r"(?:€|eur\b)\s*(\d{1,3}(?:[\s., ]\d{3})+|\d+)(?:[.,]\d{2})?|(\d{1,3}(?:[\s., ]\d{3})+|\d+)(?:[.,]\d{2})?\s*(?:€|eur\b|euro)", re.I)
def euros(text):
    """'Hind 1 200 €', '€1200', '850 EUR' -> {'price': 1200}; a sold, reserved or 'on request' line -> {}"""
    text = (text or "").replace("&euro;", "€").replace("&nbsp;", " ")
    if not text or re.search(r"müüdud|sold|broneeritud|reserv|kokkuleppel|päringu|request", text, re.I): return {}
    m = _EUR.search(text)
    if not m: return {}
    n = int(re.sub(r"\D", "", m.group(1) or m.group(2)))
    return {"price": n} if n >= 1 else {}
