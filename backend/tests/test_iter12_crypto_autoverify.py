"""Crypto deposit auto-verify tests (iteration 12).

Covers:
- GET /api/admin/settings exposes auto_verify for BTC, USDT_TRC20, USDT_BEP20, LTC, ETH
- PUT /api/admin/settings persists auto_verify (restored after)
- GET /api/wallet/coins includes USDT_BEP20 (BEP20 network)
- E2E BTC auto-credit against a real recent mainnet transaction
- Mismatch deposit stays pending with chain.state=mismatch
- POST /api/admin/deposits/{id}/recheck
- Manual approve of a pending auto-checking deposit transitions status=approved
"""
import os
import time
import secrets
import requests
import pytest

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or
            open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split("\n")[0].strip()).rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = ("admin@market.com", "Admin@123")
BUYER = ("buyer@market.com", "Buyer@123")


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


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def admin_tok():
    return _login(*ADMIN)


@pytest.fixture(scope="module")
def buyer_tok():
    return _login(*BUYER)


# ---- Settings ------------------------------------------------------
def test_admin_settings_has_auto_verify(admin_tok):
    r = requests.get(f"{API}/admin/settings", headers=_h(admin_tok), timeout=30)
    assert r.status_code == 200
    av = r.json().get("auto_verify")
    assert av, "auto_verify missing"
    for c in ("BTC", "USDT_TRC20", "USDT_BEP20", "LTC", "ETH"):
        assert c in av, f"{c} missing in auto_verify"
        assert "enabled" in av[c] and "confirmations" in av[c]
        assert av[c]["enabled"] is True  # default ON per spec
    # Default confirmations per spec
    assert av["BTC"]["confirmations"] == 2
    assert av["USDT_TRC20"]["confirmations"] == 20
    assert av["USDT_BEP20"]["confirmations"] == 15
    assert av["LTC"]["confirmations"] == 6
    assert av["ETH"]["confirmations"] == 12


def test_put_admin_settings_persists_auto_verify(admin_tok):
    before = requests.get(f"{API}/admin/settings", headers=_h(admin_tok), timeout=30).json()["auto_verify"]
    body = {"auto_verify": {c: {"enabled": v["enabled"], "confirmations": v["confirmations"]} for c, v in before.items()}}
    body["auto_verify"]["BTC"] = {"enabled": False, "confirmations": 3}
    r = requests.put(f"{API}/admin/settings", json=body, headers=_h(admin_tok), timeout=30)
    assert r.status_code == 200, r.text
    av2 = r.json()["auto_verify"]
    assert av2["BTC"] == {"enabled": False, "confirmations": 3}
    # Confirm persistence via re-GET
    av3 = requests.get(f"{API}/admin/settings", headers=_h(admin_tok), timeout=30).json()["auto_verify"]
    assert av3["BTC"] == {"enabled": False, "confirmations": 3}
    # Restore
    restore = {"auto_verify": {c: {"enabled": v["enabled"], "confirmations": v["confirmations"]} for c, v in before.items()}}
    r2 = requests.put(f"{API}/admin/settings", json=restore, headers=_h(admin_tok), timeout=30)
    assert r2.status_code == 200
    av4 = r2.json()["auto_verify"]
    assert av4["BTC"] == before["BTC"]


# ---- Wallet coins --------------------------------------------------
def test_wallet_coins_has_usdt_bep20(buyer_tok):
    r = requests.get(f"{API}/wallet/coins", headers=_h(buyer_tok), timeout=30)
    assert r.status_code == 200
    coins = {c["code"]: c for c in r.json()}
    assert "USDT_BEP20" in coins
    assert "BEP20" in coins["USDT_BEP20"]["network"]


# ---- E2E auto-credit using a real mainnet BTC transaction ----------
def _pick_real_btc_txs(n=2, exclude=frozenset()):
    """Return list of (txid, output_address, sats) from distinct confirmed mainnet txs."""
    out = []
    seen = set(exclude)
    blocks = requests.get("https://mempool.space/api/blocks", timeout=30).json()
    for block in blocks[3:]:
        bhash = block["id"]
        txids = requests.get(f"https://mempool.space/api/block/{bhash}/txids", timeout=30).json()
        for tid in txids[1:60]:
            if tid in seen:
                continue
            try:
                tx = requests.get(f"https://mempool.space/api/tx/{tid}", timeout=30).json()
            except Exception:
                continue
            for v in tx.get("vout", []):
                addr = v.get("scriptpubkey_address")
                val = v.get("value", 0)
                if addr and addr.startswith(("bc1", "1", "3")) and val >= 10000:
                    out.append((tid, addr, val))
                    seen.add(tid)
                    if len(out) >= n:
                        return out
                    break
    if len(out) < n:
        pytest.skip(f"Could not find {n} suitable BTC txs on mempool.space")
    return out


