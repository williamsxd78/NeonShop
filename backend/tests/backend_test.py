"""End-to-end API tests for NeonKeys Market."""
import os
import asyncio
import secrets
import pytest
import requests

def _load_backend_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if v:
        return v.rstrip("/")
    try:
        with open("/app/frontend/.env") as fh:
            for line in fh:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().rstrip("/")
    except Exception:
        pass
    raise RuntimeError("REACT_APP_BACKEND_URL not set")


BASE_URL = _load_backend_url()
API = f"{BASE_URL}/api"

ADMIN = ("admin@market.com", "Admin@123")
BUYER = ("buyer@market.com", "Buyer@123")
VENDOR = ("vendor@market.com", "Vendor@123")


def _solve_captcha():
    r = requests.get(f"{API}/auth/captcha", timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    q = d["question"].replace("= ?", "").strip()
    # ops: +, -, ×
    for op, sym in [("+", "+"), ("-", "-"), ("×", "*")]:
        if op in q:
            a, b = q.split(op)
            ans = eval(f"{a.strip()}{sym}{b.strip()}")
            break
    return {"captcha_id": d["captcha_id"], "captcha_answer": str(ans)}


def _login(email, password):
    body = {"email": email, "password": password, **_solve_captcha()}
    r = requests.post(f"{API}/auth/login", json=body, timeout=30)
    assert r.status_code == 200, f"login failed {email}: {r.status_code} {r.text}"
    return r.json()["token"]


def _register(email, password, name, role="buyer", **extra):
    body = {"email": email, "password": password, "name": name, "role": role, **extra, **_solve_captcha()}
    return requests.post(f"{API}/auth/register", json=body, timeout=30)


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="session")
def admin_token():
    return _login(*ADMIN)


@pytest.fixture(scope="session")
def buyer_token():
    return _login(*BUYER)


@pytest.fixture(scope="session")
def vendor_token():
    return _login(*VENDOR)


# ---------- Auth ----------
class TestAuth:
    def test_login_wrong_password(self):
        body = {"email": BUYER[0], "password": "wrongpass", **_solve_captcha()}
        r = requests.post(f"{API}/auth/login", json=body)
        assert r.status_code in (401, 429)

    def test_login_missing_captcha_422(self):
        r = requests.post(f"{API}/auth/login", json={"email": BUYER[0], "password": BUYER[1]})
        assert r.status_code == 422

    def test_register_missing_captcha_422(self):
        r = requests.post(f"{API}/auth/register", json={
            "email": f"TEST_nocap_{secrets.token_hex(3)}@market.com", "password": "pass123", "name": "N", "role": "buyer"})
        assert r.status_code == 422

    def test_captcha_single_use_reuse_400(self):
        cap = _solve_captcha()
        # first use (wrong email -> 401 but captcha is consumed)
        r1 = requests.post(f"{API}/auth/login", json={"email": "no_such_user_xyz@market.com", "password": "x", **cap})
        # second use with same captcha should fail with 400 (captcha already consumed)
        r2 = requests.post(f"{API}/auth/login", json={"email": BUYER[0], "password": BUYER[1], **cap})
        assert r2.status_code == 400, f"reused captcha should be 400, got {r2.status_code}"

    def test_captcha_wrong_answer(self):
        r = requests.get(f"{API}/auth/captcha").json()
        body = {"email": BUYER[0], "password": BUYER[1],
                "captcha_id": r["captcha_id"], "captcha_answer": "999999"}
        res = requests.post(f"{API}/auth/login", json=body)
        assert res.status_code == 400
        assert "captcha" in res.text.lower()

    def test_register_vendor_pending(self):
        email = f"TEST_vendor_{secrets.token_hex(4)}@market.com"
        r = _register(email, "Vendor@123", "Test V", role="vendor", store_name="T Store")
        assert r.status_code == 200, r.text
        u = r.json()["user"]
        assert u["role"] == "vendor"
        assert u.get("vendor_status") == "pending"

    def test_register_buyer(self):
        email = f"TEST_buyer_{secrets.token_hex(4)}@market.com"
        r = _register(email, "Buyer@123", "Test B", role="buyer")
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "buyer"

    def test_me(self, buyer_token):
        r = requests.get(f"{API}/auth/me", headers=_h(buyer_token))
        assert r.status_code == 200
        assert r.json()["email"] == BUYER[0]


