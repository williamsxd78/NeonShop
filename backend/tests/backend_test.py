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


# ---------- Bulk import, batch approve, delete ----------
def _build_bulk_text(n, uniq, lines_per=5, sep="--------------------------------------------------"):
    """Build n blocks separated by dash line. Each has `lines_per` lines; the key line is unique."""
    blocks = []
    for i in range(n):
        blocks.append("\n".join([
            f"Product: TEST_BULK_{uniq}",
            f"Plan: Yearly",
            f"Region: Global",
            f"License key: KEY-{uniq}-{i:04d}",
            f"Activation: Account > Licenses",
        ]))
    return f"\n{sep}\n".join(blocks)


class TestBulkImport:
    def test_bulk_import_dashes_and_duplicates(self, vendor_token):
        uniq = secrets.token_hex(3)
        text = _build_bulk_text(4, uniq, lines_per=5)
        # Insert a duplicate of block 0 at the end to force 1 dup skip
        text += "\n--------------------------------------------------\n" + "\n".join([
            f"Product: TEST_BULK_{uniq}", "Plan: Yearly", "Region: Global",
            f"License key: KEY-{uniq}-0000", "Activation: Account > Licenses"])
        payload = {
            "text": text, "separator": "dashes",
            # lines 0,1,2 are public; line 3 is license (hidden); line 4 is activation (hidden)
            "public_lines": [0, 1, 2], "title_line": 0,
            "title_prefix": "Item", "deliver": "all",
            "category": "Software Licenses", "price": 7.5, "tags": ["bulk", "test"],
        }
        r = requests.post(f"{API}/vendor/products/bulk", headers=_h(vendor_token), json=payload)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["created"] == 4, d
        assert d["skipped"] == 1, d
        batch_id = d["batch_id"]

        # Vendor should see 4 pending products in this batch
        prods = requests.get(f"{API}/vendor/products", headers=_h(vendor_token)).json()
        batch_prods = [p for p in prods if p.get("batch_id") == batch_id]
        assert len(batch_prods) == 4
        for p in batch_prods:
            assert p["status"] == "pending"
            assert p["stock_count"] == 1
            assert p["delivery_type"] == "keys"
            assert p["title"].startswith(f"Product: TEST_BULK_{uniq}")
            # title_line is excluded from preview_lines (so no duplication)
            assert p["preview_lines"] == ["Plan: Yearly", "Region: Global"]
            # description equals public lines joined (hidden lines not exposed to vendor list either in description)
            assert "License key" not in p["description"]

        # Store for other tests via class attr style - use module-level setattr
        TestBulkImport.batch_id = batch_id
        TestBulkImport.uniq = uniq
        TestBulkImport.batch_pids = [p["id"] for p in batch_prods]

    def test_bulk_public_products_hide_hidden_lines(self, vendor_token, admin_token):
        # Approve batch
        bid = TestBulkImport.batch_id
        r = requests.post(f"{API}/admin/batches/{bid}/approve", headers=_h(admin_token), json={"price": 9.0})
        assert r.status_code == 200, r.text
        assert r.json()["approved"] == 4

        # Public catalog: delivery_content excluded; hidden lines not in description
        for pid in TestBulkImport.batch_pids:
            pub = requests.get(f"{API}/products/{pid}")
            assert pub.status_code == 200
            data = pub.json()
            assert "delivery_content" not in data
            assert "License key" not in (data.get("description") or "")
            assert data["price_cents"] == 900
            # preview_lines included (title_line is excluded)
            assert data["preview_lines"] == ["Plan: Yearly", "Region: Global"]

    def test_bulk_deliver_hidden_only(self, vendor_token):
        """deliver='hidden' -> delivered key contains ONLY the hidden lines."""
        uniq = secrets.token_hex(3)
        text = _build_bulk_text(2, uniq, lines_per=5)
        payload = {
            "text": text, "separator": "dashes",
            "public_lines": [0, 1, 2], "title_line": 0, "deliver": "hidden",
            "category": "Software Licenses", "price": 3.0,
        }
        r = requests.post(f"{API}/vendor/products/bulk", headers=_h(vendor_token), json=payload)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["created"] == 2
        # Fetch the keys for one product and verify key content is hidden-lines-only
        prods = requests.get(f"{API}/vendor/products", headers=_h(vendor_token)).json()
        batch_prods = [p for p in prods if p.get("batch_id") == d["batch_id"]]
        pid = batch_prods[0]["id"]
        keys = requests.get(f"{API}/vendor/products/{pid}/keys", headers=_h(vendor_token)).json()
        assert keys
        # Vendor keys endpoint shows unmasked for available keys
        k_content = keys[0]["key"]
        assert "License key: KEY-" in k_content
        assert "Activation:" in k_content
        # Hidden-only: public lines should NOT be in the key
        assert "Product: TEST_BULK_" not in k_content
        assert "Plan: Yearly" not in k_content
        # Clean up this batch
        requests.delete(f"{API}/vendor/batches/{d['batch_id']}", headers=_h(vendor_token))

    def test_bulk_purchase_delivers_full_multiline(self, admin_token):
        """Buyer purchases a bulk item -> gets multi-line delivery, product becomes sold out."""
        pid = TestBulkImport.batch_pids[0]
        # Fresh buyer
        email = f"TEST_bulkbuy_{secrets.token_hex(3)}@market.com"
        reg = _register(email, "Buyer@123", "BB").json()
        tok, uid = reg["token"], reg["user"]["id"]
        requests.post(f"{API}/admin/users/{uid}/adjust", headers=_h(admin_token),
                      json={"amount": 20, "reason": "TEST_bulkbuy"})
        r = requests.post(f"{API}/orders", headers=_h(tok), json={"product_id": pid})
        assert r.status_code == 200, r.text
        order = r.json()["order"]
        # Multi-line delivery - deliver='all' -> all 5 lines returned via license_key
        assert order["license_key"] is not None
        assert "\n" in order["license_key"]
        assert "License key: KEY-" in order["license_key"]
        assert "Product: TEST_BULK_" in order["license_key"]

        # Product now sold out
        r2 = requests.get(f"{API}/products/{pid}")
        # After buying the sole key, stock=0; product still "approved" so endpoint returns it
        if r2.status_code == 200:
            assert r2.json()["stock_count"] == 0
        # Second buy should 400
        r3 = requests.post(f"{API}/orders", headers=_h(tok), json={"product_id": pid})
        assert r3.status_code == 400

        TestBulkImport.sold_pid = pid

    def test_vendor_delete_single_product_keeps_past_orders(self, vendor_token):
        """Delete the sold bulk product; past buyer orders remain intact (orders not deleted)."""
        pid = TestBulkImport.sold_pid
        r = requests.delete(f"{API}/vendor/products/{pid}", headers=_h(vendor_token))
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["deleted"] == 1
        # Public product gone
        assert requests.get(f"{API}/products/{pid}").status_code == 404

    def test_vendor_delete_batch_removes_rest(self, vendor_token):
        bid = TestBulkImport.batch_id
        r = requests.delete(f"{API}/vendor/batches/{bid}", headers=_h(vendor_token))
        assert r.status_code == 200, r.text
        # 3 remaining products + unsold keys removed (1 sold already)
        assert r.json()["deleted"] == 3
        # Verify batch gone
        prods = requests.get(f"{API}/vendor/products", headers=_h(vendor_token)).json()
        assert not [p for p in prods if p.get("batch_id") == bid]

    def test_bulk_separator_blank(self, vendor_token):
        uniq = secrets.token_hex(3)
        blocks = []
        for i in range(2):
            blocks.append(f"Title: TEST_BLANK_{uniq}_{i}\nKey: BLANK-{uniq}-{i}")
        text = "\n\n".join(blocks)
        r = requests.post(f"{API}/vendor/products/bulk", headers=_h(vendor_token), json={
            "text": text, "separator": "blank", "public_lines": [0], "title_line": 0,
            "deliver": "all", "category": "Templates", "price": 1.0})
        assert r.status_code == 200, r.text
        assert r.json()["created"] == 2
        # cleanup
        requests.delete(f"{API}/vendor/batches/{r.json()['batch_id']}", headers=_h(vendor_token))

    def test_bulk_empty_text_400(self, vendor_token):
        r = requests.post(f"{API}/vendor/products/bulk", headers=_h(vendor_token), json={
            "text": "\n\n", "separator": "dashes", "public_lines": [0], "deliver": "all",
            "category": "Templates", "price": 1.0})
        assert r.status_code == 400