@pytest.fixture(scope="module")
def real_btc_txs(admin_tok):
    # Exclude txids already stored in the DB from previous runs
    used = set()
    try:
        deps = requests.get(f"{API}/admin/deposits?status=all", headers=_h(admin_tok), timeout=30).json()
        used = {d["txid"] for d in deps if d.get("txid")}
    except Exception:
        pass
    return _pick_real_btc_txs(2, exclude=used)


@pytest.fixture(scope="module")
def real_btc_tx(real_btc_txs):
    return real_btc_txs[0]


def _get_settings(tok):
    return requests.get(f"{API}/admin/settings", headers=_h(tok), timeout=30).json()


def _put_addr(tok, settings, coin, address):
    body = {"addresses": {c: settings["addresses"].get(c, "") for c in settings["addresses"]}}
    body["addresses"][coin] = address
    r = requests.put(f"{API}/admin/settings", json=body, headers=_h(tok), timeout=30)
    assert r.status_code == 200, r.text


def test_btc_e2e_auto_credit(admin_tok, buyer_tok, real_btc_tx):
    txid, address, sats = real_btc_tx
    print(f"\n[e2e] using BTC tx={txid} addr={address} sats={sats}")

    # Save existing BTC address + buyer balance to restore after
    s = _get_settings(admin_tok)
    orig_btc = s["addresses"].get("BTC", "")
    me = requests.get(f"{API}/auth/me", headers=_h(buyer_tok), timeout=30).json()
    buyer_id = me["id"]
    bal_before = me["balance_cents"]

    try:
        _put_addr(admin_tok, s, "BTC", address)

        # Create deposit (expected USD doesn't need to match - credited uses received*price)
        r = requests.post(f"{API}/wallet/deposits",
                          json={"coin": "BTC", "amount": 1.0},
                          headers=_h(buyer_tok), timeout=30)
        assert r.status_code == 200, r.text
        did = r.json()["id"]

        # Submit the real txid
        r2 = requests.post(f"{API}/wallet/deposits/{did}/txid",
                           json={"txid": txid}, headers=_h(buyer_tok), timeout=30)
        assert r2.status_code == 200, r2.text
        assert r2.json().get("chain", {}).get("state") in ("searching", "credited", "confirming")

        # Poll up to ~45s for auto-credit (verify_now runs immediately async)
        credited = None
        for i in range(15):
            time.sleep(3)
            w = requests.get(f"{API}/wallet", headers=_h(buyer_tok), timeout=30).json()
            dep = next((x for x in w["deposits"] if x["id"] == did), None)
            if dep and dep.get("status") == "approved":
                credited = dep
                break
            # also allow manual recheck via admin recheck endpoint midway
            if i == 5:
                try:
                    requests.post(f"{API}/admin/deposits/{did}/recheck", headers=_h(admin_tok), timeout=60)
                except Exception:
                    pass
        assert credited, f"Deposit did not auto-credit within timeout; last dep={dep}"
        assert credited["auto"] is True
        assert credited["chain"]["state"] == "credited"
        assert credited["credited_cents"] > 0
        price = float(credited["chain"]["usd_price"])
        received = float(credited["chain"]["received"])
        expected_cents = int(received * price * 100)
        assert abs(credited["credited_cents"] - expected_cents) <= 2, \
            f"credited_cents mismatch: {credited['credited_cents']} vs {expected_cents}"

        # Balance increased
        bal_after = requests.get(f"{API}/auth/me", headers=_h(buyer_tok), timeout=30).json()["balance_cents"]
        assert bal_after - bal_before == credited["credited_cents"]

        # Audit log contains deposit.auto_approve
        audits = requests.get(f"{API}/admin/audit", headers=_h(admin_tok), timeout=30)
        if audits.status_code == 200:
            assert any(a.get("action") == "deposit.auto_approve" and a.get("target_id") == did
                       for a in audits.json()), "deposit.auto_approve audit missing"

        # Approved deposits no longer in pending queue
        pend = requests.get(f"{API}/admin/deposits?status=pending", headers=_h(admin_tok), timeout=30).json()
        assert not any(d["id"] == did for d in pend)

        # Debit back the credited amount
        debit = -credited["credited_cents"] / 100.0
        adj = requests.post(f"{API}/admin/users/{buyer_id}/adjust",
                            json={"amount": debit, "reason": "TEST iter12 e2e cleanup"},
                            headers=_h(admin_tok), timeout=30)
        assert adj.status_code == 200, adj.text
        bal_restored = requests.get(f"{API}/auth/me", headers=_h(buyer_tok), timeout=30).json()["balance_cents"]
        assert bal_restored == bal_before
    finally:
        # Always restore original BTC address
        s_now = _get_settings(admin_tok)
        _put_addr(admin_tok, s_now, "BTC", orig_btc)


