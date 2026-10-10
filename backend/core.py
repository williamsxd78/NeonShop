from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import re
import uuid
import asyncio
import logging
import ipaddress
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse
from datetime import datetime, timezone, timedelta

import bcrypt
import jwt
import httpx
import requests
from fastapi import Request, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger("market")

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

JWT_ALGORITHM = "HS256"
APP_NAME = os.environ["APP_NAME"]

CATEGORIES = ["Software Licenses", "Templates", "Digital Assets", "Subscriptions", "Courses"]
COINS = {
    "BTC": {"label": "Bitcoin (BTC)", "network": "Bitcoin", "warning": "Send only BTC on the Bitcoin network. Other assets sent here are lost."},
    "USDT_TRC20": {"label": "Tether (USDT)", "network": "TRC20 (Tron)", "warning": "Send ONLY USDT via the TRC20 (Tron) network. Sending USDT on ERC20, BEP20 or any other network will result in permanent loss."},
    "USDT_BEP20": {"label": "Tether (USDT)", "network": "BEP20 (BNB Smart Chain)", "warning": "Send ONLY USDT via the BEP20 (BNB Smart Chain) network. Sending on TRC20, ERC20 or any other network will result in permanent loss."},
    "LTC": {"label": "Litecoin (LTC)", "network": "Litecoin", "warning": "Send only LTC on the Litecoin network. Other assets sent here are lost."},
    "ETH": {"label": "Ethereum (ETH)", "network": "ERC20 (Ethereum mainnet)", "warning": "Send only native ETH on Ethereum mainnet. Do not send from L2s or other EVM chains."},
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


def to_cents(amount: float) -> int:
    return int(round(amount * 100))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email, "type": "access",
               "exp": datetime.now(timezone.utc) + timedelta(days=1)}
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=JWT_ALGORITHM)


def public_user(u: dict) -> dict:
    return {k: v for k, v in u.items() if k not in ("_id", "password_hash")}


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    if payload.get("type") != "access":
        raise HTTPException(401, "Invalid token type")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(401, "User not found")
    if user.get("status") == "suspended":
        raise HTTPException(403, "Account suspended")
    return user


def require_role(*roles):
    async def dep(user: dict = Depends(get_current_user)):
        if user["role"] not in roles:
            raise HTTPException(403, "Forbidden")
        return user
    return dep


async def require_approved_vendor(user: dict = Depends(require_role("vendor", "admin"))):
    if user["role"] == "vendor" and user.get("vendor_status") != "approved":
        raise HTTPException(403, "Vendor account not approved yet")
    return user


async def audit(actor: dict, action: str, target_id: str = None, amount_cents: int = None,
                user_id: str = None, details: str = ""):
    await db.audit_logs.insert_one({
        "id": new_id(), "actor_id": actor.get("id"), "actor_email": actor.get("email"),
        "action": action, "target_id": target_id, "user_id": user_id,
        "amount_cents": amount_cents, "details": details, "created_at": now_iso(),
    })


async def notify(user_id: str, title: str, body: str, email_subject: str = None):
    await db.notifications.insert_one({"id": new_id(), "user_id": user_id, "title": title,
                                       "body": body, "read": False, "created_at": now_iso()})
    if email_subject:
        user = await db.users.find_one({"id": user_id}, {"_id": 0, "email": 1, "name": 1})
        if user:
            asyncio.create_task(_safe_send(user, email_subject, title, body))


DEFAULT_NOTICE = {"enabled": True, "tone": "amber", "title": "All sales final",
                  "body": "Keys are delivered instantly and are non-refundable. Disputes are reviewed by admin and resolved via wallet credit.",
                  "highlight": "Every key is reserved atomically — never sold twice."}


HERO_IMAGE = "/assets/hero.jpeg"
BANNER_IMAGE = "/assets/banner.jpeg"
DEFAULT_HERO = {"enabled": True, "title": "MARKETPLACE", "subtitle": "{count} Products Available", "image": HERO_IMAGE}
DEFAULT_BANNERS = [{"id": "welcome", "enabled": True, "title": "Verified vendors, instant delivery",
                    "subtitle": "Top up with crypto and get your keys in seconds.", "button_text": "Browse vendors",
                    "link": "/vendors", "image": BANNER_IMAGE}]
DEFAULT_CATEGORY_STYLE = {"Software Licenses": {"icon": "key", "color": "#22D3EE"},
                          "Templates": {"icon": "layout", "color": "#A855F7"},
                          "Digital Assets": {"icon": "gem", "color": "#4ADE80"},
                          "Subscriptions": {"icon": "repeat", "color": "#FFB800"},
                          "Courses": {"icon": "graduation", "color": "#FF2A5F"}}


DEFAULT_THEME = {"brand": "#22C55E", "brandlt": "#4ADE80", "info": "#22D3EE", "ink": "#0A0B0B",
                 "panel": "#171A19", "surface": "#121413", "deep": "#0E100F", "line": "#272B29"}
