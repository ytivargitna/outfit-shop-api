#!/usr/bin/env python3
"""OutfitShop API endpoint audit harness.

Sweeps every route with guest + 4 role tokens, records status codes.
Dangerous mutations get validation-probe payloads (expect 422, no side
effects). Real CRUD lifecycles are done by the dedicated lifecycle phase.
"""
import json
import re
import sys
import time
import urllib.request
import urllib.error

import os

BASE = os.environ.get("API_BASE", "https://api.kesararamwithdigital.tech/api/v1")
CREDS = {
    "admin": ("admin", os.environ.get("API_ADMIN_PW", "")),
    "manager": ("manager", os.environ.get("API_MANAGER_PW", "")),
    "cashier": ("cashier", os.environ.get("API_CASHIER_PW", "")),
    "staff": ("staff", os.environ.get("API_STAFF_PW", "")),
}

ROUTES_FILE = os.environ.get("ROUTES_FILE", "/tmp/routes_api.json")
OUT_FILE = os.environ.get("OUT_FILE", "/tmp/endpoint_audit_prod.json")


def request(method, path, token=None, payload=None, raw=False, timeout=30):
    url = BASE + path
    data = None
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
                return resp.status, (body if raw else safe_json(body))
        except urllib.error.HTTPError as e:
            body = e.read()
            if e.status == 429 and attempt < 3:
                wait = int(e.headers.get("Retry-After") or 5)
                time.sleep(wait + 0.5)
                continue
            return e.status, (body if raw else safe_json(body))
        except Exception as e:  # noqa: BLE001
            if attempt < 3:
                time.sleep(2)
                continue
            return 0, str(e)


def safe_json(body):
    try:
        return json.loads(body)
    except Exception:  # noqa: BLE001
        return body[:200].decode("utf-8", "replace") if isinstance(body, bytes) else body


def login(role):
    user, pw = CREDS[role]
    status, body = request("POST", "/auth/login", payload={"username": user, "password": pw, "device_name": "endpoint-audit"})
    if status == 200 and isinstance(body, dict) and body.get("success"):
        d = body["data"]
        return d.get("access_token")
    print(f"LOGIN FAILED {role}: {status} {str(body)[:200]}")
    return None


ROLE_TIER = {
    "guest": 0, "staff": 1, "cashier": 2, "manager": 3, "admin": 4,
}

# Routes whose tier the middleware implies (route:list emits full class names).
def route_tier(route):
    mw = route.get("middleware", [])
    if isinstance(mw, str):
        mw = [mw]
    role_mw = [m for m in mw if "CheckRole" in m]
    authed = any("Authenticate" in m or m.startswith("auth") for m in mw)
    if not role_mw and not authed:
        return 0
    if role_mw:
        arg = role_mw[0].split(":", 1)[1] if ":" in role_mw[0] else ""
        roles = [r.strip() for r in arg.split(",")]
        if roles == ["ADMIN"]:
            return 4
        if "MANAGER" in roles:
            return 3
        if "CASHIER" in roles:
            return 2
        return 4
    return 1


# Validation-probe payloads for mutating endpoints (expect 422 - no effects).
PROBES = {
    "/auth/register": [{}],
    "/auth/forgot-password": [{}],
    "/auth/reset-password": [{}],
    "/auth/admin-reset-password": [{}],
    "/auth/2fa/setup": None,
    "/auth/2fa/verify": [{}],
    "/auth/avatar": [{}],
    "/orders/checkout": [{}],
    "/orders/{id}/void": [{}],
    "/sales/checkout": [{}],
    "/sales/{id}/void": [{}],
    "/stock-movements/adjust": [{}],
    "/inventory/stock-opname": [{}],
    "/inventory/bulk-adjust": [{}],
    "/variants/bulk-price-update": [{}],
    "/products/bulk-import": [{}],
    "/purchases/bulk-receive": [{}],
    "/compliance/customers/{id}/forget-me": [{}],
    "/customers/{id}/erasure-requests": [{}],
    "/customers/{id}/data-exports": None,
    "/admin/broadcast-alert": [{}],
    "/offline/push-transactions": [{}],
    "/webhooks/test": [{}],
    "/estimates": [{}],
    "/gift-cards": [{}],
    "/gift-cards/issue": [{}],
    "/shipping-orders": [{}],
    "/shipping-orders/{id}": [{}],
    "/stock-transfers/{id}/receive": [{}],
}


def build_payloads(uri, method):
    if method in ("GET", "HEAD"):
        return None
    if uri in PROBES:
        p = PROBES[uri]
        return [p] if p is not None else []
    # generic create probes for catalog CRUD (validation failure expected only
    # if fields missing; lifecycle phase covers real creates)
    generic = {
        "POST": [{}],
        "PUT": [{}],
        "PATCH": [{}],
        "DELETE": [],
    }
    return generic.get(method, [])