# ---------- Catalog ----------
class TestCatalog:
    def test_products_list(self):
        r = requests.get(f"{API}/products")
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        assert all(p["status"] == "approved" for p in data)

    def test_search(self):
        r = requests.get(f"{API}/products?q=VPN")
        assert r.status_code == 200
        for p in r.json():
            assert "vpn" in (p["title"] + p["description"]).lower() or "vpn" in p.get("vendor_name", "").lower()

    def test_vendor_filter(self):
        vendors = requests.get(f"{API}/vendors").json()
        assert vendors, "no vendors"
        vid = vendors[0]["id"]
        r = requests.get(f"{API}/products?vendor={vid}")
        assert r.status_code == 200
        for p in r.json():
            assert p["vendor_id"] == vid

    def test_category_tabs(self):
        r = requests.get(f"{API}/products?category=Courses")
        assert r.status_code == 200
        for p in r.json():
            assert p["category"] == "Courses"


# ---------- Deposit flow ----------
class TestDeposits:
    def test_full_deposit_flow(self, buyer_token, admin_token):
        # Ensure a BTC address is configured
        s = requests.get(f"{API}/admin/settings", headers=_h(admin_token)).json()
        addrs = dict(s.get("addresses") or {})
        if not addrs.get("BTC") or addrs["BTC"].startswith("REPLACE"):
            addrs["BTC"] = "bc1qtestdepositaddress"
            r = requests.put(f"{API}/admin/settings", headers=_h(admin_token), json={"addresses": addrs})
            assert r.status_code == 200

        # Create deposit
        r = requests.post(f"{API}/wallet/deposits", headers=_h(buyer_token), json={"coin": "BTC", "amount": 25})
        assert r.status_code == 200, r.text
        dep = r.json()
        assert dep["status"] == "awaiting_txid"
        assert dep["reference"].startswith("DEP-")

        # Submit TXID
        txid = f"test_tx_{secrets.token_hex(6)}"
        r = requests.post(f"{API}/wallet/deposits/{dep['id']}/txid", headers=_h(buyer_token), json={"txid": txid})
        assert r.status_code == 200
        assert r.json()["status"] == "pending"

        # Create second deposit, try duplicate txid
        r2 = requests.post(f"{API}/wallet/deposits", headers=_h(buyer_token), json={"coin": "BTC", "amount": 10}).json()
        rdup = requests.post(f"{API}/wallet/deposits/{r2['id']}/txid", headers=_h(buyer_token), json={"txid": txid})
        assert rdup.status_code in (400, 500), f"Expected rejection but got {rdup.status_code}"

        # Approve deposit as admin
        r = requests.post(f"{API}/admin/deposits/{dep['id']}/approve", headers=_h(admin_token), json={})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "approved"

        # Buyer balance credited
        me = requests.get(f"{API}/auth/me", headers=_h(buyer_token)).json()
        assert me["balance_cents"] >= 2500

    def test_usdt_warning(self, buyer_token, admin_token):
        r = requests.get(f"{API}/wallet/coins", headers=_h(buyer_token))
        assert r.status_code == 200
        coins = {c["code"]: c for c in r.json()}
        assert "TRC20" in coins["USDT_TRC20"]["warning"]