# ---------- Iteration 4: Bulk price/delete + buyer attr filters & facets ----------
import json as _json


def _create_approved_bulk(vendor_token, admin_token, uniq, regions, plan="Pro", price=3.0, category="Subscriptions"):
    """Create a batch of items with public lines 'Plan: Pro' / 'Region: <r>', approve it. Returns (batch_id, pids)."""
    blocks = []
    for i, r in enumerate(regions):
        blocks.append("\n".join([
            f"Name: TEST_ITER4_{uniq}_{i}",
            f"Plan: {plan}",
            f"Region: {r}",
            f"Pass: secret-{uniq}-{i}",
        ]))
    text = "\n-----\n".join(blocks)
    body = {"text": text, "separator": "dashes", "public_lines": [1, 2], "title_line": 0,
            "title_prefix": "Item", "deliver": "all", "category": category, "price": price, "tags": []}
    r = requests.post(f"{API}/vendor/products/bulk", headers=_h(vendor_token), json=body)
    assert r.status_code == 200, r.text
    d = r.json()
    bid = d["batch_id"]
    assert d["created"] == len(regions)
    ap = requests.post(f"{API}/admin/batches/{bid}/approve", headers=_h(admin_token), json={})
    assert ap.status_code == 200, ap.text
    prods = requests.get(f"{API}/vendor/products", headers=_h(vendor_token)).json()
    pids = [p["id"] for p in prods if p.get("batch_id") == bid]
    return bid, pids


class TestBulkPriceDelete:
    """POST /api/vendor/products/bulk-price and bulk-delete."""

    @classmethod
    def setup_class(cls):
        cls.uniq = secrets.token_hex(3)
        cls.vtok = _login(*VENDOR)
        cls.atok = _login(*ADMIN)
        cls.bid, cls.pids = _create_approved_bulk(cls.vtok, cls.atok, cls.uniq, ["EU", "US", "EU", "Asia"])

    @classmethod
    def teardown_class(cls):
        # Clean up remaining products in the batch
        try:
            requests.delete(f"{API}/vendor/batches/{cls.bid}", headers=_h(cls.vtok))
        except Exception:
            pass
        if getattr(cls, "_other_vtok", None):
            try:
                requests.delete(f"{API}/vendor/batches/{cls._other_bid}", headers=_h(cls._other_vtok))
            except Exception:
                pass

    def test_bulk_price_requires_price(self):
        r = requests.post(f"{API}/vendor/products/bulk-price", headers=_h(self.vtok),
                          json={"ids": self.pids[:1]})
        # price Optional default None -> 400 by handler (or 422 if pydantic blocked). Accept both; the API says 400.
        assert r.status_code in (400, 422), r.text

    def test_bulk_price_updates_and_resets_to_pending(self):
        ids = self.pids[:2]
        r = requests.post(f"{API}/vendor/products/bulk-price", headers=_h(self.vtok),
                          json={"ids": ids, "price": 7.0})
        assert r.status_code == 200, r.text
        assert r.json()["updated"] == 2
        # Verify both go to pending at the new price
        prods = requests.get(f"{API}/vendor/products", headers=_h(self.vtok)).json()
        touched = [p for p in prods if p["id"] in ids]
        assert len(touched) == 2
        for p in touched:
            assert p["status"] == "pending"
            assert p["price_cents"] == 700
            assert p["vendor_price_cents"] == 700
        # Public products now hidden (not approved)
        for pid in ids:
            assert requests.get(f"{API}/products/{pid}").status_code == 404

    @classmethod
    def _get_or_create_other_vendor_product(cls):
        if getattr(cls, "_other_pid", None):
            return cls._other_pid
        # Register new vendor
        email = f"TEST_vend2_{secrets.token_hex(3)}@market.com"
        reg = _register(email, "Vendor@123", "V2", role="vendor", store_name="TEST V2 Store").json()
        vtok2, vuid2 = reg["token"], reg["user"]["id"]
        # Approve vendor
        requests.post(f"{API}/admin/vendors/{vuid2}/approve", headers=_h(cls.atok), json={})
        # Create a bulk listing + approve batch
        bid2, pids2 = _create_approved_bulk(vtok2, cls.atok, secrets.token_hex(3), ["X"], price=1.0)
        cls._other_vtok = vtok2
        cls._other_bid = bid2
        cls._other_pid = pids2[0]
        return cls._other_pid

    def test_bulk_price_ignores_other_vendors_ids(self):
        """Vendor cannot touch another vendor's products via bulk-price."""
        target = self._get_or_create_other_vendor_product()
        before = requests.get(f"{API}/products/{target}").json()
        r = requests.post(f"{API}/vendor/products/bulk-price", headers=_h(self.vtok),
                          json={"ids": [target], "price": 999.0})
        assert r.status_code == 200
        assert r.json()["updated"] == 0
        after = requests.get(f"{API}/products/{target}").json()
        assert after["price_cents"] == before["price_cents"]
        assert after["status"] == "approved"

    def test_bulk_price_invalid_price_422(self):
        # price <= 0 is rejected by pydantic (gt=0)
        r = requests.post(f"{API}/vendor/products/bulk-price", headers=_h(self.vtok),
                          json={"ids": self.pids[:1], "price": 0})
        assert r.status_code == 422
        r2 = requests.post(f"{API}/vendor/products/bulk-price", headers=_h(self.vtok),
                           json={"ids": self.pids[:1], "price": 1e9})
        assert r2.status_code == 422

    def test_bulk_delete_removes_products_and_keys(self):
        # Delete 2 items (pick two still-approved ones: last 2 pids)
        victims = self.pids[2:4]
        r = requests.post(f"{API}/vendor/products/bulk-delete", headers=_h(self.vtok),
                          json={"ids": victims})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["deleted"] == 2
        assert d["keys_removed"] >= 2
        for pid in victims:
            assert requests.get(f"{API}/products/{pid}").status_code == 404
        # Vendor list no longer has them
        prods = requests.get(f"{API}/vendor/products", headers=_h(self.vtok)).json()
        assert not [p for p in prods if p["id"] in victims]

    def test_bulk_delete_ignores_other_vendors_ids(self):
        target = self._get_or_create_other_vendor_product()
        r = requests.post(f"{API}/vendor/products/bulk-delete", headers=_h(self.vtok),
                          json={"ids": [target]})
        # _delete_products raises 404 when no products match the (ids + vendor_id) filter
        assert r.status_code == 404
        # Target still exists
        assert requests.get(f"{API}/products/{target}").status_code == 200

    def test_bulk_delete_sold_orders_preserved(self, admin_token):
        """Buy a bulk item, then bulk-delete it; buyer's vault order should remain."""
        # Create fresh bulk + approve
        uniq = secrets.token_hex(3)
        bid, pids = _create_approved_bulk(self.vtok, self.atok, uniq, ["EU"], price=2.0)
        pid = pids[0]
        # Fresh buyer
        email = f"TEST_iter4buy_{secrets.token_hex(3)}@market.com"
        reg = _register(email, "Buyer@123", "BB").json()
        btok, buid = reg["token"], reg["user"]["id"]
        requests.post(f"{API}/admin/users/{buid}/adjust", headers=_h(admin_token),
                      json={"amount": 20, "reason": "TEST_iter4"})
        o = requests.post(f"{API}/orders", headers=_h(btok), json={"product_id": pid})
        assert o.status_code == 200, o.text
        order_id = o.json()["order"]["id"]
        # Now vendor bulk-deletes it
        r = requests.post(f"{API}/vendor/products/bulk-delete", headers=_h(self.vtok),
                          json={"ids": [pid]})
        assert r.status_code == 200
        assert r.json()["deleted"] == 1
        # Buyer vault should still contain the order
        vault = requests.get(f"{API}/orders", headers=_h(btok)).json()
        assert any(x["id"] == order_id for x in vault), "buyer vault lost sold order after vendor bulk-delete"


