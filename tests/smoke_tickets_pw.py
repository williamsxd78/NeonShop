import io, sys, uuid, requests
sys.path.insert(0, "/app/backend/tests")
from backend_test import _solve_captcha  # noqa

API = open("/app/frontend/.env").read().split("REACT_APP_BACKEND_URL=")[1].split()[0].strip('"') + "/api"
PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082")


def login(e, p):
    r = requests.post(f"{API}/auth/login", json={"email": e, "password": p, **_solve_captcha()})
    return r


def H(t):
    return {"Authorization": f"Bearer {t}"}


em = f"test_pw_{uuid.uuid4().hex[:6]}@market.com"
r = requests.post(f"{API}/auth/register", json={"email": em, "password": "Start@123", "name": "PW", "role": "buyer", **_solve_captcha()})
tok = r.json()["token"]
assert requests.post(f"{API}/auth/change-password", json={"current_password": "bad", "new_password": "Newpass@1"}, headers=H(tok)).status_code == 400
assert requests.post(f"{API}/auth/change-password", json={"current_password": "Start@123", "new_password": "short"}, headers=H(tok)).status_code == 422
assert requests.post(f"{API}/auth/change-password", json={"current_password": "Start@123", "new_password": "Newpass@1"}, headers=H(tok)).status_code == 200
assert login(em, "Start@123").status_code == 401
tok = login(em, "Newpass@1").json()["token"]
print("password change OK")

up = requests.post(f"{API}/tickets/upload", files={"file": ("a.png", io.BytesIO(PNG), "image/png")}, headers=H(tok))
assert up.status_code == 200, up.text
path = up.json()["path"]
assert requests.post(f"{API}/tickets/upload", files={"file": ("a.txt", io.BytesIO(b"x"), "text/plain")}, headers=H(tok)).status_code == 400
assert requests.get(f"{API}/files/{path}").status_code == 404
assert requests.post(f"{API}/tickets", json={"subject": "Proof", "message": "", "attachments": []}, headers=H(tok)).status_code == 400
t = requests.post(f"{API}/tickets", json={"subject": "Proof", "message": "", "attachments": [path]}, headers=H(tok)).json()
assert t["messages"][0]["attachments"] == [path]
assert requests.get(f"{API}/tickets/files/{path}", headers=H(tok)).content == PNG
assert requests.get(f"{API}/tickets/files/{path}").status_code == 401
adm = login("admin@market.com", "Admin@123").json()["token"]
assert requests.get(f"{API}/tickets/files/{path}", headers=H(adm)).status_code == 200
buyer = login("buyer@market.com", "Buyer@123").json()["token"]
assert requests.get(f"{API}/tickets/files/{path}", headers=H(buyer)).status_code == 403
assert requests.post(f"{API}/tickets/{t['id']}/messages", json={"message": "x", "attachments": [path]}, headers=H(buyer)).status_code == 404
print("attachments OK")

c = requests.get(f"{API}/admin/canned-replies", headers=H(adm)).json()
assert len(c) >= 5 and c[0]["title"] == "Deposit delay"
assert requests.get(f"{API}/admin/canned-replies", headers=H(buyer)).status_code == 403
saved = requests.put(f"{API}/admin/canned-replies", json={"replies": c + [{"title": "TEST_x", "text": "hello {name}"}]}, headers=H(adm)).json()
assert saved[-1]["title"] == "TEST_x"
requests.put(f"{API}/admin/canned-replies", json={"replies": c}, headers=H(adm))
ap = requests.post(f"{API}/tickets/upload", files={"file": ("b.png", io.BytesIO(PNG), "image/png")}, headers=H(adm)).json()["path"]
rr = requests.post(f"{API}/tickets/{t['id']}/messages", json={"message": "see", "attachments": [ap]}, headers=H(adm))
assert rr.status_code == 200
assert requests.get(f"{API}/tickets/files/{ap}", headers=H(tok)).status_code == 200
print("canned + admin attachment OK")