# ---------- Purchase ----------
class TestPurchase:
    def test_insufficient_balance(self):
        tok = _login(*BUYER)
        # Zero out via admin? just use a fresh buyer
        email = f"TEST_poor_{secrets.token_hex(4)}@market.com"
        _register(email, "Buyer@123", "Poor")
        poor_tok = _login(email, "Buyer@123")
        prod = requests.get(f"{API}/products").json()[0]
        r = requests.post(f"{API}/orders", headers=_h(poor_tok), json={"product_id": prod["id"]})
        assert r.status_code == 400
        assert "balance" in r.text.lower()

    def test_purchase_delivery(self, buyer_token, admin_token):
        # Credit buyer wallet
        me = requests.get(f"{API}/auth/me", headers=_h(buyer_token)).json()
        r = requests.post(f"{API}/admin/users/{me['id']}/adjust", headers=_h(admin_token),
                          json={"amount": 100, "reason": "TEST_topup"})
        assert r.status_code == 200
        products = requests.get(f"{API}/products").json()
        prod = next(p for p in products if p["stock_count"] > 0 and p["price_cents"] <= 10000)
        pre_bal = requests.get(f"{API}/auth/me", headers=_h(buyer_token)).json()["balance_cents"]
        r = requests.post(f"{API}/orders", headers=_h(buyer_token), json={"product_id": prod["id"]})
        assert r.status_code == 200, r.text
        order = r.json()["order"]
        assert order["license_key"]
        assert order["commission_pct"] == 10.0 or order["commission_pct"] >= 0
        new_bal = r.json()["balance_cents"]
        assert new_bal == pre_bal - prod["price_cents"]

        # Order visible to buyer
        orders = requests.get(f"{API}/orders", headers=_h(buyer_token)).json()
        assert any(o["id"] == order["id"] for o in orders)


# ---------- Concurrency ----------
class TestConcurrency:
    def test_no_oversell(self, admin_token):
        # Register a fresh buyer and fund them
        email = f"TEST_conc_{secrets.token_hex(4)}@market.com"
        reg = _register(email, "Buyer@123", "C").json()
        tok = reg["token"]
        uid = reg["user"]["id"]
        # Pick a product with stock
        products = requests.get(f"{API}/products").json()
        prod = next((p for p in products if p["stock_count"] > 0), None)
        assert prod is not None
        stock_before = prod["stock_count"]
        price = prod["price_cents"]
        # Fund with just enough for 'stock_before' buys
        requests.post(f"{API}/admin/users/{uid}/adjust", headers=_h(admin_token),
                      json={"amount": (price * (stock_before + 3)) / 100, "reason": "TEST_concurrency"})

        async def _fire():
            import httpx
            async with httpx.AsyncClient(timeout=30) as c:
                tasks = [c.post(f"{API}/orders", headers=_h(tok), json={"product_id": prod["id"]}) for _ in range(stock_before + 3)]
                return await asyncio.gather(*tasks, return_exceptions=True)

        results = asyncio.run(_fire())
        ok = [r for r in results if hasattr(r, "status_code") and r.status_code == 200]
        fail = [r for r in results if hasattr(r, "status_code") and r.status_code != 200]
        assert len(ok) <= stock_before, f"Oversold! ok={len(ok)} stock={stock_before}"
        # distinct keys
        keys = {r.json()["order"]["license_key"] for r in ok}
        assert len(keys) == len(ok), "Duplicate keys delivered"
        # Balance not negative
        bal = requests.get(f"{API}/auth/me", headers=_h(tok)).json()["balance_cents"]
        assert bal >= 0


# ---------- Admin commission override ----------
class TestCommission:
    def test_global_commission(self, admin_token):
        s = requests.get(f"{API}/admin/settings", headers=_h(admin_token)).json()
        orig = s["commission_pct"]
        r = requests.put(f"{API}/admin/settings", headers=_h(admin_token), json={"commission_pct": 15.0})
        assert r.status_code == 200
        assert r.json()["commission_pct"] == 15.0
        # Restore
        requests.put(f"{API}/admin/settings", headers=_h(admin_token), json={"commission_pct": orig})

    def test_vendor_commission_override(self, admin_token):
        vendors = requests.get(f"{API}/admin/vendors?status=approved", headers=_h(admin_token)).json()
        assert vendors
        vid = vendors[0]["id"]
        r = requests.put(f"{API}/admin/vendors/{vid}/commission", headers=_h(admin_token), json={"pct": 20})
        assert r.status_code == 200
        # reset
        r2 = requests.put(f"{API}/admin/vendors/{vid}/commission", headers=_h(admin_token), json={"pct": None})
        assert r2.status_code == 200