def main():
    routes = json.load(open(ROUTES_FILE))
    api_routes = []
    for r in routes:
        uri = r["uri"]
        if not uri.startswith("api/"):
            continue
        path = "/" + uri[len("api/"):]
        if path.startswith("/v1/"):
            path = path[len("/v1"):]
        methods = [m for m in r["method"].split("|") if m != "HEAD"]
        for m in methods:
            api_routes.append({"method": m, "path": path, "middleware": r.get("middleware", []), "name": r.get("name")})

    tokens = {}
    for role in CREDS:
        t = login(role)
        if t:
            tokens[role] = t

    ids = resolve_ids(tokens.get("admin"))

    results = []
    for r in api_routes:
        path = substitute(r["path"], ids)
        tier = route_tier(r)
        actor = {0: "guest", 1: "staff", 2: "cashier", 3: "manager", 4: "admin"}[tier]
        payload_sets = build_payloads(r["path"], r["method"])
        # First: the expected-tier actor call
        for pl in (payload_sets if payload_sets is not None else [None]):
            status, body = request(r["method"], path, tokens.get(actor), pl)
            msg = ""
            code = None
            if isinstance(body, dict):
                msg = str(body.get("message") or "")[:120]
                code = (body.get("error") or {}).get("code") if isinstance(body.get("error"), dict) else None
            else:
                msg = str(body)[:120]
            results.append({
                "method": r["method"], "path": r["path"], "resolved": path,
                "actor": actor, "status": status,
                "error_code": code,
                "message": msg,
            })
        # Guest probe on protected routes (expect 401)
        if tier > 0:
            status, body = request(r["method"], path, None, ([{}] if r["method"] not in ("GET", "HEAD", "DELETE") else None))
            results.append({
                "method": r["method"], "path": r["path"], "resolved": path,
                "actor": "guest", "status": status,
                "error_code": None,
                "message": "",
                "probe": "guest-auth",
            })

    json.dump(results, open(OUT_FILE, "w"), indent=1)
    print(f"done: {len(results)} results -> {OUT_FILE}")


def resolve_ids(admin_token):
    ids = {"id": "1", "product_id": "1", "category_id": "1", "brand_id": "1",
           "size_id": "1", "color_id": "1", "employee_id": "1", "customer_id": "1",
           "supplier_id": "1", "sale_id": "1", "order_id": "1", "purchase_id": "1",
           "transfer_id": "1", "shift_id": "1", "bundle_id": "1", "promotion_id": "1",
           "webhook_id": "1", "banner_id": "1", "audit_id": "1", "estimate_id": "1",
           "shipping_id": "1", "imageId": "x", "image_id": "x", "code": "TESTCODE",
           "barcode": "0000000000000", "variant_id": "1", "publicId": "x", "review_id": "1"}
    if not admin_token:
        return ids
    def first_from(path, key, data_key=None):
        st, body = request("GET", path, admin_token)
        if st == 200 and isinstance(body, dict):
            data = body.get("data")
            if isinstance(data, list) and data:
                item = data[0]
                if isinstance(item, dict):
                    k = data_key or key
                    if k in item:
                        return str(item[k])
                    for cand in (key, "id"):
                        if cand in item:
                            return str(item[cand])
        return None
    mapping = [
        ("/products?per_page=1", "product_id", "product_id"),
        ("/variants?per_page=1", "variant_id", "variant_id"),
        ("/categories?per_page=1", "category_id", "category_id"),
        ("/brands?per_page=1", "brand_id", "brand_id"),
        ("/clothing-sizes?per_page=1", "size_id", "size_id"),
        ("/colors?per_page=1", "color_id", "color_id"),
        ("/customers?per_page=1", "customer_id", "customer_id"),
        ("/suppliers?per_page=1", "supplier_id", "supplier_id"),
        ("/employees?per_page=1", "employee_id", "employee_id"),
        ("/purchases?per_page=1", "purchase_id", "purchase_id"),
        ("/stock-transfers?per_page=1", "transfer_id", "transfer_id"),
        ("/bundles?per_page=1", "bundle_id", "bundle_id"),
        ("/promotions?per_page=1", "promotion_id", "promotion_id"),
        ("/webhooks?per_page=1", "webhook_id", "webhook_id"),
        ("/audit-logs?per_page=1", "audit_id", "audit_id"),
        ("/invoices?per_page=1", "estimate_id", "invoice_id"),
    ]
    for path, key, dk in mapping:
        v = first_from(path, key, dk)
        if v:
            ids[key] = v
    # sale/order: fetch orders list
    v = first_from("/orders?per_page=1", "order_id", "sale_id")
    if v:
        ids["order_id"] = v
        ids["sale_id"] = v
    # shipping order id
    v = first_from("/shipping-orders?per_page=1", "shipping_id", "shipping_order_id")
    if v:
        ids["shipping_id"] = v
    print("resolved ids:", {k: ids[k] for k in ("product_id", "variant_id", "customer_id", "order_id")})
    return ids


def substitute(path, ids):
    def rep(m):
        return ids.get(m.group(1), m.group(0))
    return re.sub(r"\{(\w+)\}", rep, path)


if __name__ == "__main__":
    main()
