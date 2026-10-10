"""Iteration 10 — regression tests for admin site builder (brand/theme/footer/sections)."""
import os
import re
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://wallet-goods.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN = ("admin@market.com", "Admin@123")

DEFAULT_THEME = {"brand": "#22C55E", "brandlt": "#4ADE80", "info": "#22D3EE", "ink": "#0A0B0B",
                 "panel": "#171A19", "surface": "#121413", "deep": "#0E100F", "line": "#272B29"}
DEFAULT_BRAND = {"name_start": "Neon", "name_end": "Keys", "icon": "zap",
                 "page_title": "NeonKeys Market", "official_store": "NeonKeys Official"}
DEFAULT_FOOTER = {"text": "© 2026 NeonKeys · Verified vendors · Instant delivery", "columns": [
    {"title": "Marketplace", "links": [{"label": "Shop", "url": "/"}, {"label": "Vendors", "url": "/vendors"},
                                       {"label": "Become a vendor", "url": "/vendor/register"}]},
    {"title": "Account", "links": [{"label": "Wallet", "url": "/wallet"}, {"label": "Key vault", "url": "/vault"},
                                   {"label": "Orders", "url": "/orders"}]},
    {"title": "Help", "links": [{"label": "Support", "url": "/support"}, {"label": "Notifications", "url": "/notifications"}]}]}
DEFAULT_SECTIONS = [{"id": t, "type": t, "enabled": True} for t in ["hero", "banners", "notice", "vendors", "products"]]


def _captcha_answer(q):
    m = re.match(r"\s*(\d+)\s*([+\-×])\s*(\d+)", q)
    a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
    return str(a + b if op == "+" else a - b if op == "-" else a * b)