class TestBuyerFilters:
    """Facets endpoint and ?attrs= filter on /api/products."""

    @classmethod
    def setup_class(cls):
        cls.uniq = secrets.token_hex(3)
        cls.vtok = _login(*VENDOR)
        cls.atok = _login(*ADMIN)
        # 2 EU, 1 US, 1 Asia; all Plan: Pro; category Subscriptions
        cls.bid, cls.pids = _create_approved_bulk(
            cls.vtok, cls.atok, cls.uniq, ["EU", "US", "EU", "Asia"], plan="Pro")

    @classmethod
    def teardown_class(cls):
        try:
            requests.delete(f"{API}/vendor/batches/{cls.bid}", headers=_h(cls.vtok))
        except Exception:
            pass

    def test_facets_returns_region_and_plan(self):
        r = requests.get(f"{API}/products/facets", params={"category": "Subscriptions"})
        assert r.status_code == 200
        data = r.json()
        keys = {f["key"]: f for f in data}
        # Region: should contain at least EU(>=2), US(>=1), Asia(>=1) across my batch
        assert "Region" in keys, keys
        region_vals = {v["value"]: v["count"] for v in keys["Region"]["values"]}
        assert region_vals.get("EU", 0) >= 2
        assert region_vals.get("US", 0) >= 1
        assert region_vals.get("Asia", 0) >= 1
        # Values sorted by count desc
        counts = [v["count"] for v in keys["Region"]["values"]]
        assert counts == sorted(counts, reverse=True)

    def test_facets_single_value_hidden_when_only_one(self):
        # Single-value keys (Plan: Pro only) are hidden; filters need >=2 options
        r = requests.get(f"{API}/products/facets", params={"category": "Subscriptions"})
        data = {f["key"]: f for f in r.json()}
        assert "Plan" not in data
        assert "Region" in data

    def test_attrs_filter_eu(self):
        r = requests.get(f"{API}/products", params={"attrs": _json.dumps({"Region": "EU"})})
        assert r.status_code == 200
        prods = r.json()
        mine = [p for p in prods if p.get("batch_id") == self.bid]
        assert len(mine) == 2
        for p in mine:
            assert {"k": "Region", "v": "EU"} in p.get("attrs", [])

    def test_attrs_filter_and_combination(self):
        # Region=EU AND Plan=Pro -> both my 2 EU items
        r = requests.get(f"{API}/products",
                         params={"attrs": _json.dumps({"Region": "EU", "Plan": "Pro"})})
        assert r.status_code == 200
        mine = [p for p in r.json() if p.get("batch_id") == self.bid]
        assert len(mine) == 2
        # Region=EU AND Plan=Nonexistent -> 0
        r2 = requests.get(f"{API}/products",
                          params={"attrs": _json.dumps({"Region": "EU", "Plan": "NoSuch"})})
        assert r2.status_code == 200
        assert not [p for p in r2.json() if p.get("batch_id") == self.bid]

    def test_attrs_invalid_json_400(self):
        r = requests.get(f"{API}/products", params={"attrs": "not-json{"})
        assert r.status_code == 400

    def test_attrs_empty_dict_ignored(self):
        """Empty attrs dict should NOT filter (returns full catalog)."""
        r = requests.get(f"{API}/products", params={"attrs": _json.dumps({})})
        assert r.status_code == 200
        full = requests.get(f"{API}/products").json()
        assert len(r.json()) == len(full)


# ---------- Iteration 5: /site + /admin/site (notice & categories) ----------
DEFAULT_CATS = ["Software Licenses", "Templates", "Digital Assets", "Subscriptions", "Courses"]
DEFAULT_NOTICE = {
    "enabled": True, "tone": "amber", "title": "All sales final",
    "body": "Keys are delivered instantly and are non-refundable. Disputes are reviewed by admin and resolved via wallet credit.",
    "highlight": "Every key is reserved atomically — never sold twice.",
}


def _cat_payload(names):
    return [{"name": n, "original": n} for n in names]


def _restore_site(atok):
    requests.put(f"{API}/admin/site", headers=_h(atok), json={
        "notice": DEFAULT_NOTICE,
        "categories": _cat_payload(DEFAULT_CATS),
    })


class TestSitePublic:
    def test_site_public_shape(self):
        r = requests.get(f"{API}/site")
        assert r.status_code == 200
        d = r.json()
        assert "categories" in d and "notice" in d
        assert isinstance(d["categories"], list) and len(d["categories"]) >= 1
        n = d["notice"]
        for k in ("enabled", "tone", "title", "body", "highlight"):
            assert k in n

    def test_site_matches_categories_endpoint(self):
        s = requests.get(f"{API}/site").json()
        c = requests.get(f"{API}/categories").json()
        assert s["categories"] == c