# ---- Mismatch + recheck + manual approve ---------------------------
def test_mismatch_and_recheck_and_manual_approve(admin_tok, buyer_tok, real_btc_txs):
    """Create a BTC deposit against an address that the txid does NOT pay.
    Expect chain.state=mismatch and status stays pending. Then test recheck
    and manual approve on a fresh pending deposit."""
    txid, _real_addr, _sats = real_btc_txs[1]  # use the second tx (first is consumed by e2e)

    s = _get_settings(admin_tok)
    orig_btc = s["addresses"].get("BTC", "")
    # A valid BTC address that is extremely unlikely to appear in a random tx
    unused_addr = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"  # BIP173 test vector addr

    try:
        _put_addr(admin_tok, s, "BTC", unused_addr)

        r = requests.post(f"{API}/wallet/deposits",
                          json={"coin": "BTC", "amount": 1.0},
                          headers=_h(buyer_tok), timeout=30)
        assert r.status_code == 200
        did = r.json()["id"]
        # Use the real txid - it pays a different address
        r2 = requests.post(f"{API}/wallet/deposits/{did}/txid",
                           json={"txid": txid}, headers=_h(buyer_tok), timeout=30)
        assert r2.status_code == 200, r2.text

        # Allow verify_now to run
        time.sleep(4)
        rc = requests.post(f"{API}/admin/deposits/{did}/recheck", headers=_h(admin_tok), timeout=60)
        assert rc.status_code == 200, rc.text
        dep = rc.json()
        assert dep["status"] == "pending", f"status should remain pending, got {dep['status']}"
        assert dep["chain"]["state"] == "mismatch"
        assert dep["chain"].get("final") is True
        assert dep["chain"].get("error")

        # Appears in admin pending queue
        pend = requests.get(f"{API}/admin/deposits?status=pending", headers=_h(admin_tok), timeout=30).json()
        assert any(d["id"] == did for d in pend), "mismatch deposit should remain in pending queue"

        # Manual reject sets chain.final (already True) and status=rejected
        rj = requests.post(f"{API}/admin/deposits/{did}/reject",
                           json={"reason": "TEST iter12 mismatch reject"},
                           headers=_h(admin_tok), timeout=30)
        assert rj.status_code == 200
        assert rj.json()["status"] == "rejected"
        assert rj.json()["chain"]["final"] is True

        # ---- Manual approve path: fresh deposit, bogus txid stays searching, admin approves ----
        r3 = requests.post(f"{API}/wallet/deposits",
                           json={"coin": "BTC", "amount": 1.0},
                           headers=_h(buyer_tok), timeout=30)
        did2 = r3.json()["id"]
        fake_txid = secrets.token_hex(32)  # 64 hex chars; not found on-chain
        r4 = requests.post(f"{API}/wallet/deposits/{did2}/txid",
                           json={"txid": fake_txid}, headers=_h(buyer_tok), timeout=30)
        assert r4.status_code == 200
        time.sleep(4)
        me_before = requests.get(f"{API}/auth/me", headers=_h(buyer_tok), timeout=30).json()["balance_cents"]
        appr = requests.post(f"{API}/admin/deposits/{did2}/approve",
                             json={"amount": 1.0}, headers=_h(admin_tok), timeout=30)
        assert appr.status_code == 200, appr.text
        body = appr.json()
        assert body["status"] == "approved"
        assert body["chain"]["final"] is True
        assert body.get("auto") is not True  # manual approve, not auto
        me_after = requests.get(f"{API}/auth/me", headers=_h(buyer_tok), timeout=30).json()["balance_cents"]
        assert me_after - me_before == 100

        # Cleanup: debit the $1 back
        requests.post(f"{API}/admin/users/{body['user_id']}/adjust",
                      json={"amount": -1.0, "reason": "TEST iter12 cleanup"},
                      headers=_h(admin_tok), timeout=30)
    finally:
        s_now = _get_settings(admin_tok)
        _put_addr(admin_tok, s_now, "BTC", orig_btc)