# ---------- Vendor flows ----------
class TestVendor:
    def test_vendor_create_product_admin_approve_price_override(self, vendor_token, admin_token):
        title = f"TEST_Prod_{secrets.token_hex(4)}"
        r = requests.post(f"{API}/vendor/products", headers=_h(vendor_token), json={
            "title": title, "description": "test", "category": "Templates", "price": 10.0,
        })
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        assert r.json()["status"] == "pending"

        # Add keys with duplicates (in-batch dedup) then re-add to trigger skipped
        suffix = secrets.token_hex(3)
        keys_text = f"KEY-{suffix}-AAA\nKEY-{suffix}-AAA\nKEY-{suffix}-BBB"
        r = requests.post(f"{API}/vendor/products/{pid}/keys", headers=_h(vendor_token), json={"keys": keys_text})
        assert r.status_code == 200
        assert r.json()["added"] == 2
        # Re-submit same keys - should all be skipped as duplicates
        r2 = requests.post(f"{API}/vendor/products/{pid}/keys", headers=_h(vendor_token), json={"keys": f"KEY-{suffix}-AAA"})
        assert r2.json()["added"] == 0 and r2.json()["skipped"] == 1

        # Admin approve with price override
        r = requests.post(f"{API}/admin/products/{pid}/approve", headers=_h(admin_token), json={"price": 15.0})
        assert r.status_code == 200
        # Verify live at new price
        p = requests.get(f"{API}/products/{pid}").json()
        assert p["price_cents"] == 1500

    def test_vendor_withdrawal_flow(self, vendor_token, admin_token):
        stats = requests.get(f"{API}/vendor/stats", headers=_h(vendor_token)).json()
        # Only test if earnings exist, otherwise skip
        if stats["earnings_cents"] < 100:
            pytest.skip("no earnings to withdraw")
        r = requests.post(f"{API}/vendor/withdrawals", headers=_h(vendor_token), json={
            "amount": 1.0, "coin": "BTC", "address": "bc1qvendorpayout"
        })
        assert r.status_code == 200, r.text
        wid = r.json()["id"]
        # Reject -> refund
        r = requests.post(f"{API}/admin/withdrawals/{wid}/reject", headers=_h(admin_token), json={"reason": "TEST"})
        assert r.status_code == 200
        # Create another and pay
        r2 = requests.post(f"{API}/vendor/withdrawals", headers=_h(vendor_token), json={
            "amount": 1.0, "coin": "BTC", "address": "bc1qvendorpayout"
        }).json()
        rp = requests.post(f"{API}/admin/withdrawals/{r2['id']}/pay", headers=_h(admin_token), json={"payout_txid": "txpay"})
        assert rp.status_code == 200


# ---------- Admin user mgmt + suspended login ----------
class TestAdminUsers:
    def test_suspend_user_blocks_login(self, admin_token):
        email = f"TEST_sus_{secrets.token_hex(4)}@market.com"
        reg = _register(email, "Buyer@123", "S").json()
        uid = reg["user"]["id"]
        r = requests.post(f"{API}/admin/users/{uid}/status", headers=_h(admin_token), json={"status": "suspended"})
        assert r.status_code == 200
        rl = requests.post(f"{API}/auth/login", json={"email": email, "password": "Buyer@123", **_solve_captcha()})
        assert rl.status_code == 403

    def test_adjust_credit_debit(self, admin_token):
        email = f"TEST_adj_{secrets.token_hex(4)}@market.com"
        reg = _register(email, "Buyer@123", "A").json()
        uid = reg["user"]["id"]
        r = requests.post(f"{API}/admin/users/{uid}/adjust", headers=_h(admin_token), json={"amount": 50, "reason": "TEST"})
        assert r.status_code == 200
        r = requests.post(f"{API}/admin/users/{uid}/adjust", headers=_h(admin_token), json={"amount": -20, "reason": "TEST"})
        assert r.status_code == 200


# ---------- Admin stats + audit ----------
class TestAdminMisc:
    def test_stats(self, admin_token):
        r = requests.get(f"{API}/admin/stats", headers=_h(admin_token))
        assert r.status_code == 200
        d = r.json()
        for k in ("users", "vendors", "products_live", "orders", "pending"):
            assert k in d

    def test_audit_log(self, admin_token):
        r = requests.get(f"{API}/admin/audit", headers=_h(admin_token))
        assert r.status_code == 200
        logs = r.json()
        assert len(logs) >= 1

    def test_addresses_update(self, admin_token):
        r = requests.put(f"{API}/admin/settings", headers=_h(admin_token),
                         json={"addresses": {"ETH": "0xTEST_eth_addr", "BTC": "bc1qtestdepositaddress", "USDT_TRC20": "TTEST_trc20", "LTC": "LTEST_ltc"}})
        assert r.status_code == 200
        assert r.json()["addresses"]["ETH"] == "0xTEST_eth_addr"