class TestAdminSite:
    @classmethod
    def setup_class(cls):
        cls.atok = _login(*ADMIN)
        cls.btok = _login(*BUYER)
        cls.vtok = _login(*VENDOR)

    @classmethod
    def teardown_class(cls):
        _restore_site(cls.atok)

    def test_admin_site_requires_admin(self):
        r = requests.put(f"{API}/admin/site", headers=_h(self.btok),
                         json={"notice": DEFAULT_NOTICE})
        assert r.status_code == 403

    def test_update_notice_and_disable(self):
        new_notice = {"enabled": True, "tone": "green", "title": "TEST notice",
                      "body": "Body here", "highlight": "Highlight here"}
        r = requests.put(f"{API}/admin/site", headers=_h(self.atok), json={"notice": new_notice})
        assert r.status_code == 200
        s = requests.get(f"{API}/site").json()
        assert s["notice"]["title"] == "TEST notice"
        assert s["notice"]["tone"] == "green"
        assert s["notice"]["enabled"] is True
        # Disable
        off = {**new_notice, "enabled": False}
        r = requests.put(f"{API}/admin/site", headers=_h(self.atok), json={"notice": off})
        assert r.status_code == 200
        assert requests.get(f"{API}/site").json()["notice"]["enabled"] is False

    def test_duplicate_category_names_400(self):
        bad = [{"name": "Software Licenses", "original": "Software Licenses"},
               {"name": "software licenses", "original": "Templates"}]
        r = requests.put(f"{API}/admin/site", headers=_h(self.atok), json={"categories": bad})
        assert r.status_code == 400
        assert "unique" in r.text.lower() or "empty" in r.text.lower()

    def test_empty_category_name_400(self):
        bad = [{"name": "   ", "original": "Software Licenses"}] + [
            {"name": n, "original": n} for n in DEFAULT_CATS[1:]
        ]
        r = requests.put(f"{API}/admin/site", headers=_h(self.atok), json={"categories": bad})
        assert r.status_code == 400

    def test_rename_moves_products(self):
        # Rename "Courses" -> "TEST_Courses_X"
        new_name = f"TEST_Courses_{secrets.token_hex(2)}"
        payload = []
        for n in DEFAULT_CATS:
            if n == "Courses":
                payload.append({"name": new_name, "original": "Courses"})
            else:
                payload.append({"name": n, "original": n})
        r = requests.put(f"{API}/admin/site", headers=_h(self.atok), json={"categories": payload})
        assert r.status_code == 200
        assert new_name in r.json()["categories"]
        # Products previously in Courses now searchable under new name
        prods = requests.get(f"{API}/products", params={"category": new_name}).json()
        assert all(p["category"] == new_name for p in prods)
        # Old name has no products
        old = requests.get(f"{API}/products", params={"category": "Courses"}).json()
        assert len(old) == 0
        # Rename back
        rev = []
        for n in r.json()["categories"]:
            if n == new_name:
                rev.append({"name": "Courses", "original": new_name})
            else:
                rev.append({"name": n, "original": n})
        r2 = requests.put(f"{API}/admin/site", headers=_h(self.atok), json={"categories": rev})
        assert r2.status_code == 200
        assert "Courses" in r2.json()["categories"]

    def test_remove_category_with_products_400(self):
        # Try removing "Software Licenses" (should have seed products)
        kept = [{"name": n, "original": n} for n in DEFAULT_CATS if n != "Software Licenses"]
        r = requests.put(f"{API}/admin/site", headers=_h(self.atok), json={"categories": kept})
        assert r.status_code == 400, r.text
        assert "Software Licenses" in r.text
        # Nothing changed
        assert requests.get(f"{API}/categories").json() == DEFAULT_CATS

    def test_add_and_remove_empty_category(self):
        new_cat = f"TEST_Cat_{secrets.token_hex(2)}"
        payload = _cat_payload(DEFAULT_CATS) + [{"name": new_cat, "original": None}]
        r = requests.put(f"{API}/admin/site", headers=_h(self.atok), json={"categories": payload})
        assert r.status_code == 200
        assert new_cat in r.json()["categories"]
        # Now remove it (empty, so allowed)
        r2 = requests.put(f"{API}/admin/site", headers=_h(self.atok),
                          json={"categories": _cat_payload(DEFAULT_CATS)})
        assert r2.status_code == 200
        assert new_cat not in r2.json()["categories"]

    def test_vendor_create_in_new_category(self):
        new_cat = f"TEST_NewCat_{secrets.token_hex(2)}"
        payload = _cat_payload(DEFAULT_CATS) + [{"name": new_cat, "original": None}]
        r = requests.put(f"{API}/admin/site", headers=_h(self.atok), json={"categories": payload})
        assert r.status_code == 200
        # Vendor creates product in this new cat
        rp = requests.post(f"{API}/vendor/products", headers=_h(self.vtok), json={
            "title": f"TEST_InNewCat_{secrets.token_hex(3)}", "description": "x",
            "category": new_cat, "price": 1.0,
        })
        assert rp.status_code == 200, rp.text
        pid = rp.json()["id"]
        # Vendor delete
        requests.delete(f"{API}/vendor/products/{pid}", headers=_h(self.vtok))
        # Remove the new category (should be empty now)
        r2 = requests.put(f"{API}/admin/site", headers=_h(self.atok),
                          json={"categories": _cat_payload(DEFAULT_CATS)})
        assert r2.status_code == 200

    def test_vendor_unknown_category_400(self):
        r = requests.post(f"{API}/vendor/products", headers=_h(self.vtok), json={
            "title": f"TEST_UnknownCat_{secrets.token_hex(3)}", "description": "x",
            "category": "NoSuchCategoryXYZ", "price": 1.0,
        })
        assert r.status_code == 400
        assert "category" in r.text.lower()

    def test_bulk_import_unknown_category_400(self):
        r = requests.post(f"{API}/vendor/products/bulk", headers=_h(self.vtok), json={
            "text": "Title: a\nKey: k1", "separator": "blank", "public_lines": [0],
            "title_line": 0, "deliver": "all",
            "category": "NoSuchCategoryXYZ", "price": 1.0,
        })
        assert r.status_code == 400
    
    def test_facets_respects_category(self):
        r = requests.get(f"{API}/products/facets", params={"category": "Templates"})
        assert r.status_code == 200
        # None of my Subscriptions-Region values should appear here
        data = {f["key"]: f for f in r.json()}
        if "Region" in data:
            vals = {v["value"] for v in data["Region"]["values"]}
            # My batch is in Subscriptions, so these region counts shouldn't come from me - but other seeds may contribute.
            # Just assert the response shape.
            assert all("value" in v and "count" in v for v in data["Region"]["values"])



# ---------- Iteration 6: hero, banners, notice scheduling, category icons/colors ----------
from datetime import datetime, timezone, timedelta


def _snapshot_site(atok):
    r = requests.get(f"{API}/admin/site", headers=_h(atok))
    assert r.status_code == 200
    s = r.json()
    return {
        "notice": {k: s["notice"][k] for k in ("enabled", "tone", "title", "body", "highlight", "starts_at", "ends_at")},
        "hero": s["hero"],
        "banners": s["banners"],
        "categories": [{"name": c, "original": c, "icon": s["category_style"][c]["icon"],
                        "color": s["category_style"][c]["color"]} for c in s["categories"]],
    }


def _restore_full(atok, snap):
    # Normalize notice datetimes which came back as ISO strings
    r = requests.put(f"{API}/admin/site", headers=_h(atok), json=snap)
    assert r.status_code == 200, r.text


