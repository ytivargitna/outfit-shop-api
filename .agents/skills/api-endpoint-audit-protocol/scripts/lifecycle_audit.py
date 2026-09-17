#!/usr/bin/env python3
"""Real CRUD lifecycle tests against the live API.

Every created entity is marked TESTAUDIT and cleaned up (deleted) where a
delete endpoint exists. Financial flows use a dedicated test variant.
"""
import json
import time
import urllib.request
import urllib.error

import os

BASE = os.environ.get("API_BASE", "https://api.kesararamwithdigital.tech/api/v1")
TS = str(int(time.time()))[-6:]
results = []


def request(method, path, token=None, payload=None, timeout=40):
    url = BASE + path
    data = None
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, safe_json(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read()
            if e.status == 429 and attempt < 2:
                time.sleep(int(e.headers.get("Retry-After") or 5) + 1)
                continue
            return e.status, safe_json(body)
        except Exception as ex:  # noqa: BLE001
            if attempt < 2:
                time.sleep(2)
                continue
            return 0, str(ex)


def safe_json(body):
    try:
        return json.loads(body)
    except Exception:  # noqa: BLE001
        return body[:200].decode("utf-8", "replace") if isinstance(body, bytes) else body


def record(step, method, path, status, body, expect):
    ok = status == expect if isinstance(expect, int) else status in expect
    if isinstance(body, dict):
        detail = str(body.get("message") or (body.get("error") or {}).get("code") or "")[:150]
    else:
        detail = str(body)[:150]
    results.append({"step": step, "method": method, "path": path,
                    "status": status, "expected": expect, "ok": ok,
                    "detail": detail})
    mark = "OK " if ok else "!! "
    print(f"{mark}{step:38} {method:7} {path:52} -> {status} (expect {expect})")
    return status, body


def login(role):
    creds = {"admin": ("admin", os.environ.get("API_ADMIN_PW", "")), "manager": ("manager", os.environ.get("API_MANAGER_PW", "")),
             "cashier": ("cashier", os.environ.get("API_CASHIER_PW", "")), "staff": ("staff", os.environ.get("API_STAFF_PW", ""))}
    u, p = creds[role]
    st, body = request("POST", "/auth/login", payload={"username": u, "password": p, "device_name": "audit-lifecycle"})
    if st == 200 and isinstance(body, dict) and body.get("success"):
        return body["data"]["access_token"]
    raise SystemExit(f"login failed {role}: {st}")


def data_id(body, *keys):
    if isinstance(body, dict):
        d = body.get("data")
        if isinstance(d, dict):
            for k in keys:
                if k in d:
                    return d[k]
    return None


def main():
    admin = login("admin")
    manager = login("manager")
    cashier = login("cashier")
    staff = login("staff")

    # ---- category CRUD ----
    st, b = record("category create", "POST", "/categories", *request("POST", "/categories", manager, {"category_name": f"TESTAUDIT-CAT-{TS}", "description": "audit"}), expect=201)
    cat_id = data_id(b, "category_id")
    if cat_id:
        record("category read", "GET", f"/categories/{cat_id}", *request("GET", f"/categories/{cat_id}"), expect=200)
        record("category patch", "PATCH", f"/categories/{cat_id}", *request("PATCH", f"/categories/{cat_id}", manager, {"description": "audit-upd"}), expect=200)
        record("category delete", "DELETE", f"/categories/{cat_id}", *request("DELETE", f"/categories/{cat_id}", manager), expect=(200, 204))

    # ---- color CRUD ----
    st, b = record("color create", "POST", "/colors", *request("POST", "/colors", manager, {"color_name": f"TESTAUDIT-COLOR-{TS}", "hex_code": "#abcdef"}), expect=201)
    color_id = data_id(b, "color_id")
    if color_id:
        record("color patch", "PATCH", f"/colors/{color_id}", *request("PATCH", f"/colors/{color_id}", manager, {"color_name": f"TESTAUDIT-COLOR-{TS}U"}), expect=200)
        record("color delete", "DELETE", f"/colors/{color_id}", *request("DELETE", f"/colors/{color_id}", manager), expect=(200, 204))

    # ---- size CRUD ----
    st, b = record("size create", "POST", "/clothing-sizes", *request("POST", "/clothing-sizes", manager, {"size_name": f"AU{TS}"}), expect=201)
    size_id = data_id(b, "size_id")
    if size_id:
        record("size delete", "DELETE", f"/clothing-sizes/{size_id}", *request("DELETE", f"/clothing-sizes/{size_id}", manager), expect=(200, 204))

    # ---- brand CRUD ----
    st, b = record("brand create", "POST", "/brands", *request("POST", "/brands", manager, {"brand_name": f"TESTAUDIT-BRAND-{TS}"}), expect=201)
    brand_id = data_id(b, "brand_id")
    if brand_id:
        record("brand delete", "DELETE", f"/brands/{brand_id}", *request("DELETE", f"/brands/{brand_id}", manager), expect=(200, 204))

    # ---- product + variant + stock adjust ----
    st, b = record("product create", "POST", "/products", *request("POST", "/products", manager, {"product_name": f"TESTAUDIT-PRODUCT-{TS}", "category_id": 1}), expect=201)
    product_id = data_id(b, "product_id")
    variant_id = None
    if product_id:
        record("product read", "GET", f"/products/{product_id}", *request("GET", f"/products/{product_id}"), expect=200)
        record("product patch", "PATCH", f"/products/{product_id}", *request("PATCH", f"/products/{product_id}", manager, {"description": "audit updated"}), expect=200)
        st, vb = record("variant create", "POST", "/variants", *request("POST", "/variants", manager, {"product_id": product_id, "size_id": 1, "color_id": 1, "sku": f"AUDIT-{TS}", "cost_price": 1, "sale_price": 2, "quantity": 50}), expect=201)
        variant_id = data_id(vb, "variant_id")
        if variant_id:
            record("variant patch", "PATCH", f"/variants/{variant_id}", *request("PATCH", f"/variants/{variant_id}", manager, {"sale_price": 3}), expect=200)
            record("stock adjust", "POST", "/stock-movements/adjust", *request("POST", "/stock-movements/adjust", manager, {"variant_id": variant_id, "quantity": -1, "movement_type": "ADJUSTMENT", "note": "endpoint audit"}), expect=200)
        record("product images list", "GET", f"/products/{product_id}/images", *request("GET", f"/products/{product_id}/images"), expect=200)

    # ---- supplier CRUD ----
    st, b = record("supplier create", "POST", "/suppliers", *request("POST", "/suppliers", manager, {"supplier_name": f"TESTAUDIT-SUP-{TS}", "contact_person": "Audit", "phone": "010000000", "email": f"audit{TS}@test.local"}), expect=201)
    sup_id = data_id(b, "supplier_id")
    if sup_id:
        record("supplier patch", "PATCH", f"/suppliers/{sup_id}", *request("PATCH", f"/suppliers/{sup_id}", manager, {"phone": "011111111"}), expect=200)
        record("supplier delete", "DELETE", f"/suppliers/{sup_id}", *request("DELETE", f"/suppliers/{sup_id}", manager), expect=(200, 204))

    # ---- customer CRUD (cashier) ----
    st, b = record("customer create", "POST", "/customers", *request("POST", "/customers", cashier, {"customer_name": f"TESTAUDIT-CUST-{TS}", "phone": "012345678", "email": f"cust{TS}@test.local"}), expect=201)
    cust_id = data_id(b, "customer_id")
    if cust_id:
        record("customer patch", "PATCH", f"/customers/{cust_id}", *request("PATCH", f"/customers/{cust_id}", cashier, {"phone": "013456789"}), expect=200)

    # ---- employee CRUD (admin) ----
    st, b = record("employee create", "POST", "/employees", *request("POST", "/employees", admin, {"employee_name": f"TESTAUDIT-EMP-{TS}", "email": f"emp{TS}@test.local", "username": f"auditemp{TS}", "password": "AuditPass123!", "role": "STAFF"}), expect=201)
    emp_id = data_id(b, "employee_id")
    if emp_id:
        record("employee patch", "PATCH", f"/employees/{emp_id}", *request("PATCH", f"/employees/{emp_id}", admin, {"position": "Audit Temp"}), expect=200)
        record("employee delete", "DELETE", f"/employees/{emp_id}", *request("DELETE", f"/employees/{emp_id}", admin), expect=(200, 204))

    # ---- gift card issue + read ----
    st, b = record("gift card issue", "POST", "/gift-cards", *request("POST", "/gift-cards", manager, {"amount": 10, "initial_balance": 10}), expect=201)
    gcode = data_id(b, "code", "gift_card_code", "card_code")
    if gcode:
        record("gift card read", "GET", f"/gift-cards/{gcode}", *request("GET", f"/gift-cards/{gcode}"), expect=200)

    # ---- estimate -> convert ----
    st, b = record("estimate create", "POST", "/estimates", *request("POST", "/estimates", cashier, {"customer_id": cust_id or 1, "items": [{"variant_id": variant_id or 1, "quantity": 1}]}), expect=201)
    est_id = data_id(b, "estimate_id", "id")
    if est_id:
        record("estimate convert", "POST", f"/estimates/{est_id}/convert", *request("POST", f"/estimates/{est_id}/convert", manager, {"payment_method": "CASH"}), expect=(200, 201))

    # ---- checkout -> receipts -> void (test variant) ----
    sale_id = None
    if variant_id:
        st, b = record("checkout", "POST", "/orders/checkout", *request("POST", "/orders/checkout", cashier, {"items": [{"variant_id": variant_id, "quantity": 1}], "payment_method": "CASH", "tax_rate": 0}), expect=201)
        sale_id = data_id(b, "sale_id", "order_id", "id")
        if sale_id:
            record("order read", "GET", f"/orders/{sale_id}", *request("GET", f"/orders/{sale_id}", cashier), expect=200)
            record("receipt thermal", "GET", f"/orders/{sale_id}/receipt-thermal", *request("GET", f"/orders/{sale_id}/receipt-thermal", cashier), expect=200)
            record("invoice html", "GET", f"/orders/{sale_id}/invoice-pdf", *request("GET", f"/orders/{sale_id}/invoice-pdf", cashier), expect=200)
            record("khqr for order", "GET", f"/orders/{sale_id}/khqr", *request("GET", f"/orders/{sale_id}/khqr", cashier), expect=200)
            record("void", "POST", f"/orders/{sale_id}/void", *request("POST", f"/orders/{sale_id}/void", manager, {"reason": "endpoint audit cleanup"}), expect=200)

    # ---- promotion CRUD ----
    st, b = record("promotion create", "POST", "/promotions", *request("POST", "/promotions", manager, {"title": f"TESTAUDIT-PROMO-{TS}", "discount_type": "PERCENTAGE", "discount_value": 5, "start_date": "2026-08-01", "end_date": "2026-08-31"}), expect=201)
    prom_id = data_id(b, "promotion_id", "id")
    if prom_id:
        record("promotion delete", "DELETE", f"/promotions/{prom_id}", *request("DELETE", f"/promotions/{prom_id}", manager), expect=(200, 204))

    # ---- banner CRUD ----
    st, b = record("banner create", "POST", "/marketing/banners", *request("POST", "/marketing/banners", manager, {"title": f"TESTAUDIT-BANNER-{TS}", "image_url": "https://example.com/x.png", "placement": "HOME_TOP"}), expect=201)
    ban_id = data_id(b, "banner_id", "id")
    if ban_id:
        record("banner delete", "DELETE", f"/marketing/banners/{ban_id}", *request("DELETE", f"/marketing/banners/{ban_id}", manager), expect=(200, 204))

    # ---- webhook create -> test -> delete ----
    st, b = record("webhook create", "POST", "/webhooks/subscribe", *request("POST", "/webhooks/subscribe", manager, {"event_type": "LOW_STOCK_ALERT", "url": "https://example.com/hook"}), expect=201)
    wh_id = data_id(b, "webhook_id", "id")
    if wh_id:
        record("webhook test", "POST", "/webhooks/test", *request("POST", "/webhooks/test", manager, {"webhook_id": wh_id}), expect=200)
        record("webhook delete", "DELETE", f"/webhooks/{wh_id}", *request("DELETE", f"/webhooks/{wh_id}", manager), expect=(200, 204))

    # ---- stock transfer create -> cancel ----
    st, b = record("transfer create", "POST", "/stock-transfers", *request("POST", "/stock-transfers", manager, {"from_branch_id": 1, "to_branch_id": 2, "items": [{"variant_id": variant_id or 1, "quantity": 1}]}), expect=201)
    tr_id = data_id(b, "transfer_id", "id")
    if tr_id:
        record("transfer cancel", "POST", f"/stock-transfers/{tr_id}/cancel", *request("POST", f"/stock-transfers/{tr_id}/cancel", manager, {"reason": "audit"}), expect=200)

    # ---- shift open -> close (cashier) ----
    st, b = record("shift open", "POST", "/shifts/open", *request("POST", "/shifts/open", cashier, {"opening_float_usd": 100, "opening_float_khr": 0}), expect=201)
    shift_id = data_id(b, "shift_id", "id")
    if shift_id:
        record("shift current", "GET", "/shifts/current", *request("GET", "/shifts/current", cashier), expect=200)
        record("shift close", "POST", "/shifts/close", *request("POST", "/shifts/close", cashier, {"closing_cash_usd": 100}), expect=200)

    # ---- guest cart lifecycle ----
    record("cart add", "POST", "/cart/items", *request("POST", "/cart/items", None, {"variant_id": variant_id or 1, "quantity": 1}), expect=(200, 201))
    st, b = record("cart view", "GET", "/cart", *request("GET", "/cart"), expect=200)
    cart_item = None
    if isinstance(b, dict):
        items = b.get("data", {}).get("items") if isinstance(b.get("data"), dict) else None
        if items:
            cart_item = items[0].get("cart_item_id") or items[0].get("id")
    if cart_item:
        record("cart update qty", "PATCH", f"/cart/items/{cart_item}", *request("PATCH", f"/cart/items/{cart_item}", None, {"quantity": 2}), expect=200)
        record("cart remove item", "DELETE", f"/cart/items/{cart_item}", *request("DELETE", f"/cart/items/{cart_item}"), expect=(200, 204))
    record("cart clear", "DELETE", "/cart", *request("DELETE", "/cart"), expect=(200, 204))

    # ---- wishlist toggle (guest) ----
    record("wishlist toggle", "POST", "/wishlist/toggle", *request("POST", "/wishlist/toggle", None, {"customer_id": 1, "product_id": product_id or 1}), expect=(200, 201))

    # ---- exports (reads) ----
    record("export inventory excel", "GET", "/exports/inventory/excel", *request("GET", "/exports/inventory/excel", manager), expect=200)
    record("export movements csv", "GET", "/exports/stock-movements/csv", *request("GET", "/exports/stock-movements/csv", manager), expect=200)

    # ---- avatar (new endpoint; old build expected 404) ----
    record("avatar set url", "POST", "/auth/avatar", *request("POST", "/auth/avatar", staff, {"avatar_url": "https://example.com/a.png"}), expect=(200, 404))

    # cleanup: delete test product + customer (soft deletes)
    if product_id:
        record("cleanup product delete", "DELETE", f"/products/{product_id}", *request("DELETE", f"/products/{product_id}", manager), expect=(200, 204))
    if cust_id:
        record("cleanup customer delete", "DELETE", f"/customers/{cust_id}", *request("DELETE", f"/customers/{cust_id}", manager), expect=(200, 204))

    ok = sum(1 for r in results if r["ok"])
    print(f"\nLIFECYCLE SUMMARY: {ok}/{len(results)} steps as expected")
    json.dump(results, open("/tmp/lifecycle_audit_prod.json", "w"), indent=1)


if __name__ == "__main__":
    main()