# ---------- New features: tags, default image, content delivery, security ----------
class TestNewFeatures:
    def test_product_default_image_when_omitted(self, vendor_token, admin_token):
        title = f"TEST_DefImg_{secrets.token_hex(3)}"
        r = requests.post(f"{API}/vendor/products", headers=_h(vendor_token), json={
            "title": title, "description": "x", "category": "Templates", "price": 5.0,
            "tags": ["Alpha", "beta", "Alpha", "  gamma  "],
        })
        assert r.status_code == 200, r.text
        p = r.json()
        assert p["image"], "default image should be assigned when image is omitted"
        # tags normalized (lowercase, trim, dedupe)
        assert "alpha" in p["tags"] and "beta" in p["tags"] and "gamma" in p["tags"]
        assert len([t for t in p["tags"] if t == "alpha"]) == 1

    def test_tags_capped_to_8(self, vendor_token):
        tags = [f"t{i}" for i in range(12)]
        r = requests.post(f"{API}/vendor/products", headers=_h(vendor_token), json={
            "title": f"TEST_TagCap_{secrets.token_hex(3)}", "description": "x",
            "category": "Templates", "price": 5.0, "tags": tags,
        })
        # Pydantic enforces max_length=8 -> 422; this is acceptable server-side validation
        assert r.status_code in (200, 422)
        if r.status_code == 200:
            assert len(r.json()["tags"]) <= 8

    def test_content_product_requires_delivery(self, vendor_token):
        r = requests.post(f"{API}/vendor/products", headers=_h(vendor_token), json={
            "title": f"TEST_ContentEmpty_{secrets.token_hex(3)}", "description": "x",
            "category": "Digital Assets", "price": 3.0,
            "delivery_type": "content", "delivery_content": "   ",
        })
        assert r.status_code == 400
        assert "delivery" in r.text.lower()

    def test_content_product_full_flow(self, vendor_token, admin_token):
        secret = f"SECRET-CONTENT-{secrets.token_hex(6)}"
        title = f"TEST_Content_{secrets.token_hex(3)}"
        r = requests.post(f"{API}/vendor/products", headers=_h(vendor_token), json={
            "title": title, "description": "buyer sees this", "category": "Digital Assets",
            "price": 2.0, "tags": ["ebook", "pdf"],
            "delivery_type": "content", "delivery_content": secret,
        })
        assert r.status_code == 200, r.text
        pid = r.json()["id"]
        # Admin approve
        r = requests.post(f"{API}/admin/products/{pid}/approve", headers=_h(admin_token), json={})
        assert r.status_code == 200

        # Public listing should NOT include delivery_content
        public = requests.get(f"{API}/products/{pid}").json()
        assert "delivery_content" not in public, "SECURITY: public endpoint leaking delivery_content"
        public_list = requests.get(f"{API}/products").json()
        for p in public_list:
            assert "delivery_content" not in p

        # Register & fund buyer
        bemail = f"TEST_cbuyer_{secrets.token_hex(3)}@market.com"
        reg = _register(bemail, "Buyer@123", "CB").json()
        uid, btok = reg["user"]["id"], reg["token"]
        requests.post(f"{API}/admin/users/{uid}/adjust", headers=_h(admin_token),
                      json={"amount": 10, "reason": "TEST_content"})

        # First purchase
        r = requests.post(f"{API}/orders", headers=_h(btok), json={"product_id": pid})
        assert r.status_code == 200, r.text
        order = r.json()["order"]
        assert order["delivery_type"] == "content"
        assert order["delivery_content"] == secret
        assert order.get("license_key") is None

        # Unlimited stock -> buy again works
        r2 = requests.post(f"{API}/orders", headers=_h(btok), json={"product_id": pid})
        assert r2.status_code == 200, r2.text
        assert r2.json()["order"]["delivery_content"] == secret