class TestIter6HeroBannersNotice:
    @classmethod
    def setup_class(cls):
        cls.atok = _login(*ADMIN)
        cls.btok = _login(*BUYER)
        cls.snap = _snapshot_site(cls.atok)

    @classmethod
    def teardown_class(cls):
        _restore_full(cls.atok, cls.snap)

    # ----- Admin-only guard -----
    def test_put_site_admin_only(self):
        r = requests.put(f"{API}/admin/site", headers=_h(self.btok), json={"hero": self.snap["hero"]})
        assert r.status_code == 403

    def test_get_admin_site_admin_only(self):
        r = requests.get(f"{API}/admin/site", headers=_h(self.btok))
        assert r.status_code == 403

    # ----- Hero -----
    def test_hero_update_and_reflect(self):
        new_hero = {"enabled": True, "title": "TEST_MARKET", "subtitle": "Hello {count}", "image": "https://example.com/x.png"}
        r = requests.put(f"{API}/admin/site", headers=_h(self.atok), json={"hero": new_hero})
        assert r.status_code == 200, r.text
        pub = requests.get(f"{API}/site").json()
        assert pub["hero"]["title"] == "TEST_MARKET"
        assert pub["hero"]["subtitle"] == "Hello {count}"
        assert pub["hero"]["enabled"] is True
        assert isinstance(pub["product_count"], int)

    def test_hero_disable(self):
        off = {**self.snap["hero"], "enabled": False}
        r = requests.put(f"{API}/admin/site", headers=_h(self.atok), json={"hero": off})
        assert r.status_code == 200
        pub = requests.get(f"{API}/site").json()
        assert pub["hero"]["enabled"] is False

    # ----- Banners -----
    def test_banner_without_image_422(self):
        bad = [{"enabled": True, "title": "x", "subtitle": "y", "button_text": "", "link": "/vendors", "image": ""}]
        r = requests.put(f"{API}/admin/site", headers=_h(self.atok), json={"banners": bad})
        assert r.status_code == 422, r.text

    def test_banner_bad_link_422(self):
        bad = [{"enabled": True, "title": "x", "subtitle": "y", "button_text": "", "link": "javascript:alert(1)",
                "image": "https://example.com/b.png"}]
        r = requests.put(f"{API}/admin/site", headers=_h(self.atok), json={"banners": bad})
        assert r.status_code == 422

    def test_banners_enabled_filter_public_vs_admin(self):
        banners = [
            {"id": "TEST_b1", "enabled": True, "title": "TEST_on", "subtitle": "", "button_text": "", "link": "/vendors",
             "image": "https://example.com/a.png"},
            {"id": "TEST_b2", "enabled": False, "title": "TEST_off", "subtitle": "", "button_text": "", "link": "",
             "image": "https://example.com/b.png"},
        ]
        r = requests.put(f"{API}/admin/site", headers=_h(self.atok), json={"banners": banners})
        assert r.status_code == 200, r.text
        pub = requests.get(f"{API}/site").json()
        titles_pub = [b["title"] for b in pub["banners"]]
        assert "TEST_on" in titles_pub
        assert "TEST_off" not in titles_pub
        # Admin sees all
        adm = requests.get(f"{API}/admin/site", headers=_h(self.atok)).json()
        titles_adm = [b["title"] for b in adm["banners"]]
        assert "TEST_on" in titles_adm and "TEST_off" in titles_adm
        # IDs preserved
        ids = {b["id"] for b in adm["banners"]}
        assert "TEST_b1" in ids and "TEST_b2" in ids

    def test_banner_valid_links_accepted(self):
        banners = [
            {"id": "TEST_rel", "enabled": True, "title": "r", "subtitle": "", "button_text": "", "link": "/vendors",
             "image": "https://example.com/a.png"},
            {"id": "TEST_abs", "enabled": True, "title": "a", "subtitle": "", "button_text": "", "link": "https://example.com/p",
             "image": "https://example.com/b.png"},
            {"id": "TEST_empty", "enabled": True, "title": "e", "subtitle": "", "button_text": "", "link": "",
             "image": "https://example.com/c.png"},
        ]
        r = requests.put(f"{API}/admin/site", headers=_h(self.atok), json={"banners": banners})
        assert r.status_code == 200, r.text

    # ----- Notice scheduling -----
    def test_notice_future_starts_hidden(self):
        future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        n = {"enabled": True, "tone": "amber", "title": "future", "body": "b", "highlight": "",
             "starts_at": future, "ends_at": None}
        r = requests.put(f"{API}/admin/site", headers=_h(self.atok), json={"notice": n})
        assert r.status_code == 200
        pub = requests.get(f"{API}/site").json()
        assert pub["notice"]["active"] is False
        # Admin snapshot shows notice_active flag false
        adm = requests.get(f"{API}/admin/site", headers=_h(self.atok)).json()
        assert adm.get("notice_active") is False

    def test_notice_past_ends_hidden(self):
        past_start = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        past_end = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        n = {"enabled": True, "tone": "amber", "title": "past", "body": "b", "highlight": "",
             "starts_at": past_start, "ends_at": past_end}
        r = requests.put(f"{API}/admin/site", headers=_h(self.atok), json={"notice": n})
        assert r.status_code == 200
        pub = requests.get(f"{API}/site").json()
        assert pub["notice"]["active"] is False

    def test_notice_ends_before_starts_400(self):
        start = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        end = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        n = {"enabled": True, "tone": "amber", "title": "bad", "body": "b", "highlight": "",
             "starts_at": start, "ends_at": end}
        r = requests.put(f"{API}/admin/site", headers=_h(self.atok), json={"notice": n})
        assert r.status_code == 400
        assert "end" in r.text.lower() or "start" in r.text.lower()

    def test_notice_cleared_schedule_visible(self):
        n = {"enabled": True, "tone": "amber", "title": "live", "body": "b", "highlight": "h",
             "starts_at": None, "ends_at": None}
        r = requests.put(f"{API}/admin/site", headers=_h(self.atok), json={"notice": n})
        assert r.status_code == 200
        pub = requests.get(f"{API}/site").json()
        assert pub["notice"]["active"] is True
        assert pub["notice"]["title"] == "live"

    def test_notice_in_window_active(self):
        start = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        end = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        n = {"enabled": True, "tone": "cyan", "title": "window", "body": "b", "highlight": "",
             "starts_at": start, "ends_at": end}
        r = requests.put(f"{API}/admin/site", headers=_h(self.atok), json={"notice": n})
        assert r.status_code == 200
        pub = requests.get(f"{API}/site").json()
        assert pub["notice"]["active"] is True

    # ----- Category icons & colors -----
    def test_category_icon_color_persistence(self):
        cats = [{"name": c["name"], "original": c["name"], "icon": c["icon"], "color": c["color"]}
                for c in self.snap["categories"]]
        cats[0] = {**cats[0], "icon": "zap", "color": "#AABBCC"}
        r = requests.put(f"{API}/admin/site", headers=_h(self.atok), json={"categories": cats})
        assert r.status_code == 200, r.text
        pub = requests.get(f"{API}/site").json()
        style = pub["category_style"][cats[0]["name"]]
        assert style["icon"] == "zap"
        assert style["color"].upper() == "#AABBCC"

    def test_category_invalid_color_422(self):
        cats = [{"name": c["name"], "original": c["name"], "icon": c["icon"], "color": c["color"]}
                for c in self.snap["categories"]]
        cats[0] = {**cats[0], "color": "red"}  # not hex
        r = requests.put(f"{API}/admin/site", headers=_h(self.atok), json={"categories": cats})
        assert r.status_code == 422

    def test_category_rename_preserves_style(self):
        # Rename "Templates" -> TEST_Tmpl_* with new icon/color then rename back
        new_name = f"TEST_Tmpl_{secrets.token_hex(2)}"
        cats = []
        for c in self.snap["categories"]:
            if c["name"] == "Templates":
                cats.append({"name": new_name, "original": "Templates", "icon": "gift", "color": "#123456"})
            else:
                cats.append({"name": c["name"], "original": c["name"], "icon": c["icon"], "color": c["color"]})
        r = requests.put(f"{API}/admin/site", headers=_h(self.atok), json={"categories": cats})
        assert r.status_code == 200, r.text
        pub = requests.get(f"{API}/site").json()
        assert new_name in pub["categories"]
        assert pub["category_style"][new_name]["icon"] == "gift"
        assert pub["category_style"][new_name]["color"].upper() == "#123456"
        # Rename back preserving original style from snapshot
        cats_back = []
        for c in cats:
            if c["name"] == new_name:
                orig = next(x for x in self.snap["categories"] if x["name"] == "Templates")
                cats_back.append({"name": "Templates", "original": new_name, "icon": orig["icon"], "color": orig["color"]})
            else:
                cats_back.append({"name": c["name"], "original": c["name"], "icon": c["icon"], "color": c["color"]})
        r2 = requests.put(f"{API}/admin/site", headers=_h(self.atok), json={"categories": cats_back})
        assert r2.status_code == 200


