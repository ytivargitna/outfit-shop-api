#!/usr/bin/env python3
"""Classify sweep results: expected vs deviation, grouped by cause."""
import json
from collections import Counter, defaultdict

rs = json.load(open("/tmp/endpoint_audit_prod.json"))

# Endpoints where the mutation probe legitimately succeeds without fields
NO_FIELD_PROBES_OK = {
    ("POST", "/auth/2fa/setup"),
    ("POST", "/auth/logout"),
    ("POST", "/auth/refresh"),
    ("POST", "/auth/revoke-all"),
    ("POST", "/customers/{id}/data-exports"),
    ("POST", "/compliance/customers/{id}/export-data"),
}
# Reads that legitimately return non-200 on empty/placeholder ids
MAY_MISS = {
    ("GET", "/orders/{id}"), ("GET", "/sales/{id}"),
    ("GET", "/orders/{id}/khqr"), ("GET", "/orders/{id}/receipt-thermal"),
    ("GET", "/orders/{id}/invoice-pdf"), ("GET", "/sales/{id}/khqr"),
    ("GET", "/sales/{id}/receipt-thermal"), ("GET", "/sales/{id}/invoice-pdf"),
    ("GET", "/products/{id}/download"), ("GET", "/uploads/image/{publicId}"),
    ("GET", "/gift-cards/{code}"), ("GET", "/variants/barcode/{barcode}"),
    ("GET", "/exports/z-report/{id}/thermal"), ("GET", "/shifts/current"),
}

def expected(r):
    m, p, actor = r["method"], r["path"], r["actor"]
    key = (m, p)
    if r.get("probe") == "guest-auth":
        return 401
    if m in ("GET",):
        return 200
    if key in NO_FIELD_PROBES_OK:
        return (200, 201)
    if m == "DELETE":
        return (200, 204, 404, 422)
    # mutation probes with empty payload -> validation error is the healthy path
    return (200, 201, 422)

deviations = []
for r in rs:
    exp = expected(r)
    ok = r["status"] in exp if isinstance(exp, tuple) else r["status"] == exp
    r["expected"] = exp if isinstance(exp, tuple) else [exp]
    r["verdict"] = "OK" if ok else "DEVIATION"
    if not ok and (r["method"], r["path"]) not in MAY_MISS:
        deviations.append(r)
    elif not ok:
        r["verdict"] = "OK(placeholder-id)"

print("total:", len(rs))
print("verdicts:", dict(Counter(r["verdict"] for r in rs)))
print("\n=== DEVIATIONS (excluding placeholder-id reads) ===")
groups = defaultdict(list)
for r in deviations:
    groups[r["status"]].append(r)
for status in sorted(groups):
    print(f"\n--- HTTP {status} ({len(groups[status])}) ---")
    for r in groups[status]:
        print(f"  {r['actor']:8} {r['method']:7} {r['path']:55} {r.get('error_code') or ''}")

json.dump(rs, open("/tmp/endpoint_audit_classified.json", "w"), indent=1)
