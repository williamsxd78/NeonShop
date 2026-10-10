"""Backend tests for guest_lock feature."""
import os
import re
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://wallet-goods.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def solve(q):
    m = re.match(r"(-?\d+)\s*([+\-×])\s*(-?\d+)", q)
    a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
    return {"+": a + b, "-": a - b, "×": a * b}[op]


def login(email, password):
    s = requests.Session()
    cap = s.get(f"{API}/auth/captcha").json()
    r = s.post(f"{API}/auth/login", json={
        "email": email, "password": password,
        "captcha_id": cap["captcha_id"], "captcha_answer": str(solve(cap["question"])),
    })
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def admin_token():
    return login("admin@market.com", "Admin@123")


def test_get_site_contains_guest_lock():
    r = requests.get(f"{API}/site")
    assert r.status_code == 200
    assert "guest_lock" in r.json()


def test_admin_toggle_guest_lock(admin_token):
    h = {"Authorization": f"Bearer {admin_token}"}
    # turn ON
    r = requests.put(f"{API}/admin/site", json={"guest_lock": True}, headers=h)
    assert r.status_code == 200
    assert requests.get(f"{API}/site").json()["guest_lock"] is True
    # turn OFF
    r = requests.put(f"{API}/admin/site", json={"guest_lock": False}, headers=h)
    assert r.status_code == 200
    assert requests.get(f"{API}/site").json()["guest_lock"] is False
    # Set back to ON for subsequent UI tests (will reset at end)
    requests.put(f"{API}/admin/site", json={"guest_lock": True}, headers=h)


def test_buyer_login():
    tok = login("buyer@market.com", "Buyer@123")
    assert tok