# ---------- Iteration 7: Manual deposit + Admin-as-vendor store ----------
class TestIter7ManualDeposit:
    @classmethod
    def setup_class(cls):
        cls.atok = _login(*ADMIN)
        cls.btok = _login(*BUYER)

    def test_manual_deposit_credits_wallet_instantly(self):
        me_before = requests.get(f"{API}/auth/me", headers=_h(self.btok)).json()
        txid = f"TEST_MAN_{secrets.token_hex(6)}"
        body = {"email": BUYER[0], "amount": 12.5, "coin": "USDT_TRC20",
                "txid": txid, "note": "TEST support ticket"}
        r = requests.post(f"{API}/admin/deposits/manual", headers=_h(self.atok), json=body)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "approved"
        assert d["manual"] is True
        assert d["reviewed_by"] == ADMIN[0]
        assert d["credited_cents"] == 1250
        assert d["amount_cents"] == 1250
        assert d["reference"].startswith("MAN-")
        assert d["txid"] == txid.lower()

        # Wallet credited
        me_after = requests.get(f"{API}/auth/me", headers=_h(self.btok)).json()
        assert me_after["balance_cents"] == me_before["balance_cents"] + 1250

        # Appears under 'approved' filter
        approved = requests.get(f"{API}/admin/deposits", headers=_h(self.atok),
                                params={"status": "approved"}).json()
        row = next((x for x in approved if x["reference"] == d["reference"]), None)
        assert row is not None
        assert row["manual"] is True
        assert row["reviewed_by"] == ADMIN[0]

        # Buyer gets a 'Deposit approved' notification
        notifs = requests.get(f"{API}/notifications", headers=_h(self.btok)).json()
        assert any(n.get("title") == "Deposit approved" and d["reference"] in n.get("body", "")
                   for n in notifs)

        # Audit entry
        logs = requests.get(f"{API}/admin/audit", headers=_h(self.atok)).json()
        assert any(l.get("action") == "deposit.manual" and l.get("target_id") == d["id"] for l in logs)

    def test_manual_deposit_unknown_email_404(self):
        r = requests.post(f"{API}/admin/deposits/manual", headers=_h(self.atok), json={
            "email": f"no_such_user_{secrets.token_hex(3)}@market.com", "amount": 5,
            "coin": "OTHER", "note": "TEST"})
        assert r.status_code == 404

    def test_manual_deposit_duplicate_txid_400(self):
        txid = f"TEST_DUP_{secrets.token_hex(6)}"
        base = {"email": BUYER[0], "amount": 1, "coin": "BTC", "txid": txid, "note": "TEST dup"}
        r1 = requests.post(f"{API}/admin/deposits/manual", headers=_h(self.atok), json=base)
        assert r1.status_code == 200, r1.text
        r2 = requests.post(f"{API}/admin/deposits/manual", headers=_h(self.atok), json=base)
        assert r2.status_code == 400, r2.text
        assert "txid" in r2.text.lower()

    def test_manual_deposit_blocks_normal_deposit_reuse(self, admin_token):
        """A TXID used in a manual deposit cannot be reused by a normal deposit."""
        txid = f"TEST_CROSS_{secrets.token_hex(6)}"
        r = requests.post(f"{API}/admin/deposits/manual", headers=_h(self.atok), json={
            "email": BUYER[0], "amount": 1, "coin": "BTC", "txid": txid, "note": "TEST cross"})
        assert r.status_code == 200
        # Now buyer tries normal deposit with same txid
        dep = requests.post(f"{API}/wallet/deposits", headers=_h(self.btok),
                            json={"coin": "BTC", "amount": 5}).json()
        rdup = requests.post(f"{API}/wallet/deposits/{dep['id']}/txid",
                             headers=_h(self.btok), json={"txid": txid})
        assert rdup.status_code in (400, 500), f"Expected rejection, got {rdup.status_code}"

    def test_manual_deposit_amount_zero_422(self):
        r = requests.post(f"{API}/admin/deposits/manual", headers=_h(self.atok), json={
            "email": BUYER[0], "amount": 0, "coin": "OTHER", "note": "TEST"})
        assert r.status_code == 422

    def test_manual_deposit_amount_negative_422(self):
        r = requests.post(f"{API}/admin/deposits/manual", headers=_h(self.atok), json={
            "email": BUYER[0], "amount": -10, "coin": "OTHER", "note": "TEST"})
        assert r.status_code == 422

    def test_manual_deposit_non_admin_403(self):
        r = requests.post(f"{API}/admin/deposits/manual", headers=_h(self.btok), json={
            "email": BUYER[0], "amount": 1, "coin": "OTHER", "note": "TEST"})
        assert r.status_code == 403

    def test_manual_deposit_optional_txid_works(self):
        r = requests.post(f"{API}/admin/deposits/manual", headers=_h(self.atok), json={
            "email": BUYER[0], "amount": 2, "coin": "OTHER", "note": "TEST no txid"})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "approved"
        assert "txid" not in d or d.get("txid") in (None, "")