@pytest.fixture(scope="module")
def admin_token():
    s = requests.Session()
    cap = s.get(f"{API}/auth/captcha").json()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN[0], "password": ADMIN[1],
                                           "captcha_id": cap["captcha_id"],
                                           "captcha_answer": _captcha_answer(cap["question"])})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_hdr(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module", autouse=True)
def _restore(admin_hdr):
    yield
    # Restore defaults after module tests
    requests.put(f"{API}/admin/site", headers=admin_hdr,
                 json={"theme": DEFAULT_THEME, "brand": DEFAULT_BRAND,
                       "footer": DEFAULT_FOOTER, "sections": DEFAULT_SECTIONS})


def test_public_site_exposes_theme_brand_footer_sections():
    r = requests.get(f"{API}/site")
    assert r.status_code == 200
    d = r.json()
    for k in ("theme", "brand", "footer", "sections"):
        assert k in d, f"/api/site missing {k}"
    assert d["brand"]["name_start"] == "Neon"
    assert d["brand"]["name_end"] == "Keys"
    assert re.fullmatch(r"#[0-9A-Fa-f]{6}", d["theme"]["brand"])
    # Only enabled sections should be exposed publicly
    for s in d["sections"]:
        assert s["enabled"] is True


def test_admin_site_returns_all_sections_incl_disabled(admin_hdr):
    r = requests.get(f"{API}/admin/site", headers=admin_hdr)
    assert r.status_code == 200
    d = r.json()
    for k in ("theme", "brand", "footer", "sections"):
        assert k in d
    types = {s["type"] for s in d["sections"]}
    assert {"hero", "banners", "notice", "vendors", "products"}.issubset(types)


def test_update_brand_persists_and_shows_in_public_site(admin_hdr):
    new_brand = {"name_start": "TEST", "name_end": "Lab", "icon": "shield",
                 "page_title": "TEST Lab", "official_store": "TEST Lab Official"}
    r = requests.put(f"{API}/admin/site", headers=admin_hdr, json={"brand": new_brand})
    assert r.status_code == 200, r.text
    pub = requests.get(f"{API}/site").json()
    assert pub["brand"]["name_start"] == "TEST"
    assert pub["brand"]["page_title"] == "TEST Lab"
    assert pub["brand"]["icon"] == "shield"
    # restore
    requests.put(f"{API}/admin/site", headers=admin_hdr, json={"brand": DEFAULT_BRAND})
    assert requests.get(f"{API}/site").json()["brand"]["name_start"] == "Neon"


def test_theme_invalid_hex_rejected(admin_hdr):
    bad = {**DEFAULT_THEME, "brand": "not-a-hex"}
    r = requests.put(f"{API}/admin/site", headers=admin_hdr, json={"theme": bad})
    assert r.status_code == 422


def test_theme_update_persists(admin_hdr):
    new_theme = {"brand": "#3B82F6", "brandlt": "#60A5FA", "info": "#A78BFA", "ink": "#090B10",
                 "panel": "#151922", "surface": "#11141B", "deep": "#0D1016", "line": "#252B38"}
    r = requests.put(f"{API}/admin/site", headers=admin_hdr, json={"theme": new_theme})
    assert r.status_code == 200
    pub = requests.get(f"{API}/site").json()
    assert pub["theme"]["brand"].upper() == "#3B82F6"
    requests.put(f"{API}/admin/site", headers=admin_hdr, json={"theme": DEFAULT_THEME})


def test_footer_rejects_javascript_url(admin_hdr):
    bad = {"text": "x", "columns": [{"title": "T", "links": [{"label": "Evil", "url": "javascript:alert(1)"}]}]}
    r = requests.put(f"{API}/admin/site", headers=admin_hdr, json={"footer": bad})
    assert r.status_code == 422


def test_footer_update_persists(admin_hdr):
    new_footer = {"text": "TEST footer line", "columns": [
        {"title": "TEST", "links": [{"label": "Shop", "url": "/"}, {"label": "Ext", "url": "https://example.com"}]}]}
    r = requests.put(f"{API}/admin/site", headers=admin_hdr, json={"footer": new_footer})
    assert r.status_code == 200
    pub = requests.get(f"{API}/site").json()
    assert pub["footer"]["text"] == "TEST footer line"
    assert pub["footer"]["columns"][0]["title"] == "TEST"
    requests.put(f"{API}/admin/site", headers=admin_hdr, json={"footer": DEFAULT_FOOTER})


def test_sections_builtins_deduped_and_missing_appended_disabled(admin_hdr):
    # Only send 2 builtins; others must be appended disabled, duplicates removed
    payload = [{"id": "hero", "type": "hero", "enabled": True},
               {"id": "hero", "type": "hero", "enabled": False},  # dup
               {"id": "products", "type": "products", "enabled": False}]
    r = requests.put(f"{API}/admin/site", headers=admin_hdr, json={"sections": payload})
    assert r.status_code == 200, r.text
    secs = r.json()["sections"]
    types = [s["type"] for s in secs]
    # all 5 built-ins present, exactly once
    for t in ["hero", "banners", "notice", "vendors", "products"]:
        assert types.count(t) == 1
    # hero enabled from first entry, products disabled, others appended disabled
    by = {s["type"]: s for s in secs}
    assert by["hero"]["enabled"] is True
    assert by["products"]["enabled"] is False
    assert by["banners"]["enabled"] is False
    # restore
    requests.put(f"{API}/admin/site", headers=admin_hdr, json={"sections": DEFAULT_SECTIONS})


def test_custom_section_add_and_public_only_shows_enabled(admin_hdr):
    custom_text = {"id": None, "type": "text", "enabled": True, "title": "TEST hello",
                   "body": "hi", "image": "", "button_text": "", "link": "", "columns": []}
    custom_cols = {"id": None, "type": "columns", "enabled": False, "title": "TEST hidden cols",
                   "body": "", "image": "", "button_text": "", "link": "",
                   "columns": [{"icon": "zap", "title": "A", "text": "1"}]}
    payload = DEFAULT_SECTIONS + [custom_text, custom_cols]
    r = requests.put(f"{API}/admin/site", headers=admin_hdr, json={"sections": payload})
    assert r.status_code == 200
    secs = r.json()["sections"]
    # custom text section got an id
    text_sec = next(s for s in secs if s["type"] == "text")
    assert text_sec["id"] and text_sec["id"] not in ["hero", "banners", "notice", "vendors", "products"]
    pub = requests.get(f"{API}/site").json()["sections"]
    pub_titles = [s.get("title") for s in pub]
    assert "TEST hello" in pub_titles
    assert "TEST hidden cols" not in pub_titles
    # restore
    requests.put(f"{API}/admin/site", headers=admin_hdr, json={"sections": DEFAULT_SECTIONS})


def test_non_admin_cannot_update_site():
    r = requests.put(f"{API}/admin/site", json={"brand": DEFAULT_BRAND})
    assert r.status_code == 401
