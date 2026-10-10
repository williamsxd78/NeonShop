"""Admin delete-user / delete-vendor / delete-product tests (iteration 11)."""
import os
import time
import secrets
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split("\n")[0].strip().rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = ("admin@market.com", "Admin@123")
BUYER = ("buyer@market.com", "Buyer@123")
VENDOR = ("vendor@market.com", "Vendor@123")


def _solve_captcha():
    d = requests.get(f"{API}/auth/captcha", timeout=30).json()
    q = d["question"].replace("= ?", "").strip()
    for op, sym in [("+", "+"), ("-", "-"), ("×", "*")]:
        if op in q:
            a, b = q.split(op)
            ans = eval(f"{a.strip()}{sym}{b.strip()}")
            break
    return {"captcha_id": d["captcha_id"], "captcha_answer": str(ans)}


def _login(email, password):
    body = {"email": email, "password": password, **_solve_captcha()}
    r = requests.post(f"{API}/auth/login", json=body, timeout=30)
    assert r.status_code == 200, f"{email}: {r.status_code} {r.text}"
    return r.json()["token"]


def _register(email, password, name, role="buyer", store_name=None):
    body = {"email": email, "password": password, "name": name, "role": role, **_solve_captcha()}
    if store_name:
        body["store_name"] = store_name
    r = requests.post(f"{API}/auth/register", json=body, timeout=30)
    assert r.status_code == 200, f"register {email}: {r.status_code} {r.text}"
    return r.json()


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def admin_tok():
    return _login(*ADMIN)


@pytest.fixture(scope="module")
def buyer_tok():
    return _login(*BUYER)


def _mkuser(role="buyer"):
    suffix = secrets.token_hex(4)
    email = f"TEST_del_{role}_{suffix}@market.com"
    pw = "Passw0rd!"
    name = f"TEST {role} {suffix}"
    r = _register(email, pw, name, role=role, store_name=f"TEST Store {suffix}" if role == "vendor" else None)
    return {"email": email, "password": pw, "id": r["user"]["id"], "token": r["token"], "name": name}


# ---------- Authorization checks ----------

def test_delete_user_requires_admin(buyer_tok):
    # make a dummy target so endpoint reaches the auth check
    r = requests.delete(f"{API}/admin/users/nonexistent", headers=_h(buyer_tok), timeout=30)
    assert r.status_code in (401, 403), r.text


def test_delete_user_unauthenticated():
    r = requests.delete(f"{API}/admin/users/nonexistent", timeout=30)
    assert r.status_code in (401, 403), r.text


def test_delete_unknown_user_404(admin_tok):
    r = requests.delete(f"{API}/admin/users/does-not-exist-xyz", headers=_h(admin_tok), timeout=30)
    assert r.status_code == 404


def test_delete_self_400(admin_tok):
    me = requests.get(f"{API}/auth/me", headers=_h(admin_tok), timeout=30).json()
    r = requests.delete(f"{API}/admin/users/{me['id']}", headers=_h(admin_tok), timeout=30)
    assert r.status_code == 400


def test_delete_another_admin_400(admin_tok):
    # find another admin if exists; else create one via DB? We can't create admin via register.
    # Instead confirm the role check path: temporarily we skip if only 1 admin.
    users = requests.get(f"{API}/admin/users", headers=_h(admin_tok), params={"role": "admin"}, timeout=30).json()
    me = requests.get(f"{API}/auth/me", headers=_h(admin_tok), timeout=30).json()
    others = [u for u in users if u["id"] != me["id"]]
    if not others:
        pytest.skip("only one admin seeded; cannot test cross-admin block separately from self-block")
    r = requests.delete(f"{API}/admin/users/{others[0]['id']}", headers=_h(admin_tok), timeout=30)
    assert r.status_code == 400


# ---------- Buyer deletion cascade ----------

def test_delete_buyer_cascades(admin_tok):
    buyer = _mkuser("buyer")
    bid = buyer["id"]
    btok = buyer["token"]

    # Create a deposit (pending) - correct endpoint & body
    dr = requests.post(f"{API}/wallet/deposits", json={"coin": "BTC", "amount": 10.0}, headers=_h(btok), timeout=30)
    assert dr.status_code == 200, dr.text
    # Create a ticket
    tr = requests.post(f"{API}/tickets", json={"subject": "TEST subject", "message": "hello world", "topic": "General"}, headers=_h(btok), timeout=30)
    assert tr.status_code == 200, tr.text

    # Confirm docs exist pre-delete
    deps = requests.get(f"{API}/admin/deposits", headers=_h(admin_tok), params={"status": "all"}, timeout=30).json()
    assert any(d.get("user_id") == bid for d in deps)

    # DELETE
    r = requests.delete(f"{API}/admin/users/{bid}", headers=_h(admin_tok), timeout=30)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    for k in ("products", "keys", "orders", "deposits", "withdrawals", "tickets"):
        assert k in body

    # User GONE
    users = requests.get(f"{API}/admin/users", headers=_h(admin_tok), params={"q": buyer["email"]}, timeout=30).json()
    assert not any(u["id"] == bid for u in users)

    # Can no longer login
    r = requests.post(f"{API}/auth/login", json={"email": buyer["email"], "password": buyer["password"], **_solve_captcha()}, timeout=30)
    assert r.status_code == 401, f"deleted buyer should not login: {r.status_code}"

    # Deposits cleaned up
    deps2 = requests.get(f"{API}/admin/deposits", headers=_h(admin_tok), params={"status": "all"}, timeout=30).json()
    assert not any(d.get("user_id") == bid for d in deps2)

    # Audit entry 'user.delete' exists for this uid
    audit = requests.get(f"{API}/admin/audit", headers=_h(admin_tok), params={"action": "user.delete"}, timeout=30).json()
    assert any(a.get("target_id") == bid or bid in str(a) for a in audit), "no audit entry for user.delete"