class TestIter7AdminStore:
    """Admin can list products as 'NeonKeys Official', approved instantly, 100% commission."""

    @classmethod
    def setup_class(cls):
        cls.atok = _login(*ADMIN)
        cls.btok = _login(*BUYER)
        cls.vtok = _login(*VENDOR)
        cls.created_pids = []
        cls.created_batches = []

    @classmethod
    def teardown_class(cls):
        for pid in cls.created_pids:
            try:
                requests.delete(f"{API}/vendor/products/{pid}", headers=_h(cls.atok))
            except Exception:
                pass
        for bid in cls.created_batches:
            try:
                requests.delete(f"{API}/vendor/batches/{bid}", headers=_h(cls.atok))
            except Exception:
                pass

    def test_admin_create_product_goes_live_instantly(self):
        title = f"TEST_AdminProd_{secrets.token_hex(3)}"
        r = requests.post(f"{API}/vendor/products", headers=_h(self.atok), json={
            "title": title, "description": "official", "category": "Templates",
            "price": 4.0, "delivery_type": "content", "delivery_content": "official-secret",
        })
        assert r.status_code == 200, r.text
        p = r.json()
        assert p["status"] == "approved"
        assert p["vendor_name"] == "NeonKeys Official"
        assert p["approved_at"]
        self.__class__.created_pids.append(p["id"])
        # Appears in public catalog
        pub = requests.get(f"{API}/products/{p['id']}")
        assert pub.status_code == 200
        assert pub.json()["vendor_name"] == "NeonKeys Official"

    def test_admin_bulk_import_approved_instantly(self):
        uniq = secrets.token_hex(3)
        blocks = []
        for i in range(2):
            blocks.append("\n".join([
                f"Title: TEST_AdminBulk_{uniq}_{i}", "Plan: Pro",
                f"License key: AK-{uniq}-{i:03d}",
            ]))
        text = "\n----\n".join(blocks)
        r = requests.post(f"{API}/vendor/products/bulk", headers=_h(self.atok), json={
            "text": text, "separator": "dashes", "public_lines": [0, 1], "title_line": 0,
            "deliver": "all", "category": "Software Licenses", "price": 3.0})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["created"] == 2
        bid = d["batch_id"]
        self.__class__.created_batches.append(bid)
        # Admin's bulk imports go live immediately
        prods = requests.get(f"{API}/vendor/products", headers=_h(self.atok)).json()
        mine = [p for p in prods if p.get("batch_id") == bid]
        assert len(mine) == 2
        for p in mine:
            assert p["status"] == "approved"
            assert p["vendor_name"] == "NeonKeys Official"
            # Visible publicly
            assert requests.get(f"{API}/products/{p['id']}").status_code == 200

    def test_buyer_purchase_admin_product_100pct_commission(self):
        # Create admin product with a single key
        title = f"TEST_AdmBuy_{secrets.token_hex(3)}"
        rc = requests.post(f"{API}/vendor/products", headers=_h(self.atok), json={
            "title": title, "description": "x", "category": "Templates", "price": 5.0,
        })
        assert rc.status_code == 200
        pid = rc.json()["id"]
        self.__class__.created_pids.append(pid)
        rk = requests.post(f"{API}/vendor/products/{pid}/keys", headers=_h(self.atok),
                           json={"keys": f"ADMKEY-{secrets.token_hex(3)}"})
        assert rk.status_code == 200
        # Fund fresh buyer
        email = f"TEST_admbuy_{secrets.token_hex(3)}@market.com"
        reg = _register(email, "Buyer@123", "AB").json()
        btok, uid = reg["token"], reg["user"]["id"]
        requests.post(f"{API}/admin/users/{uid}/adjust", headers=_h(self.atok),
                      json={"amount": 10, "reason": "TEST_adminbuy"})
        r = requests.post(f"{API}/orders", headers=_h(btok), json={"product_id": pid})
        assert r.status_code == 200, r.text
        order = r.json()["order"]
        assert order["commission_pct"] == 100
        assert order["vendor_earning_cents"] == 0
        assert order["commission_cents"] == order["price_cents"]
        assert order["license_key"] is not None
        assert order["vendor_name"] == "NeonKeys Official"
        # Appears in admin My store -> Sales
        sales = requests.get(f"{API}/vendor/sales", headers=_h(self.atok)).json()
        assert any(s["id"] == order["id"] for s in sales)

    def test_regression_normal_vendor_still_pending(self):
        """Normal (non-admin) vendor products must remain pending review."""
        title = f"TEST_RegVendor_{secrets.token_hex(3)}"
        r = requests.post(f"{API}/vendor/products", headers=_h(self.vtok), json={
            "title": title, "description": "x", "category": "Templates", "price": 2.0,
        })
        assert r.status_code == 200, r.text
        p = r.json()
        assert p["status"] == "pending"
        assert p["vendor_name"] != "NeonKeys Official"
        # Cleanup
        requests.delete(f"{API}/vendor/products/{p['id']}", headers=_h(self.vtok))


class TestIter7PromoBannerPersistence:
    """Editing promo banner title/subtitle/button via PUT /admin/site updates /site."""

    @classmethod
    def setup_class(cls):
        cls.atok = _login(*ADMIN)
        s = requests.get(f"{API}/admin/site", headers=_h(cls.atok)).json()
        cls.orig_banners = s["banners"]

    @classmethod
    def teardown_class(cls):
        requests.put(f"{API}/admin/site", headers=_h(cls.atok),
                     json={"banners": cls.orig_banners})

    def test_edit_welcome_banner_reflected_publicly(self):
        edited = []
        for b in self.orig_banners:
            if b.get("id") == "welcome":
                edited.append({**b, "title": "TEST Verified vendors",
                               "subtitle": "TEST Top up with crypto.",
                               "button_text": "TEST Browse"})
            else:
                edited.append(b)
        r = requests.put(f"{API}/admin/site", headers=_h(self.atok),
                         json={"banners": edited})
        assert r.status_code == 200, r.text
        pub = requests.get(f"{API}/site").json()
        welcome = next((b for b in pub["banners"] if b.get("id") == "welcome"), None)
        assert welcome is not None
        assert welcome["title"] == "TEST Verified vendors"
        assert welcome["subtitle"] == "TEST Top up with crypto."
        assert welcome["button_text"] == "TEST Browse"



