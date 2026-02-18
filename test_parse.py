import httpx, json

# Test 1: simple site
print("=== Test 1: Simple site ===")
resp = httpx.post("http://127.0.0.1:8000/parse-url", json={"url": "https://www.amazon.com"}, timeout=30)
print(f"Status: {resp.status_code}")
print(json.dumps(resp.json(), ensure_ascii=False, indent=2))

# Test 2: OG preview endpoint
print("\n=== Test 2: /og/preview ===")
resp = httpx.post("http://127.0.0.1:8000/og/preview", json={"url": "https://www.amazon.com"}, timeout=30)
print(f"Status: {resp.status_code}")
print(json.dumps(resp.json(), ensure_ascii=False, indent=2))
