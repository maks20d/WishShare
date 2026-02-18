try:
    from playwright.sync_api import sync_playwright
    print("playwright import ok")
except Exception as e:
    print(f"playwright import failed: {e}")

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        browser.close()
        print("playwright browser launch ok")
except Exception as e:
    print(f"playwright browser launch failed: {e}")