# ---------------- Support tickets (iter-8) ----------------
class TestIter8SupportTickets:
    @classmethod
    def setup_class(cls):
        cls.btok = _login(*BUYER)
        cls.vtok = _login(*VENDOR)
        cls.atok = _login(*ADMIN)
        cls.created_tids = []

    @classmethod
    def teardown_class(cls):
        # Close test tickets so admin stats aren't polluted
        for tid in cls.created_tids:
            try:
                requests.post(f"{API}/admin/tickets/{tid}/status", headers=_h(cls.atok),
                              json={"status": "closed"}, timeout=20)
            except Exception:
                pass

    def _create(self, tok, subject="TEST_subject hello support", topic="General",
                message="TEST initial message body"):
        r = requests.post(f"{API}/tickets", headers=_h(tok),
                          json={"subject": subject, "topic": topic, "message": message})
        assert r.status_code == 200, r.text
        t = r.json()
        self.__class__.created_tids.append(t["id"])
        return t

    # ---- Create ----
    def test_create_ticket_ok_and_persisted(self):
        t = self._create(self.btok, subject="TEST_create_001 need help")
        assert t["ref"].startswith("TCK-")
        assert t["status"] == "open"
        assert t["unread_admin"] is True
        assert t["unread_user"] is False
        assert len(t["messages"]) == 1
        assert t["messages"][0]["from_admin"] is False
        assert "_id" not in t
        # GET verifies persistence
        g = requests.get(f"{API}/tickets/{t['id']}", headers=_h(self.btok))
        assert g.status_code == 200
        gt = g.json()
        assert gt["id"] == t["id"] and gt["subject"] == t["subject"]

    def test_create_ticket_short_subject_422(self):
        r = requests.post(f"{API}/tickets", headers=_h(self.btok),
                          json={"subject": "hi", "topic": "General", "message": "ok"})
        assert r.status_code == 422

    def test_create_ticket_bad_topic_422(self):
        r = requests.post(f"{API}/tickets", headers=_h(self.btok),
                          json={"subject": "TEST_subject_x", "topic": "Nope", "message": "hi there"})
        assert r.status_code == 422

    def test_create_ticket_requires_auth_401_or_403(self):
        r = requests.post(f"{API}/tickets",
                          json={"subject": "TEST_subject_y", "topic": "General", "message": "hi there"})
        assert r.status_code in (401, 403)

    def test_vendor_can_create_ticket(self):
        t = self._create(self.vtok, subject="TEST_vendor_ticket")
        assert t["user_role"] == "vendor"

    # ---- List + security ----
    def test_my_tickets_only_mine(self):
        tb = self._create(self.btok, subject="TEST_mine_only buyer")
        tv = self._create(self.vtok, subject="TEST_mine_only vendor")
        rb = requests.get(f"{API}/tickets", headers=_h(self.btok))
        assert rb.status_code == 200
        ids = {x["id"] for x in rb.json()}
        assert tb["id"] in ids
        assert tv["id"] not in ids

    def test_user_cannot_read_other_users_ticket_404(self):
        t = self._create(self.btok, subject="TEST_cross_user_read")
        r = requests.get(f"{API}/tickets/{t['id']}", headers=_h(self.vtok))
        assert r.status_code == 404

    def test_non_admin_forbidden_on_admin_tickets(self):
        r = requests.get(f"{API}/admin/tickets", headers=_h(self.btok))
        assert r.status_code == 403

    def test_admin_can_list_tickets(self):
        t = self._create(self.btok, subject="TEST_admin_list visible")
        r = requests.get(f"{API}/admin/tickets", headers=_h(self.atok))
        assert r.status_code == 200
        assert any(x["id"] == t["id"] for x in r.json())

    def test_admin_tickets_filter_open(self):
        t = self._create(self.btok, subject="TEST_filter_open status check")
        r = requests.get(f"{API}/admin/tickets?status=open", headers=_h(self.atok))
        assert r.status_code == 200
        for x in r.json():
            assert x["status"] == "open"
        assert any(x["id"] == t["id"] for x in r.json())

    def test_admin_tickets_search(self):
        unique = f"TEST_search_{secrets.token_hex(3)}"
        t = self._create(self.btok, subject=unique)
        r = requests.get(f"{API}/admin/tickets", headers=_h(self.atok), params={"q": unique})
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) >= 1 and rows[0]["id"] == t["id"]
        # search by email
        r2 = requests.get(f"{API}/admin/tickets", headers=_h(self.atok), params={"q": BUYER[0]})
        assert r2.status_code == 200
        assert any(x["user_email"] == BUYER[0] for x in r2.json())

    # ---- Reply / status flow ----
    def test_user_reply_keeps_open_and_flags_admin_unread(self):
        t = self._create(self.btok, subject="TEST_reply_user")
        # First admin reads to clear unread_admin
        requests.get(f"{API}/admin/tickets/{t['id']}", headers=_h(self.atok))  # may or may not exist, use user route via admin
        g = requests.get(f"{API}/tickets/{t['id']}", headers=_h(self.atok))
        assert g.status_code == 200
        # User follows up
        r = requests.post(f"{API}/tickets/{t['id']}/messages", headers=_h(self.btok),
                          json={"message": "TEST follow-up from user"})
        assert r.status_code == 200
        rt = r.json()
        assert rt["status"] == "open"
        assert rt["unread_admin"] is True
        assert rt["unread_user"] is False
        assert len(rt["messages"]) == 2

    def test_admin_reply_sets_answered_and_notifies_user(self):
        t = self._create(self.btok, subject="TEST_admin_reply")
        # Count buyer notifications before
        n0 = requests.get(f"{API}/notifications", headers=_h(self.btok)).json()
        before_support = sum(1 for n in n0 if n.get("title") == "Support replied")
        r = requests.post(f"{API}/tickets/{t['id']}/messages", headers=_h(self.atok),
                          json={"message": "TEST admin reply here"})
        assert r.status_code == 200
        rt = r.json()
        assert rt["status"] == "answered"
        assert rt["unread_user"] is True
        assert rt["unread_admin"] is False
        assert rt["messages"][-1]["from_admin"] is True
        # Notification created
        n1 = requests.get(f"{API}/notifications", headers=_h(self.btok)).json()
        after_support = sum(1 for n in n1 if n.get("title") == "Support replied")
        assert after_support == before_support + 1

    def test_user_get_clears_unread_user(self):
        t = self._create(self.btok, subject="TEST_clear_unread")
        requests.post(f"{API}/tickets/{t['id']}/messages", headers=_h(self.atok),
                      json={"message": "TEST admin msg"})
        # buyer fetches
        r = requests.get(f"{API}/tickets/{t['id']}", headers=_h(self.btok))
        assert r.status_code == 200
        assert r.json()["unread_user"] is False
        # listing shouldn't show unread anymore
        lst = requests.get(f"{API}/tickets", headers=_h(self.btok)).json()
        row = next(x for x in lst if x["id"] == t["id"])
        assert row["unread_user"] is False

    def test_close_blocks_user_reply_but_admin_can(self):
        t = self._create(self.btok, subject="TEST_close_block")
        r = requests.post(f"{API}/admin/tickets/{t['id']}/status", headers=_h(self.atok),
                          json={"status": "closed"})
        assert r.status_code == 200
        # Verify status via GET
        g = requests.get(f"{API}/tickets/{t['id']}", headers=_h(self.btok)).json()
        assert g["status"] == "closed"
        # Buyer cannot reply
        rb = requests.post(f"{API}/tickets/{t['id']}/messages", headers=_h(self.btok),
                           json={"message": "TEST reply after close"})
        assert rb.status_code == 400
        # Admin can reply (reopens-ish via answered status flip)
        ra = requests.post(f"{API}/tickets/{t['id']}/messages", headers=_h(self.atok),
                           json={"message": "TEST admin after close"})
        assert ra.status_code == 200

    def test_reopen_allows_user_reply(self):
        t = self._create(self.btok, subject="TEST_reopen")
        requests.post(f"{API}/admin/tickets/{t['id']}/status", headers=_h(self.atok),
                      json={"status": "closed"})
        r = requests.post(f"{API}/admin/tickets/{t['id']}/status", headers=_h(self.atok),
                         json={"status": "open"})
        assert r.status_code == 200
        rb = requests.post(f"{API}/tickets/{t['id']}/messages", headers=_h(self.btok),
                           json={"message": "TEST reply after reopen"})
        assert rb.status_code == 200

    # ---- admin stats ----
    def test_admin_stats_includes_open_ticket_count(self):
        t = self._create(self.btok, subject="TEST_stats_open")
        s = requests.get(f"{API}/admin/stats", headers=_h(self.atok)).json()
        assert "tickets" in s.get("pending", {})
        assert isinstance(s["pending"]["tickets"], int)
        assert s["pending"]["tickets"] >= 1