# ---------- Vendor deletion cascade ----------

def test_delete_vendor_cascades(admin_tok):
    vendor = _mkuser("vendor")
    vid = vendor["id"]
    vtok = vendor["token"]
    # approve the vendor so they can list
    r = requests.post(f"{API}/admin/vendors/{vid}/approve", headers=_h(admin_tok), timeout=30)
    assert r.status_code == 200, r.text

    # Create a product with keys
    prod = {
        "title": f"TEST product {secrets.token_hex(3)}",
        "description": "x",
        "category": "Software Licenses",
        "price": 5.0,
        "delivery_type": "keys",
    }
    pr = requests.post(f"{API}/vendor/products", json=prod, headers=_h(vtok), timeout=30)
    assert pr.status_code == 200, pr.text
    pid = pr.json()["id"]
    # add some keys
    requests.post(f"{API}/vendor/products/{pid}/keys", json={"keys": "TESTKEY-A\nTESTKEY-B"}, headers=_h(vtok), timeout=30)
    # approve so it goes live (optional)
    requests.post(f"{API}/admin/products/{pid}/approve", json={"price": 5.0}, headers=_h(admin_tok), timeout=30)

    # verify product listed in public marketplace
    pubs = requests.get(f"{API}/products", timeout=30).json()
    assert any(p["id"] == pid for p in pubs if isinstance(p, dict))

    # DELETE vendor
    r = requests.delete(f"{API}/admin/users/{vid}", headers=_h(admin_tok), timeout=30)
    assert r.status_code == 200, r.text
    counts = r.json()
    assert counts["products"] >= 1
    assert counts["keys"] >= 2

    # product removed from marketplace
    pubs2 = requests.get(f"{API}/products", timeout=30).json()
    assert not any(p["id"] == pid for p in pubs2 if isinstance(p, dict))

    # vendor cannot login
    r = requests.post(f"{API}/auth/login", json={"email": vendor["email"], "password": vendor["password"], **_solve_captcha()}, timeout=30)
    assert r.status_code == 401, f"deleted vendor should not login: {r.status_code}"


# ---------- Product delete regression (unsold keys only) ----------

def test_delete_product_keeps_sold_keys(admin_tok):
    vendor = _mkuser("vendor")
    vid = vendor["id"]
    vtok = vendor["token"]
    requests.post(f"{API}/admin/vendors/{vid}/approve", headers=_h(admin_tok), timeout=30)

    prod = {"title": f"TEST reg {secrets.token_hex(3)}", "description": "x", "category": "Software Licenses", "price": 2.0, "delivery_type": "keys"}
    pr = requests.post(f"{API}/vendor/products", json=prod, headers=_h(vtok), timeout=30)
    pid = pr.json()["id"]
    requests.post(f"{API}/vendor/products/{pid}/keys", json={"keys": "TESTREG-A\nTESTREG-B\nTESTREG-C"}, headers=_h(vtok), timeout=30)
    requests.post(f"{API}/admin/products/{pid}/approve", json={"price": 2.0}, headers=_h(admin_tok), timeout=30)

    # buyer buys one key -> credit buyer wallet first via admin adjust
    buyer = _mkuser("buyer")
    btok = buyer["token"]
    bid = buyer["id"]
    requests.post(f"{API}/admin/users/{bid}/adjust", json={"amount": 10.0, "reason": "TEST"}, headers=_h(admin_tok), timeout=30)
    buy = requests.post(f"{API}/orders", json={"product_id": pid, }, headers=_h(btok), timeout=30)
    assert buy.status_code == 200, buy.text

    # DELETE product
    r = requests.delete(f"{API}/admin/products/{pid}", headers=_h(admin_tok), timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["deleted"] == 1
    assert data["keys_removed"] == 2  # 3 added, 1 sold -> 2 unsold removed

    # orders remain (buyer still sees order)
    my_orders = requests.get(f"{API}/orders", headers=_h(btok), timeout=30).json()
    assert any(o.get("product_id") == pid for o in my_orders), "sold order should remain"

    # cleanup
    requests.delete(f"{API}/admin/users/{vid}", headers=_h(admin_tok), timeout=30)
    requests.delete(f"{API}/admin/users/{bid}", headers=_h(admin_tok), timeout=30)