DEFAULT_BRAND = {"name_start": "Card", "name_end": "Wizard", "icon": "sparkles", "page_title": "CardWizard – Gift Cards & Digital Goods",
                 "official_store": "CardWizard Official"}
DEFAULT_FOOTER = {"text": "© 2026 CardWizard · Gift cards & digital goods · Instant delivery", "columns": [
    {"title": "Marketplace", "links": [{"label": "Shop", "url": "/"}, {"label": "Vendors", "url": "/vendors"},
                                       {"label": "Become a vendor", "url": "/vendor/register"}]},
    {"title": "Account", "links": [{"label": "Wallet", "url": "/wallet"}, {"label": "Key vault", "url": "/vault"},
                                   {"label": "Orders", "url": "/orders"}]},
    {"title": "Help", "links": [{"label": "Support", "url": "/support"}, {"label": "Notifications", "url": "/notifications"}]}]}
FONT_CHOICES = {
    "heading": ["Outfit", "Space Grotesk", "Sora", "Syne", "Unbounded", "Chakra Petch", "Orbitron", "Rajdhani", "Exo 2", "Lexend", "Poppins", "Montserrat", "Bricolage Grotesque", "Playfair Display", "Bebas Neue"],
    "body": ["Manrope", "Inter", "DM Sans", "Plus Jakarta Sans", "Nunito Sans", "Figtree", "Work Sans", "Rubik", "Karla", "IBM Plex Sans", "Source Sans 3", "Lato", "Open Sans", "Outfit", "Sora", "Rajdhani", "Exo 2"],
    "mono": ["JetBrains Mono", "IBM Plex Mono", "Fira Code", "Space Mono", "Roboto Mono", "Source Code Pro", "DM Mono", "Share Tech Mono"],
}
DEFAULT_FONTS = {"heading": "Outfit", "body": "Manrope", "mono": "JetBrains Mono"}
BUILTIN_SECTIONS = ["hero", "banners", "notice", "vendors", "products"]
DEFAULT_SECTIONS = [{"id": t, "type": t, "enabled": True} for t in BUILTIN_SECTIONS]


DEFAULT_AUTO_VERIFY = {"BTC": 2, "USDT_TRC20": 20, "USDT_BEP20": 15, "LTC": 6, "ETH": 12}


async def get_settings() -> dict:
    s = await db.settings.find_one({"key": "global"}, {"_id": 0})
    s.setdefault("categories", list(CATEGORIES))
    s["notice"] = {**DEFAULT_NOTICE, "starts_at": None, "ends_at": None, **(s.get("notice") or {})}
    s["hero"] = {**DEFAULT_HERO, **(s.get("hero") or {})}
    s.setdefault("banners", DEFAULT_BANNERS)
    s["theme"] = {**DEFAULT_THEME, **(s.get("theme") or {})}
    s["brand"] = {**DEFAULT_BRAND, **(s.get("brand") or {})}
    s["fonts"] = {**DEFAULT_FONTS, **(s.get("fonts") or {})}
    s.setdefault("footer", DEFAULT_FOOTER)
    s.setdefault("sections", DEFAULT_SECTIONS)
    s.setdefault("guest_lock", False)
    av = s.get("auto_verify") or {}
    s["auto_verify"] = {c: {"enabled": True, "confirmations": n, **(av.get(c) or {})} for c, n in DEFAULT_AUTO_VERIFY.items()}
    style = s.get("category_style") or {}
    s["category_style"] = {c: style.get(c) or DEFAULT_CATEGORY_STYLE.get(c) or {"icon": "package", "color": "#22C55E"}
                           for c in s["categories"]}
    return s


# ---------------- Email (EMAIL_PROVIDER: emergent | resend | none) ----------------
EMAIL_PROVIDER = os.environ["EMAIL_PROVIDER"]
EMAIL_BASE_URL = "https://integrations.emergentagent.com"
EMAIL_FROM_NAME = os.environ["EMAIL_FROM_NAME"]
EMAIL_REPLY_TO = os.environ.get("EMAIL_REPLY_TO")

_SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "goo.gl", "rebrand.ly")
_CRED_ASK = ("reply with your password", "reply with the code", "send your password", "cvv",
             "send us your password", "enter your password below", "confirm your card number",
             "your full card number", "seed phrase", "recovery phrase", "verify your card",
             "social security number", "confirm your bank details")
_HOSTISH = re.compile(r"\b(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})", re.I)


def _host_ok(host: str) -> bool:
    if not host or "xn--" in host:
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    return not any(host == s or host.endswith("." + s) for s in _SHORTENERS)


def _same_site(shown: str, real: str) -> bool:
    return shown == real or real.endswith("." + shown) or shown.endswith("." + real)


class _EmailScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.urls, self.anchors = set(), [], []
        self._href, self._text = None, []

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag.lower())
        self.urls += [v for k, v in attrs if k.lower() in ("href", "src") and v]
        if tag.lower() == "a":
            self._href = dict((k.lower(), v) for k, v in attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text)))
            self._href, self._text = None, []


