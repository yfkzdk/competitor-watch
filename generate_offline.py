#!/usr/bin/env python
"""Generate offline standalone HTML files for the competitor-watch demo"""
import json, os, re

BASE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.join(BASE, "dashboard", "templates")
STATIC = os.path.join(BASE, "dashboard", "static")

# Load extracted API data
with open(os.path.join(BASE, "offline_data.json"), "r", encoding="utf-8") as f:
    API_DATA = json.load(f)

# Load cyberpunk CSS
with open(os.path.join(STATIC, "cyberpunk.css"), "r", encoding="utf-8") as f:
    CYBERPUNK_CSS = f.read()

# ── Helper: build fetch interceptor script ──
def build_interceptor(endpoint_keys):
    """Build a script tag that intercepts fetch() and serves embedded data."""
    subset = {}
    for key in endpoint_keys:
        if key in API_DATA:
            subset[key] = API_DATA[key]

    # Also add fuzzy matches for dynamic URLs (competitor_id, etc.)
    for full_key, val in API_DATA.items():
        for partial in endpoint_keys:
            if partial.rstrip("?") in full_key or full_key.startswith(partial):
                subset[full_key] = val

    json_data = json.dumps(subset, ensure_ascii=False)

    return f'''<script>
// ══════════════════════════════════════════════════════
// 离线演示数据 — 预提取自 API，无需后端服务器
// ══════════════════════════════════════════════════════
const __EMBEDDED__ = {json_data};

// Stub WebSocket to prevent connection attempts
window.WebSocket = window.WebSocket || function() {{
    const ws = {{ readyState: 3, send: ()=>{{}}, close: ()=>{{}} }};
    setTimeout(() => ws.onclose && ws.onclose(), 0);
    return ws;
}};

const __origFetch__ = window.fetch;
window.fetch = function(url, options) {{
    const urlStr = typeof url === 'string' ? url : (url.url || String(url));
    const urlClean = urlStr.split("?")[0];

    // Exact match first
    if (__EMBEDDED__[urlStr]) {{
        return Promise.resolve({{
            ok: true, status: 200,
            json: () => Promise.resolve(__EMBEDDED__[urlStr]),
            text: () => Promise.resolve(JSON.stringify(__EMBEDDED__[urlStr])),
        }});
    }}

    // Fuzzy match: find key contained in url or vice versa
    for (const [key, val] of Object.entries(__EMBEDDED__)) {{
        const keyBase = key.split("?")[0];
        if (urlClean.endsWith(keyBase) || keyBase.endsWith(urlClean) || urlStr.includes(keyBase)) {{
            return Promise.resolve({{
                ok: true, status: 200,
                json: () => Promise.resolve(val),
                text: () => Promise.resolve(JSON.stringify(val)),
            }});
        }}
    }}

    // Fallback: try real fetch (will fail if server not running, that's OK)
    console.warn("[Offline Demo] No embedded data for:", urlStr);
    return __origFetch__(url, options).catch(err => {{
        console.warn("[Offline Demo] Fetch failed (server not running):", urlStr);
        return {{ ok: false, status: 0, json: () => Promise.resolve({{}}), text: () => Promise.resolve("") }};
    }});
}};
</script>'''


# ═══════════════════════════════════════════════════════
# 1. ALERTS PAGE (simplest)
# ═══════════════════════════════════════════════════════
def generate_alerts():
    with open(os.path.join(TEMPLATES, "alerts_v2.html"), "r", encoding="utf-8") as f:
        html = f.read()

    interceptor = build_interceptor([
        "/api/alerts?limit=50",
        "/api/alerts/stats",
        "/api/alerts/rules",
    ])

    # Insert interceptor right after <body>
    html = html.replace("<body>", "<body>\n" + interceptor)

    # Inline CSS: replace external link
    html = html.replace(
        '<link rel="stylesheet" href="/static/cyberpunk.css">',
        f"<style>\n{CYBERPUNK_CSS}\n</style>"
    )

    # Update nav links for local files
    html = html.replace('href="/"', 'href="index_v2_offline.html"')
    html = html.replace('href="/product/v2?competitor_id=1"', 'href="product_detail_v2_offline.html"')
    html = html.replace('href="/report"', 'href="report_v2_offline.html"')

    out = os.path.join(BASE, "offline", "alerts_v2_offline.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  alerts_v2_offline.html ({len(html)/1024:.0f} KB)")


