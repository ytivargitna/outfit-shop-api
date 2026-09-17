import subprocess, json

def api(method, path, body=None, token=None):
    url = "https://api.kesararamwithdigital.tech/api/v1" + path
    cmd = ["curl", "-s", "-X", method, url, "-H", "Content-Type: application/json"]
    if token:
        cmd += ["-H", "Authorization: Bearer " + token]
    if body:
        cmd += ["-d", json.dumps(body)]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=15).stdout
    try:
        return json.loads(out)
    except Exception:
        return {"raw": out[:200]}

# Login
r = api("POST", "/auth/login", {"username": "admin", "password": "Admin#Secure#2026"})
token = (r.get("data") or {}).get("access_token", "")
print("Token:", token[:20] + "...")
print()

tests = [
    ("POST", "/wishlist", {"product_id": 182, "variant_id": 174, "customer_id": 1}),
    ("POST", "/shifts/open", {"opening_float_usd": 200.0, "branch_id": 1}),
    ("POST", "/gift-cards/issue", {"initial_balance": 50.0, "expiry_date": "2027-12-31"}),
    ("GET",  "/offline/manifest", None),
    ("GET",  "/alerts/active", None),
    ("POST", "/purchases/auto-generate", {"items": [{"variant_id": 174, "quantity": 10, "cost_price": 45.0}]}),
    ("POST", "/employees", {"employee_name": "Test User", "email": "testuser@test.com", "username": "testuser99", "password": "Test@123!", "role": "STAFF"}),
    ("POST", "/webhooks/subscribe", {"url": "https://webhook.site/test", "event_type": "LOW_STOCK_ALERT"}),
    ("POST", "/marketing/banners", {"title": "Test Banner", "subtitle": "Sub", "image_url": "https://example.com/img.jpg", "link_url": "https://example.com", "sort_order": 1}),
    ("POST", "/purchases", {"supplier_id": 1, "items": [{"variant_id": 174, "quantity": 5, "cost_price": 45.0}]}),
    ("PUT",  "/clothing-sizes/1", {"size_name": "Small", "size_code": "S"}),
    ("PUT",  "/colors/1", {"color_name": "Black", "color_code": "BLK", "hex_code": "#000000"}),
    ("PUT",  "/products/182", {"product_name": "Gucci Oxford Shirt", "category_id": 14}),
    ("PUT",  "/variants/174", {"sale_price": 125.0}),
    ("PUT",  "/suppliers/1", {"supplier_name": "Test Supplier", "contact_name": "Ratha"}),
    ("POST", "/auth/register", {"name": "New Manager", "email": "newmgr@test.com", "password": "Manager@2026", "role": "manager"}),
    ("DELETE", "/categories/14", None),
]

for method, path, body in tests:
    r2 = api(method, path, body, token)
    code = r2.get("status_code", "?")
    err = r2.get("error") or {}
    msg = (err.get("message", "") if isinstance(err, dict) else str(err))[:100]
    errs = r2.get("errors") or {}
    if errs:
        msg = str(errs)[:100]
    if not msg:
        msg = r2.get("message", "")[:80]
    print("[" + str(code) + "] " + method + " " + path + ": " + msg)
