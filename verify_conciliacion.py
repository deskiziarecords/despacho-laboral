"""
Verification script: test conciliacion automation in production.
Drives the browser end-to-end and reports status transitions.
"""
import time
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

BASE = "https://despacho-laboral-production.up.railway.app"
USERNAME = "admin"
PASSWORD = "Admin123!"
MAX_WAIT = 360  # seconds to wait for the automation to complete

def log(msg):
    print(msg, flush=True)

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()

        # ── STEP 1: Login ──────────────────────────────────────────────────
        log(f"\n[1] Navigating to login: {BASE}/accounts/login/")
        page.goto(f"{BASE}/accounts/login/", timeout=30000)
        page.fill('[name="username"]', USERNAME)
        page.fill('[name="password"]', PASSWORD)
        page.click('[type="submit"]')
        page.wait_for_load_state("networkidle", timeout=15000)
        current = page.url
        log(f"    → After login URL: {current}")
        if "login" in current:
            log("ERROR: Still on login page — wrong credentials?")
            log(f"  Page text: {page.inner_text('body')[:300]}")
            browser.close()
            sys.exit(1)
        log("    ✅ Logged in")

        # ── STEP 2: Find an expediente with CURP + telefono ───────────────
        log(f"\n[2] Looking for expedientes list...")
        page.goto(f"{BASE}/expedientes/", timeout=20000)
        page.wait_for_load_state("networkidle", timeout=15000)

        # Get first expediente link
        links = page.locator("table tbody tr a, .expediente-link, a[href*='/expedientes/']").all()
        expediente_url = None
        for link in links:
            href = link.get_attribute("href") or ""
            if "/expedientes/" in href and href.rstrip("/").split("/")[-1].isdigit():
                expediente_url = href if href.startswith("http") else BASE + href
                break

        if not expediente_url:
            # Try finding any link with a number pattern like /expedientes/123/
            import re
            hrefs = page.eval_on_selector_all(
                "a", "els => els.map(e => e.href)"
            )
            for h in hrefs:
                if re.search(r"/expedientes/\d+/?$", h):
                    expediente_url = h
                    break

        if not expediente_url:
            log("ERROR: Could not find any expediente link on the list page")
            log(f"  Page text: {page.inner_text('body')[:500]}")
            browser.close()
            sys.exit(1)

        log(f"    → Found expediente: {expediente_url}")

        # ── STEP 3: Open expediente detail and check CURP/telefono ─────────
        log(f"\n[3] Opening expediente detail...")
        page.goto(expediente_url, timeout=20000)
        page.wait_for_load_state("networkidle", timeout=15000)
        body_text = page.inner_text("body")

        # Look for conciliacion automation button
        concil_btn = page.locator("a[href*='conciliacion-automatica'], a:has-text('Conciliación'), a:has-text('conciliacion')")
        concil_count = concil_btn.count()
        log(f"    Conciliacion buttons found: {concil_count}")

        if concil_count == 0:
            # Try to find the expediente pk from the URL and construct the automation URL
            import re
            pk_match = re.search(r"/expedientes/(\d+)", expediente_url)
            if pk_match:
                pk = pk_match.group(1)
                concil_url = f"{BASE}/expedientes/{pk}/conciliacion-automatica/"
                log(f"    → Trying direct automation URL: {concil_url}")
            else:
                log("ERROR: Could not determine expediente pk")
                browser.close()
                sys.exit(1)
        else:
            concil_url = concil_btn.first.get_attribute("href")
            if not concil_url.startswith("http"):
                concil_url = BASE + concil_url
            log(f"    → Conciliacion URL: {concil_url}")

        # ── STEP 4: Open the confirmation page ────────────────────────────
        log(f"\n[4] Opening conciliacion confirmation page...")
        page.goto(concil_url, timeout=20000)
        page.wait_for_load_state("networkidle", timeout=15000)
        confirm_text = page.inner_text("body")

        if "CURP" in confirm_text and ("debe tener" in confirm_text or "required" in confirm_text.lower()):
            log("ERROR: Expediente missing CURP or telefono — need a different expediente")
            log(f"  Message: {confirm_text[:300]}")
            browser.close()
            sys.exit(1)

        if "confirmar" not in confirm_text.lower() and "conciliaci" not in confirm_text.lower():
            log(f"  Unexpected page — text: {confirm_text[:400]}")

        log(f"    Page title: {page.title()}")
        log(f"    ✅ Confirmation page loaded")

        # ── STEP 5: Debug cookies then submit via Python requests ─────────
        log(f"\n[5] Checking session cookies and submitting...")

        # Get all cookies from Playwright context
        cookies = ctx.cookies()
        cookie_dict = {c["name"]: c["value"] for c in cookies}
        log(f"    Cookies present: {list(cookie_dict.keys())}")
        has_session = "sessionid" in cookie_dict
        has_csrf = "csrftoken" in cookie_dict
        log(f"    sessionid: {'YES' if has_session else 'NO'}")
        log(f"    csrftoken: {'YES' if has_csrf else 'NO'}")

        # Get CSRF token from the form
        csrf_form_token = page.eval_on_selector(
            'input[name="csrfmiddlewaretoken"]',
            "el => el.value"
        )
        log(f"    CSRF form token: {'YES (' + csrf_form_token[:8] + '...)' if csrf_form_token else 'NO'}")

        # Use urllib with all cookies + correct headers
        import urllib.request, urllib.parse, urllib.error, re as _re
        import http.cookiejar, ssl as _ssl
        _ssl_ctx = _ssl.create_default_context()
        _ssl_ctx.check_hostname = False
        _ssl_ctx.verify_mode = _ssl.CERT_NONE

        pk_match = _re.search(r"/expedientes/(\d+)", expediente_url)
        pk = pk_match.group(1)
        post_url = f"{BASE}/expedientes/{pk}/conciliacion-automatica/"

        # Build cookie header manually
        cookie_header = "; ".join(f"{c['name']}={c['value']}" for c in cookies)

        post_data = urllib.parse.urlencode({
            "csrfmiddlewaretoken": csrf_form_token,
            "modo": "automatico",
        }).encode("utf-8")

        req = urllib.request.Request(
            post_url,
            data=post_data,
            method="POST",
            headers={
                "Cookie": cookie_header,
                "Referer": post_url,
                "Origin": BASE,
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0 (compatible; verify-script)",
                "X-Forwarded-Proto": "https",
            },
        )

        # Don't follow redirects so we can see where it goes
        opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None

        no_redir_opener = urllib.request.build_opener(
            NoRedirect(),
            urllib.request.HTTPSHandler(context=_ssl_ctx),
        )
        try:
            with no_redir_opener.open(req, timeout=15) as resp:
                status = resp.status
                location = resp.headers.get("Location", "")
                log(f"    POST status: {status}, Location: {location}")
        except urllib.error.HTTPError as e:
            log(f"    POST HTTP error: {e.code}, Location: {e.headers.get('Location', '')}")
            location = e.headers.get("Location", "")
            status = e.code

        if location and "procesando" in location:
            progress_url = BASE + location if location.startswith("/") else location
        else:
            # Fall back — browser click
            log(f"    POST result: status={status}, redirects to: {location}")
            log(f"    Trying browser button click as fallback...")
            page.reload()
            page.wait_for_load_state("networkidle", timeout=10000)
            try:
                page.click('input[name="modo"][value="automatico"]', timeout=2000)
            except Exception:
                pass
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle", timeout=15000)
            progress_url = page.url

        log(f"    → Progress URL: {progress_url}")

        if "procesando" not in progress_url and "conciliacion" not in progress_url:
            log(f"WARNING: Unexpected redirect URL: {progress_url}")
            log(f"  Page: {page.inner_text('body')[:300]}")

        log(f"    ✅ Automation started, now on progress page")

        # ── STEP 6: Poll status API until done (or timeout) ──────────────
        import re
        task_match = re.search(r"/conciliacion/(\d+)/procesando", progress_url)
        if not task_match:
            log(f"ERROR: Could not extract task ID from URL: {progress_url}")
            browser.close()
            sys.exit(1)

        task_id = task_match.group(1)
        status_url = f"{BASE}/conciliacion/{task_id}/estado/"
        log(f"\n[6] Polling task status: {status_url}")

        import json, urllib.request, urllib.error

        # Grab session cookies from playwright to use in urllib
        cookies = ctx.cookies()
        cookie_header = "; ".join(f"{c['name']}={c['value']}" for c in cookies)

        # Also open a second page to watch the portal live during execution
        portal_page = ctx.new_page()

        start = time.time()
        last_estado = None
        portal_captured = False
        while True:
            elapsed = int(time.time() - start)
            if elapsed > MAX_WAIT:
                log(f"\n❌ TIMEOUT after {elapsed}s — task never completed")
                break

            try:
                req = urllib.request.Request(status_url, headers={"Cookie": cookie_header})
                with urllib.request.urlopen(req, timeout=10, context=_ssl_ctx) as resp:
                    data = json.loads(resp.read())
            except Exception as e:
                log(f"  [{elapsed}s] Poll error: {e}")
                time.sleep(5)
                continue

            estado = data.get("estado", "?")
            detalle = data.get("detalle", "")
            if estado != last_estado:
                log(f"  [{elapsed}s] Estado: {estado} | error={data.get('error','')[:80]} | folio={data.get('folio','')}")
                last_estado = estado

            # When task fails, capture portal diagnostic info
            import re as _re2
            
            # Try both URL patterns: "URL=" and "URL documento:"
            _url_match = _re2.search(r'URL_FINAL=([^\s|]+)', detalle) or _re2.search(r'URL=([^\s|]+)', detalle)
            _doc_url_match = _re2.search(r'URL_DOC=([^\s|]+)', detalle) or _re2.search(r'URL documento: ([^\s|]+)', detalle)
            
            if not portal_captured and estado == "fallido":
                # Try the doc URL first (more likely to have the folio/PDF info)
                portal_url = None
                if _doc_url_match:
                    portal_url = _doc_url_match.group(1).strip()
                    log(f"\n  Capturing portal document page: {portal_url}")
                elif _url_match:
                    portal_url = _url_match.group(1).strip()
                    log(f"\n  Capturing portal page: {portal_url}")
                
                if portal_url:
                    try:
                        portal_page.goto(portal_url, timeout=20000)
                        portal_page.wait_for_load_state("networkidle", timeout=10000)
                        portal_page.screenshot(path="verify_portal.png", full_page=True)
                        page_text = portal_page.inner_text("body")
                        log(f"  Portal page text (first 1200 chars):\n{page_text[:1200]}")
                        # Also dump all links
                        links = portal_page.eval_on_selector_all(
                            "a", "els => els.map(e => ({href: e.href, text: e.textContent.trim()}))"
                        )
                        log(f"  Links on portal page: {[l for l in links if l['href'] and l['text']][:20]}")
                        buttons = portal_page.eval_on_selector_all(
                            "button", "els => els.map(e => e.textContent.trim())"
                        )
                        log(f"  Buttons on portal page: {buttons[:20]}")
                        # Also dump all input fields and their values
                        inputs = portal_page.eval_on_selector_all(
                            "input, select, textarea", 
                            "els => els.map(e => ({name: e.name, id: e.id, value: e.value, type: e.type}))"
                        )
                        log(f"  Inputs on portal page: {[i for i in inputs if i['name'] or i['id']][:15]}")
                    except Exception as e:
                        log(f"  Portal capture failed: {e}")
                    portal_captured = True

            if estado in ("completado", "fallido"):
                log(f"\n{'✅' if estado=='completado' else '❌'} Final state: {estado} after {elapsed}s")
                if estado == "completado":
                    log(f"  Folio: {data.get('folio','N/A')}")
                else:
                    log(f"  Error: {data.get('error','')}")
                    detalle = data.get('detalle', '')
                    log(f"  Detalle: {detalle[:1500] if detalle else '(empty)'}")
                break

            time.sleep(5)

        # Screenshot of Django progress page
        try:
            page.goto(progress_url, timeout=10000)
            page.wait_for_load_state("networkidle", timeout=10000)
            page.screenshot(path="verify_result.png", full_page=True)
            log(f"\n📸 Django progress page screenshot: verify_result.png")
        except Exception as e:
            log(f"  Screenshot failed: {e}")

        browser.close()
        log("\n=== DONE ===")

if __name__ == "__main__":
    run()