# ═══════════════════════════════════════════════════════
# 2. INDEX PAGE
# ═══════════════════════════════════════════════════════
def generate_index():
    with open(os.path.join(TEMPLATES, "index_v2.html"), "r", encoding="utf-8") as f:
        html = f.read()

    interceptor = build_interceptor([
        "/api/dashboard/stats",
        "/api/competitors",
        "/api/diff/changes?limit=10",
        "/api/reports?limit=10",
        "/api/v1/reviews/sentiment?competitor_id=",
    ])

    html = html.replace("<body>", "<body>\n" + interceptor)
    html = html.replace(
        '<link rel="stylesheet" href="/static/cyberpunk.css">',
        f"<style>\n{CYBERPUNK_CSS}\n</style>"
    )

    html = html.replace('href="/"', 'href="index_v2_offline.html"')
    html = html.replace('href="/alerts"', 'href="alerts_v2_offline.html"')
    html = html.replace('href="/report"', 'href="report_v2_offline.html"')
    html = html.replace('href="/docs"', 'href="#"')
    html = html.replace('href="/monitoring/dashboard"', 'href="#"')
    html = html.replace("href=\"/product/v2?competitor_id=1\"", 'href="product_detail_v2_offline.html"')

    out = os.path.join(BASE, "offline", "index_v2_offline.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  index_v2_offline.html ({len(html)/1024:.0f} KB)")


# ═══════════════════════════════════════════════════════
# 3. REPORT PAGE
# ═══════════════════════════════════════════════════════
def generate_report():
    with open(os.path.join(TEMPLATES, "report_v2.html"), "r", encoding="utf-8") as f:
        html = f.read()

    interceptor = build_interceptor([
        "/api/report/enhanced",
        "/api/competitors",
        "/api/diff/changes?limit=20",
        "/api/reports?limit=10",
    ])

    html = html.replace("<body>", "<body>\n" + interceptor)
    # Report page has inline styles, no cyberpunk.css link -- but let's check
    # It uses its own styles, not cyberpunk.css. No replacement needed.

    out = os.path.join(BASE, "offline", "report_v2_offline.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  report_v2_offline.html ({len(html)/1024:.0f} KB)")


# ═══════════════════════════════════════════════════════
# 4. PRODUCT DETAIL PAGE (most complex)
# ═══════════════════════════════════════════════════════
def generate_product_detail():
    with open(os.path.join(TEMPLATES, "product_detail_v2.html"), "r", encoding="utf-8") as f:
        html = f.read()

    # Inline the JS file
    with open(os.path.join(STATIC, "product_detail_v2.js"), "r", encoding="utf-8") as f:
        js_content = f.read()

    interceptor = build_interceptor([
        "/api/competitors/matrix",
        "/api/competitors/posture",
        "/api/competitors",
        "/api/v1/prices/history?competitor_id=",
        "/api/v1/reviews?competitor_id=",
        "/api/v1/reviews/sentiment?competitor_id=",
        "/api/reviews/sentiment-trend?competitor_id=",
        "/api/diff/changes?limit=50",
        "/api/reports?competitor_id=",
        "/api/product/",
    ])

    html = html.replace("<body>", "<body>\n" + interceptor)

    # Replace external JS reference with inline
    html = html.replace(
        '<script src="/static/product_detail_v2.js"></script>',
        f"<script>\n{js_content}\n</script>"
    )

    # Inline CSS if used (product detail page also uses cyberpunk.css via template)
    if '<link rel="stylesheet" href="/static/cyberpunk.css">' in html:
        html = html.replace(
            '<link rel="stylesheet" href="/static/cyberpunk.css">',
            f"<style>\n{CYBERPUNK_CSS}\n</style>"
        )

    html = html.replace('href="/"', 'href="index_v2_offline.html"')
    html = html.replace('href="/alerts"', 'href="alerts_v2_offline.html"')
    html = html.replace('href="/report"', 'href="report_v2_offline.html"')
    html = html.replace('href="/monitoring/dashboard"', 'href="#"')

    out = os.path.join(BASE, "offline", "product_detail_v2_offline.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  product_detail_v2_offline.html ({len(html)/1024:.0f} KB)")


if __name__ == "__main__":
    print("Generating offline HTML files...")
    generate_alerts()
    generate_index()
    generate_report()
    generate_product_detail()
    print("\nDone! Files in offline/ directory:")
    for f in os.listdir(os.path.join(BASE, "offline")):
        size = os.path.getsize(os.path.join(BASE, "offline", f))
        print(f"  {f} ({size/1024:.0f} KB)")