def _assert_safe_email(subject: str, html: str) -> None:
    scan = _EmailScan()
    scan.feed(html)
    if scan.tags & {"form", "input", "textarea", "select"}:
        raise ValueError("No forms or input fields in email (G2)")
    body = f"{subject}\n{html}".lower()
    for p in _CRED_ASK:
        if p in body:
            raise ValueError(f"Email asks the recipient for credentials: {p!r} (G2)")
    for url in scan.urls:
        low = url.strip().lower()
        if low.startswith(("mailto:", "tel:", "cid:", "#")):
            continue
        if not low.startswith("https://"):
            raise ValueError(f"Email links/assets must be absolute https: {url!r} (G3)")
        host = urlparse(low).hostname or ""
        if not _host_ok(host) or urlparse(low).username is not None:
            raise ValueError(f"Shortened, numeric-host or credential-bearing URL: {url!r} (G3)")
    for href, text in scan.anchors:
        real = urlparse(href.strip().lower()).hostname or ""
        if not real:
            continue
        for m in _HOSTISH.finditer(text):
            if not _same_site(m.group(1).lower(), real):
                raise ValueError(f"Anchor text {m.group(1)!r} != real link host {real!r} (G3)")


async def send_email(*, to: str, subject: str, html: str):
    _assert_safe_email(subject, html)
    if EMAIL_PROVIDER == "none":
        return None
    if EMAIL_PROVIDER == "resend":
        payload = {"from": os.environ["EMAIL_FROM"], "to": [to], "subject": subject, "html": html}
        if EMAIL_REPLY_TO:
            payload["reply_to"] = EMAIL_REPLY_TO
        url, headers = "https://api.resend.com/emails", {"Authorization": f"Bearer {os.environ['RESEND_API_KEY']}"}
    else:
        payload = {"to": [to], "subject": subject, "html": html, "from_name": EMAIL_FROM_NAME}
        if EMAIL_REPLY_TO:
            payload["contact_email"] = EMAIL_REPLY_TO
        url, headers = f"{EMAIL_BASE_URL}/api/v1/email/send", {"X-Email-Key": os.environ["EMERGENT_EMAIL_KEY"]}
    async with httpx.AsyncClient(timeout=30) as c:
        resp = await c.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json().get("id")


def _template(name: str, title: str, body: str) -> str:
    return (f'<table role="presentation" width="100%" style="background:#07080C"><tr><td style="padding:28px;'
            f'font-family:Arial,sans-serif;color:#F1F5F9">'
            f'<h2 style="color:#00F0FF;margin:0 0 12px">{escape(title)}</h2>'
            f'<p>Hi {escape(name)},</p><p>{escape(body)}</p>'
            f'<p>Sign in to your account to view details.</p>'
            f'<p style="font-size:12px;color:#64748B">Sent by {escape(EMAIL_FROM_NAME)}. We never ask for '
            f'your password or payment details by email.</p></td></tr></table>')


async def _safe_send(user: dict, subject: str, title: str, body: str):
    try:
        await send_email(to=user["email"], subject=f"{EMAIL_FROM_NAME}: {subject}",
                         html=_template(user.get("name") or "there", title, body))
    except Exception as e:
        logger.warning(f"Email send failed for {user.get('email')}: {e}")


# ---------------- Object Storage (STORAGE_MODE: emergent | local) ----------------
STORAGE_MODE = os.environ["STORAGE_MODE"]
LOCAL_DIR = Path(os.environ["LOCAL_STORAGE_DIR"]) if STORAGE_MODE == "local" else None
STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
_storage_key = None


def init_storage(force: bool = False):
    global _storage_key
    if STORAGE_MODE == "local":
        LOCAL_DIR.mkdir(parents=True, exist_ok=True)
        return None
    if _storage_key and not force:
        return _storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": os.environ["EMERGENT_LLM_KEY"]}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    return _storage_key


def _local_path(path: str) -> Path:
    full = (LOCAL_DIR / path).resolve()
    if not str(full).startswith(str(LOCAL_DIR.resolve()) + os.sep):
        raise HTTPException(400, "Invalid path")
    return full


def put_object(path: str, data: bytes, content_type: str) -> dict:
    if STORAGE_MODE == "local":
        full = _local_path(path)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(data)
        return {"path": path, "size": len(data)}
    resp = requests.put(f"{STORAGE_URL}/objects/{path}",
                        headers={"X-Storage-Key": init_storage(), "Content-Type": content_type},
                        data=data, timeout=120)
    resp.raise_for_status()
    return resp.json()


def get_object(path: str):
    if STORAGE_MODE == "local":
        import mimetypes
        full = _local_path(path)
        if not full.is_file():
            raise HTTPException(404, "File not found")
        return full.read_bytes(), mimetypes.guess_type(full.name)[0] or "application/octet-stream"
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": init_storage()}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")
