import os
import re
import json
import uuid
import secrets
import asyncio
from typing import Optional, Literal, Dict, List

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, UploadFile, File, Query
from fastapi.responses import Response
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from datetime import datetime, timezone, timedelta

import chain
from core import (db, client, logger, CATEGORIES, COINS, APP_NAME, now_iso, new_id, to_cents,
                  hash_password, verify_password, create_access_token, public_user, get_current_user,
                  require_role, require_approved_vendor, audit, notify, get_settings,
                  init_storage, put_object, get_object, BUILTIN_SECTIONS, FONT_CHOICES)
from seed import seed_all, IMG as DEFAULT_IMAGES

app = FastAPI()
api = APIRouter(prefix="/api")
admin_dep = require_role("admin")


# ---------------- Schemas ----------------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=1, max_length=80)
    role: Literal["buyer", "vendor"] = "buyer"
    store_name: Optional[str] = None
    captcha_id: str
    captcha_answer: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    captcha_id: str
    captcha_answer: str


class ProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class ProductIn(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=4000)
    category: str = Field(min_length=1, max_length=40)
    price: float = Field(gt=0, le=100000)
    image: Optional[str] = None
    tags: List[str] = Field(default_factory=list, max_length=8)
    delivery_type: Literal["keys", "content"] = "keys"
    delivery_content: str = Field(default="", max_length=10000)


def clean_tags(tags):
    return list(dict.fromkeys(t.strip().lower()[:24] for t in tags if t.strip()))[:8]


def default_image(cat: str) -> str:
    return DEFAULT_IMAGES.get(cat) or next(iter(DEFAULT_IMAGES.values()))


async def check_category(cat: str):
    if cat not in (await get_settings())["categories"]:
        raise HTTPException(400, "Unknown category")


def product_fields(body: ProductIn) -> dict:
    if body.delivery_type == "content" and not body.delivery_content.strip():
        raise HTTPException(400, "Delivery content is required for 'same content for every buyer' products")
    return {"title": body.title, "description": body.description, "category": body.category,
            "price_cents": to_cents(body.price), "vendor_price_cents": to_cents(body.price),
            "image": body.image or default_image(body.category), "tags": clean_tags(body.tags),
            "delivery_type": body.delivery_type, "delivery_content": body.delivery_content.strip()}


PUBLIC_PRODUCT = {"_id": 0, "delivery_content": 0}


class BulkIn(BaseModel):
    text: str = Field(min_length=1, max_length=3_000_000)
    separator: str = Field(default="dashes", max_length=60)
    public_lines: List[int] = Field(default_factory=list, max_length=100)
    title_line: Optional[int] = None
    title_lines: List[int] = Field(default_factory=list, max_length=3)
    title_prefix: str = Field(default="Item", max_length=80)
    deliver: Literal["all", "hidden"] = "all"
    category: str = Field(min_length=1, max_length=40)
    price: float = Field(gt=0, le=100000)
    image: Optional[str] = None
    tags: List[str] = Field(default_factory=list, max_length=8)


def split_blocks(text: str, sep: str) -> List[List[str]]:
    if sep == "blank":
        parts = re.split(r"\n\s*\n", text)
    elif sep == "dashes":
        parts = re.split(r"(?m)^\s*-{3,}\s*$", text)
    else:
        parts = re.split(r"(?m)^\s*" + re.escape(sep.strip()) + r"\s*$", text)
    blocks = [[f for ln in part.splitlines() for f in split_fields(ln.strip()) if f] for part in parts]
    return [b for b in blocks if b]


LABEL_RE = re.compile(r"^([A-Za-z][\w'’ ]{0,29}?)\s*:\s*(.+)$")
FIELD_SPLIT_RE = re.compile(r"\s+(?=[A-Z][\w'’]*(?:\s[a-z][\w'’]*)?\s*:\s)")


def split_fields(line: str) -> List[str]:
    if not LABEL_RE.match(line):
        return [line]
    return [f.strip() for f in FIELD_SPLIT_RE.split(line) if f.strip()]


def field_value(field: str) -> str:
    m = LABEL_RE.match(field)
    return m.group(2).strip() if m else field


class KeysIn(BaseModel):
    keys: str


class DepositIn(BaseModel):
    coin: Literal["BTC", "USDT_TRC20", "USDT_BEP20", "LTC", "ETH"]
    amount: float = Field(ge=1, le=1000000)


class TxIn(BaseModel):
    txid: str = Field(min_length=8, max_length=200)


class WithdrawIn(BaseModel):
    amount: float = Field(ge=1)
    coin: Literal["BTC", "USDT_TRC20", "USDT_BEP20", "LTC", "ETH"]
    address: str = Field(min_length=10, max_length=200)


class ReasonIn(BaseModel):
    reason: str = Field(min_length=2, max_length=500)


class ApproveDepositIn(BaseModel):
    amount: Optional[float] = Field(default=None, gt=0)


class PayIn(BaseModel):
    payout_txid: Optional[str] = None


class PriceIn(BaseModel):
    price: float = Field(gt=0, le=100000)


class ApproveProductIn(BaseModel):
    price: Optional[float] = Field(default=None, gt=0)


class CommissionIn(BaseModel):
    pct: float = Field(ge=0, le=100)


class VendorCommissionIn(BaseModel):
    pct: Optional[float] = Field(default=None, ge=0, le=100)


class AutoVerifyIn(BaseModel):
    enabled: bool
    confirmations: int = Field(ge=1, le=500)


class SettingsIn(BaseModel):
    commission_pct: Optional[float] = Field(default=None, ge=0, le=100)
    addresses: Optional[Dict[str, str]] = None
    auto_verify: Optional[Dict[str, AutoVerifyIn]] = None


class NoticeIn(BaseModel):
    enabled: bool = True
    tone: Literal["amber", "green", "cyan", "red"] = "amber"
    title: str = Field(default="", max_length=80)
    body: str = Field(default="", max_length=600)
    highlight: str = Field(default="", max_length=200)
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    original: Optional[str] = None
    icon: str = Field(default="package", max_length=30)
    color: str = Field(default="#22C55E", pattern=r"^#[0-9A-Fa-f]{6}$")


SAFE_LINK = r"^(/[^\s]*|https?://[^\s]+)?$"


class HeroIn(BaseModel):
    enabled: bool = True
    title: str = Field(default="", max_length=60)
    subtitle: str = Field(default="", max_length=120)
    image: str = Field(min_length=1, max_length=600, pattern=SAFE_LINK)


class BannerIn(BaseModel):
    id: Optional[str] = None
    enabled: bool = True
    title: str = Field(default="", max_length=80)
    subtitle: str = Field(default="", max_length=200)
    button_text: str = Field(default="", max_length=30)
    link: str = Field(default="", max_length=500, pattern=SAFE_LINK)
    image: str = Field(min_length=1, max_length=600, pattern=SAFE_LINK)


HEX = r"^#[0-9A-Fa-f]{6}$"


class ThemeIn(BaseModel):
    brand: str = Field(pattern=HEX)
    brandlt: str = Field(pattern=HEX)
    info: str = Field(pattern=HEX)
    ink: str = Field(pattern=HEX)
    panel: str = Field(pattern=HEX)
    surface: str = Field(pattern=HEX)
    deep: str = Field(pattern=HEX)
    line: str = Field(pattern=HEX)


class FontsIn(BaseModel):
    heading: str
    body: str
    mono: str

    def check(self):
        for k in ("heading", "body", "mono"):
            if getattr(self, k) not in FONT_CHOICES[k]:
                raise HTTPException(400, f"Unsupported {k} font")


class BrandIn(BaseModel):
    name_start: str = Field(default="", max_length=30)
    name_end: str = Field(default="", max_length=30)
    icon: str = Field(default="zap", max_length=30)
    page_title: str = Field(min_length=1, max_length=70)
    official_store: str = Field(min_length=1, max_length=60)


class LinkIn(BaseModel):
    label: str = Field(min_length=1, max_length=40)
    url: str = Field(min_length=1, max_length=500, pattern=SAFE_LINK)


class FooterColIn(BaseModel):
    title: str = Field(default="", max_length=40)
    links: List[LinkIn] = Field(default_factory=list, max_length=10)


class FooterIn(BaseModel):
    text: str = Field(default="", max_length=200)
    columns: List[FooterColIn] = Field(default_factory=list, max_length=6)


class FeatureColIn(BaseModel):
    icon: str = Field(default="zap", max_length=30)
    title: str = Field(default="", max_length=60)
    text: str = Field(default="", max_length=300)


class SectionIn(BaseModel):
    id: Optional[str] = None
    type: Literal["hero", "banners", "notice", "vendors", "products", "text", "columns"]
    enabled: bool = True
    title: str = Field(default="", max_length=80)
    body: str = Field(default="", max_length=1500)
    image: str = Field(default="", max_length=600, pattern=SAFE_LINK)
    button_text: str = Field(default="", max_length=30)
    link: str = Field(default="", max_length=500, pattern=SAFE_LINK)
    columns: List[FeatureColIn] = Field(default_factory=list, max_length=6)


def clean_sections(items: List[SectionIn]) -> List[dict]:
    out, seen = [], set()
    for x in items:
        if x.type in BUILTIN_SECTIONS:
            if x.type in seen:
                continue
            seen.add(x.type)
            out.append({"id": x.type, "type": x.type, "enabled": x.enabled})
        else:
            out.append({**x.model_dump(), "id": x.id if x.id and x.id not in seen and x.id not in BUILTIN_SECTIONS else new_id()})
            seen.add(out[-1]["id"])
    out += [{"id": t, "type": t, "enabled": False} for t in BUILTIN_SECTIONS if t not in seen]
    return out


class SiteIn(BaseModel):
    theme: Optional[ThemeIn] = None
    fonts: Optional[FontsIn] = None
    brand: Optional[BrandIn] = None
    footer: Optional[FooterIn] = None
    sections: Optional[List[SectionIn]] = Field(default=None, max_length=30)
    notice: Optional[NoticeIn] = None
    categories: Optional[List[CategoryIn]] = Field(default=None, min_length=1, max_length=30)
    hero: Optional[HeroIn] = None
    banners: Optional[List[BannerIn]] = Field(default=None, max_length=12)


def notice_active(n: dict) -> bool:
    now = datetime.now(timezone.utc)
    def parse(v):
        d = datetime.fromisoformat(v) if v else None
        return d.replace(tzinfo=timezone.utc) if d and not d.tzinfo else d
    st, en = parse(n.get("starts_at")), parse(n.get("ends_at"))
    return bool(n.get("enabled")) and (not st or st <= now) and (not en or now < en)


class ManualDepositIn(BaseModel):
    email: EmailStr
    amount: float = Field(gt=0, le=1_000_000)
    coin: Literal["BTC", "USDT_TRC20", "USDT_BEP20", "LTC", "ETH", "OTHER"] = "OTHER"
    txid: Optional[str] = Field(default=None, max_length=200)
    note: str = Field(min_length=2, max_length=500)


class AdjustIn(BaseModel):
    amount: float
    reason: str = Field(min_length=2, max_length=500)


class StatusIn(BaseModel):
    status: Literal["active", "suspended"]


# ---------------- Auth ----------------
@api.get("/auth/captcha")
async def captcha():
    a, b = secrets.randbelow(9) + 1, secrets.randbelow(9) + 1
    op = secrets.choice(["+", "-", "×"])
    if op == "-" and b > a:
        a, b = b, a
    ans = a + b if op == "+" else a - b if op == "-" else a * b
    cid = new_id()
    await db.captchas.insert_one({"id": cid, "answer": str(ans),
                                  "expires_at": datetime.now(timezone.utc) + timedelta(minutes=10)})
    return {"captcha_id": cid, "question": f"{a} {op} {b} = ?"}


async def verify_captcha(cid: str, answer: str):
    c = await db.captchas.find_one_and_delete({"id": cid})
    exp = c and c["expires_at"].replace(tzinfo=timezone.utc)
    if not c or exp < datetime.now(timezone.utc) or c["answer"] != answer.strip():
        raise HTTPException(400, "Incorrect captcha answer. Please try again.")


@api.post("/auth/register")
async def register(body: RegisterIn):
    await verify_captcha(body.captcha_id, body.captcha_answer)
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Email already registered")
    user = {"id": new_id(), "email": email, "password_hash": hash_password(body.password),
            "name": body.name, "role": body.role, "balance_cents": 0, "status": "active",
            "created_at": now_iso()}
    if body.role == "vendor":
        user.update({"vendor_status": "pending", "store_name": body.store_name or body.name,
                     "earnings_cents": 0, "commission_pct": None})
    await db.users.insert_one(user)
    await audit(user, "user.register", user["id"], details=f"role={body.role}")
    return {"token": create_access_token(user["id"], email), "user": public_user(user)}


@api.post("/auth/login")
async def login(body: LoginIn, request: Request):
    await verify_captcha(body.captcha_id, body.captcha_answer)
    email = body.email.lower()
    ident = f"{request.client.host if request.client else 'x'}:{email}"
    att = await db.login_attempts.find_one({"identifier": ident})
    if att and att.get("count", 0) >= 5 and att.get("locked_until", "") > now_iso():
        raise HTTPException(429, "Too many failed attempts. Try again in 15 minutes.")
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user or not verify_password(body.password, user["password_hash"]):
        lock = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
        await db.login_attempts.update_one({"identifier": ident},
                                           {"$inc": {"count": 1}, "$set": {"locked_until": lock}}, upsert=True)
        raise HTTPException(401, "Invalid email or password")
    if user.get("status") == "suspended":
        raise HTTPException(403, "Account suspended")
    await db.login_attempts.delete_many({"identifier": ident})
    return {"token": create_access_token(user["id"], email), "user": public_user(user)}


@api.get("/auth/me")
async def me(user=Depends(get_current_user)):
    unread = await db.notifications.count_documents({"user_id": user["id"], "read": False})
    return {**user, "unread_notifications": unread}


@api.put("/auth/profile")
async def update_profile(body: ProfileIn, user=Depends(get_current_user)):
    await db.users.update_one({"id": user["id"]}, {"$set": {"name": body.name}})
    return {"ok": True}


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


@api.post("/auth/change-password")
async def change_password(body: ChangePasswordIn, user=Depends(get_current_user)):
    u = await db.users.find_one({"id": user["id"]})
    if not verify_password(body.current_password, u["password_hash"]):
        raise HTTPException(400, "Current password is incorrect")
    if body.current_password == body.new_password:
        raise HTTPException(400, "New password must be different")
    await db.users.update_one({"id": user["id"]}, {"$set": {"password_hash": hash_password(body.new_password),
                                                            "password_changed_at": now_iso()}})
    await audit(user, "auth.password_changed", user["id"], None, user["id"], "Password changed")
    await notify(user["id"], "Password changed", "Your account password was changed. If this wasn't you, contact support.")
    return {"ok": True}


# ---------------- Public catalog ----------------
@api.get("/categories")
async def categories():
    return (await get_settings())["categories"]


@api.get("/site")
async def site():
    s = await get_settings()
    return {"categories": s["categories"], "category_style": s["category_style"],
            "notice": {**s["notice"], "active": notice_active(s["notice"])}, "hero": s["hero"],
            "banners": [b for b in s["banners"] if b.get("enabled")],
            "theme": s["theme"], "fonts": s["fonts"], "brand": s["brand"], "footer": s["footer"],
            "sections": [x for x in s["sections"] if x.get("enabled")],
            "product_count": await db.products.count_documents({"status": "approved", **IN_STOCK})}


@api.get("/admin/site")
async def admin_get_site(user=Depends(admin_dep)):
    s = await get_settings()
    return {k: s[k] for k in ("categories", "category_style", "notice", "hero", "banners", "theme", "fonts", "brand", "footer", "sections")} | {"font_choices": FONT_CHOICES} | {"notice_active": notice_active(s["notice"])}


def parse_attrs(lines: List[str]) -> List[dict]:
    out = []
    for ln in lines:
        k, sep, v = ln.partition(":")
        if sep and 0 < len(k.strip()) <= 30 and v.strip() and len(v.strip()) <= 60:
            out.append({"k": k.strip().title(), "v": v.strip()})
    return out


IN_STOCK = {"$or": [{"delivery_type": "content"}, {"stock_count": {"$gt": 0}}]}


def base_query(category: str, vendor: str) -> dict:
    query = {"status": "approved", "$and": [IN_STOCK]}
    if vendor:
        query["vendor_id"] = vendor
    if category:
        query["category"] = category
    return query


@api.get("/products/facets")
async def product_facets(category: str = "", vendor: str = ""):
    facets: Dict[str, Dict[str, int]] = {}
    async for p in db.products.find({**base_query(category, vendor), "attrs.0": {"$exists": True}}, {"attrs": 1}):
        for a in p["attrs"]:
            facets.setdefault(a["k"], {}).setdefault(a["v"], 0)
            facets[a["k"]][a["v"]] += 1
    return [{"key": k, "values": sorted([{"value": v, "count": c} for v, c in vals.items()], key=lambda x: -x["count"])}
            for k, vals in facets.items() if 2 <= len(vals) <= 40]


@api.get("/products")
async def list_products(q: str = "", category: str = "", sort: str = "new", vendor: str = "", attrs: str = ""):
    query = base_query(category, vendor)
    if attrs:
        try:
            sel = {str(k): str(v) for k, v in json.loads(attrs).items() if v}
        except (ValueError, AttributeError):
            raise HTTPException(400, "Invalid attrs filter")
        if sel:
            query["attrs"] = {"$all": [{"$elemMatch": {"k": k, "v": v}} for k, v in sel.items()]}
    if q:
        query["$and"].append({"$or": [{"title": {"$regex": q, "$options": "i"}},
                        {"description": {"$regex": q, "$options": "i"}},
                        {"vendor_name": {"$regex": q, "$options": "i"}}]})
    sorts = {"new": [("approved_at", -1)], "popular": [("sales_count", -1)],
             "price_asc": [("price_cents", 1)], "price_desc": [("price_cents", -1)]}
    return await db.products.find(query, PUBLIC_PRODUCT).sort(sorts.get(sort, sorts["new"])).to_list(2000)


@api.get("/vendors")
async def public_vendors():
    vendors = await db.users.find({"role": "vendor", "vendor_status": "approved", "status": "active"},
                                  {"_id": 0, "id": 1, "store_name": 1, "name": 1, "created_at": 1}).to_list(500)
    stats = await db.products.aggregate([
        {"$match": {"status": "approved"}},
        {"$group": {"_id": "$vendor_id", "products": {"$sum": {"$cond": [{"$or": [{"$eq": ["$delivery_type", "content"]}, {"$gt": ["$stock_count", 0]}]}, 1, 0]}}, "sales": {"$sum": "$sales_count"},
                    "categories": {"$addToSet": "$category"}}}]).to_list(500)
    by = {s["_id"]: s for s in stats}
    out = [{**v, "products": by.get(v["id"], {}).get("products", 0), "sales": by.get(v["id"], {}).get("sales", 0),
            "categories": by.get(v["id"], {}).get("categories", [])} for v in vendors]
    return sorted(out, key=lambda v: (-v["sales"], -v["products"]))


@api.get("/products/{pid}")
async def get_product(pid: str):
    p = await db.products.find_one({"id": pid, "status": "approved"}, PUBLIC_PRODUCT)
    if not p:
        raise HTTPException(404, "Product not found")
    return p


# ---------------- Wallet / Deposits ----------------
@api.get("/wallet/coins")
async def wallet_coins(user=Depends(get_current_user)):
    s = await get_settings()
    return [{"code": c, **meta, "address": s["addresses"].get(c, "")} for c, meta in COINS.items()]


@api.get("/wallet")
async def wallet(user=Depends(get_current_user)):
    deposits = await db.deposits.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    txs = await db.audit_logs.find({"user_id": user["id"], "amount_cents": {"$ne": None}},
                                   {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"balance_cents": user["balance_cents"], "deposits": deposits, "transactions": txs}


@api.post("/wallet/deposits")
async def create_deposit(body: DepositIn, user=Depends(get_current_user)):
    s = await get_settings()
    address = s["addresses"].get(body.coin, "").strip()
    if not address:
        raise HTTPException(400, "Deposit address for this coin is not configured yet")
    dep = {"id": new_id(), "user_id": user["id"], "user_email": user["email"], "coin": body.coin,
           "network": COINS[body.coin]["network"], "address": address,
           "amount_cents": to_cents(body.amount), "reference": "DEP-" + secrets.token_hex(4).upper(),
           "status": "awaiting_txid", "created_at": now_iso()}
    await db.deposits.insert_one(dep)
    dep.pop("_id", None)
    return dep


@api.post("/wallet/deposits/{did}/txid")
async def submit_txid(did: str, body: TxIn, user=Depends(get_current_user)):
    txid = body.txid.strip().lower()
    try:
        res = await db.deposits.find_one_and_update(
            {"id": did, "user_id": user["id"], "status": "awaiting_txid"},
            {"$set": {"txid": txid, "status": "pending", "submitted_at": now_iso()}},
            projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    except DuplicateKeyError:
        raise HTTPException(400, "This transaction ID has already been submitted")
    if not res:
        raise HTTPException(400, "Deposit not found or TXID already submitted")
    if await chain.auto_cfg(res["coin"]):
        await db.deposits.update_one({"id": did}, {"$set": {"chain": {"state": "searching", "confirmations": 0}}})
        res["chain"] = {"state": "searching", "confirmations": 0}
        asyncio.create_task(chain.verify_now(did))
    return res


# ---------------- Orders ----------------
class OrderIn(BaseModel):
    product_id: str


@api.post("/orders")
async def create_order(body: OrderIn, user=Depends(get_current_user)):
    p = await db.products.find_one({"id": body.product_id, "status": "approved"}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Product not available")
    if p["vendor_id"] == user["id"]:
        raise HTTPException(400, "You cannot buy your own product")
    price = p["price_cents"]
    if user["balance_cents"] < price:
        raise HTTPException(400, "Insufficient wallet balance")
    order_id = new_id()
    uses_keys = p.get("delivery_type", "keys") == "keys"
    key = None
    if uses_keys:
        key = await db.license_keys.find_one_and_update(
            {"product_id": p["id"], "status": "available"},
            {"$set": {"status": "reserved", "order_id": order_id, "buyer_id": user["id"], "reserved_at": now_iso()}},
            sort=[("created_at", 1)], projection={"_id": 0}, return_document=ReturnDocument.AFTER)
        if not key:
            raise HTTPException(400, "Out of stock")
    debited = await db.users.find_one_and_update(
        {"id": user["id"], "balance_cents": {"$gte": price}}, {"$inc": {"balance_cents": -price}},
        projection={"_id": 0, "balance_cents": 1}, return_document=ReturnDocument.AFTER)
    if not debited:
        if key:
            await db.license_keys.update_one({"id": key["id"]}, {"$set": {"status": "available"},
                                                                   "$unset": {"order_id": "", "buyer_id": ""}})
        raise HTTPException(400, "Insufficient wallet balance")
    secret = (await db.products.find_one({"id": p["id"]}, {"_id": 0, "delivery_content": 1})).get("delivery_content", "")
    vendor = await db.users.find_one({"id": p["vendor_id"]}, {"_id": 0})
    s = await get_settings()
    pct = vendor.get("commission_pct") if vendor and vendor.get("commission_pct") is not None else s["commission_pct"]
    if vendor and vendor["role"] == "admin":
        pct = 100
    commission = int(round(price * pct / 100))
    earning = price - commission
    order = {"id": order_id, "buyer_id": user["id"], "buyer_email": user["email"], "product_id": p["id"],
             "delivery_type": p.get("delivery_type", "keys"),
             "product_title": p["title"], "category": p["category"], "image": p.get("image"),
             "vendor_id": p["vendor_id"], "vendor_name": p["vendor_name"], "price_cents": price,
             "commission_pct": pct, "commission_cents": commission, "vendor_earning_cents": earning,
             "key_id": key["id"] if key else None, "license_key": key["key"] if key else None,
             "delivery_content": secret, "status": "delivered", "created_at": now_iso()}
    await db.orders.insert_one(order)
    if key:
        await db.license_keys.update_one({"id": key["id"]}, {"$set": {"status": "sold", "sold_at": now_iso()}})
    await db.users.update_one({"id": p["vendor_id"]}, {"$inc": {"earnings_cents": earning}})
    await db.products.update_one({"id": p["id"]}, {"$inc": {"stock_count": -1 if key else 0, "sales_count": 1}})
    await audit(user, "order.purchase", order_id, -price, user["id"], f"{p['title']}")
    await audit(user, "vendor.earning", order_id, earning, p["vendor_id"],
                f"Sale of {p['title']} (commission {pct}% = ${commission / 100:.2f})")
    await notify(user["id"], "Order delivered", f"Your purchase of {p['title']} is in your vault.",
                 "Order confirmation")
    await notify(p["vendor_id"], "New sale", f"{p['title']} sold. ${earning / 100:.2f} credited to earnings.")
    order.pop("_id", None)
    return {"order": order, "balance_cents": debited["balance_cents"]}


@api.get("/orders")
async def my_orders(user=Depends(get_current_user)):
    return await db.orders.find({"buyer_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)


# ---------------- Notifications ----------------
@api.get("/notifications")
async def notifications(user=Depends(get_current_user)):
    return await db.notifications.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)


@api.post("/notifications/read-all")
async def read_all(user=Depends(get_current_user)):
    await db.notifications.update_many({"user_id": user["id"]}, {"$set": {"read": True}})
    return {"ok": True}


# ---------------- Files ----------------
ALLOWED_IMG = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif"}


@api.post("/upload")
async def upload(file: UploadFile = File(...), user=Depends(require_role("vendor", "admin"))):
    if file.content_type not in ALLOWED_IMG:
        raise HTTPException(400, "Only PNG, JPG, WEBP or GIF images allowed")
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(400, "Max 5MB")
    path = f"{APP_NAME}/uploads/{user['id']}/{uuid.uuid4()}.{ALLOWED_IMG[file.content_type]}"
    result = await asyncio.to_thread(put_object, path, data, file.content_type)
    await db.files.insert_one({"id": new_id(), "storage_path": result["path"], "original_filename": file.filename,
                               "content_type": file.content_type, "size": result.get("size"),
                               "owner_id": user["id"], "is_deleted": False, "created_at": now_iso()})
    return {"path": result["path"], "url": f"/api/files/{result['path']}"}


@api.get("/files/{path:path}")
async def serve_file(path: str):
    rec = await db.files.find_one({"storage_path": path, "is_deleted": False, "kind": {"$ne": "ticket"}})
    if not rec:
        raise HTTPException(404, "File not found")
    data, ctype = await asyncio.to_thread(get_object, path)
    return Response(content=data, media_type=rec.get("content_type", ctype),
                    headers={"Cache-Control": "public, max-age=86400"})


# ---------------- Vendor ----------------
@api.get("/vendor/stats")
async def vendor_stats(user=Depends(require_role("vendor", "admin"))):
    s = await get_settings()
    orders = await db.orders.find({"vendor_id": user["id"]}, {"_id": 0}).to_list(5000)
    return {"vendor_status": user.get("vendor_status"), "earnings_cents": user.get("earnings_cents", 0),
            "total_sales": len(orders), "gross_cents": sum(o["price_cents"] for o in orders),
            "net_cents": sum(o["vendor_earning_cents"] for o in orders),
            "commission_pct": user.get("commission_pct") if user.get("commission_pct") is not None else s["commission_pct"],
            "products": await db.products.count_documents({"vendor_id": user["id"]}),
            "live_products": await db.products.count_documents({"vendor_id": user["id"], "status": "approved"})}


@api.get("/vendor/products")
async def vendor_products(user=Depends(require_role("vendor", "admin"))):
    return await db.products.find({"vendor_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(5000)


async def store_name(user: dict) -> str:
    if user["role"] == "admin":
        return (await get_settings())["brand"]["official_store"]
    return user.get("store_name") or user["name"]


def listing_status(user: dict) -> dict:
    return {"status": "approved", "approved_at": now_iso()} if user["role"] == "admin" else {"status": "pending"}


@api.post("/vendor/products")
async def vendor_create_product(body: ProductIn, user=Depends(require_approved_vendor)):
    await check_category(body.category)
    p = {"id": new_id(), "vendor_id": user["id"], "vendor_name": await store_name(user),
         **product_fields(body), **listing_status(user), "stock_count": 0, "sales_count": 0, "created_at": now_iso()}
    await db.products.insert_one(p)
    p.pop("_id", None)
    await audit(user, "product.create", p["id"], details=f"{body.title} @ ${body.price:.2f}")
    return p


@api.put("/vendor/products/{pid}")
async def vendor_update_product(pid: str, body: ProductIn, user=Depends(require_approved_vendor)):
    await check_category(body.category)
    p = await db.products.find_one({"id": pid, "vendor_id": user["id"]}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Product not found")
    upd = {**product_fields(body), **listing_status(user), "updated_at": now_iso()}
    await db.products.update_one({"id": pid}, {"$set": upd})
    await audit(user, "product.update", pid, details=f"resubmitted for review @ ${body.price:.2f}")
    return {**p, **upd}


@api.post("/vendor/products/{pid}/keys")
async def vendor_add_keys(pid: str, body: KeysIn, user=Depends(require_approved_vendor)):
    p = await db.products.find_one({"id": pid, "vendor_id": user["id"]}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Product not found")
    keys = list(dict.fromkeys(k.strip() for k in body.keys.splitlines() if k.strip()))
    added = 0
    for k in keys:
        try:
            await db.license_keys.insert_one({"id": new_id(), "product_id": pid, "vendor_id": user["id"],
                                              "key": k, "status": "available", "created_at": now_iso()})
            added += 1
        except DuplicateKeyError:
            pass
    await db.products.update_one({"id": pid}, {"$inc": {"stock_count": added}})
    await audit(user, "product.keys_added", pid, details=f"{added} keys added")
    return {"added": added, "skipped": len(keys) - added}


@api.post("/vendor/products/bulk")
async def vendor_bulk_import(body: BulkIn, user=Depends(require_approved_vendor)):
    await check_category(body.category)
    blocks = split_blocks(body.text, body.separator)
    if not blocks:
        raise HTTPException(400, "No items found. Check the separator.")
    if len(blocks) > 2000:
        raise HTTPException(400, "Max 2000 items per import")
    pub = sorted(set(i for i in body.public_lines if i >= 0))
    items = []
    for b in blocks:
        hidden = [ln for i, ln in enumerate(b) if i not in pub]
        secret = "\n".join(hidden if body.deliver == "hidden" and hidden else b)
        items.append((b, secret))
    seen, existing = set(), set()
    async for k in db.license_keys.find({"vendor_id": user["id"], "key": {"$in": [x[1] for x in items]}}, {"key": 1}):
        existing.add(k["key"])
    batch_id, now, cents = new_id(), now_iso(), to_cents(body.price)
    vname = await store_name(user)
    products, keys, skipped = [], [], 0
    for n, (b, secret) in enumerate(items, 1):
        if secret in seen or secret in existing:
            skipped += 1
            continue
        seen.add(secret)
        tl = [i for i in (body.title_lines or ([body.title_line] if body.title_line is not None else [])) if 0 <= i < len(b)]
        preview = [b[i] for i in pub if i < len(b) and i not in tl]
        title = " · ".join(field_value(b[i]) for i in tl) or f"{body.title_prefix} #{n}"
        pid = new_id()
        products.append({"id": pid, "vendor_id": user["id"], "vendor_name": vname, "title": title[:120],
                         "description": "\n".join(preview), "preview_lines": preview, "attrs": parse_attrs(preview),
                         "category": body.category,
                         "price_cents": cents, "vendor_price_cents": cents,
                         "image": body.image or default_image(body.category), "tags": clean_tags(body.tags),
                         "delivery_type": "keys", "delivery_content": "", "batch_id": batch_id,
                         **listing_status(user), "stock_count": 1, "sales_count": 0, "created_at": now})
        keys.append({"id": new_id(), "product_id": pid, "vendor_id": user["id"], "key": secret,
                     "status": "available", "created_at": now})
    if products:
        await db.products.insert_many(products)
        await db.license_keys.insert_many(keys)
    await audit(user, "product.bulk_import", batch_id, details=f"{len(products)} items @ ${body.price:.2f}, {skipped} duplicates skipped")
    return {"batch_id": batch_id, "created": len(products), "skipped": skipped}


async def _delete_products(query: dict, actor: dict, label: str):
    pids = [p["id"] async for p in db.products.find(query, {"id": 1})]
    if not pids:
        raise HTTPException(404, "Product not found")
    await db.products.delete_many({"id": {"$in": pids}})
    k = await db.license_keys.delete_many({"product_id": {"$in": pids}, "status": "available"})
    await audit(actor, "product.delete", label, details=f"{len(pids)} product(s), {k.deleted_count} unsold keys removed")
    return {"deleted": len(pids), "keys_removed": k.deleted_count}


class BulkIdsIn(BaseModel):
    ids: List[str] = Field(min_length=1, max_length=5000)
    price: Optional[float] = Field(default=None, gt=0, le=100000)


@api.post("/vendor/products/bulk-price")
async def vendor_bulk_price(body: BulkIdsIn, user=Depends(require_approved_vendor)):
    if not body.price:
        raise HTTPException(400, "Price is required")
    cents = to_cents(body.price)
    r = await db.products.update_many({"id": {"$in": body.ids}, "vendor_id": user["id"]},
                                      {"$set": {"vendor_price_cents": cents, "price_cents": cents, **listing_status(user),
                                                "reason": None, "updated_at": now_iso()}})
    await audit(user, "product.bulk_price", None, details=f"{r.modified_count} listings -> ${body.price:.2f} (resubmitted for review)")
    return {"updated": r.modified_count}


@api.post("/vendor/products/bulk-delete")
async def vendor_bulk_delete(body: BulkIdsIn, user=Depends(require_role("vendor", "admin"))):
    return await _delete_products({"id": {"$in": body.ids}, "vendor_id": user["id"]}, user, f"{len(body.ids)} selected")


@api.delete("/vendor/products/{pid}")
async def vendor_delete_product(pid: str, user=Depends(require_role("vendor", "admin"))):
    return await _delete_products({"id": pid, "vendor_id": user["id"]}, user, pid)


@api.delete("/vendor/batches/{bid}")
async def vendor_delete_batch(bid: str, user=Depends(require_role("vendor", "admin"))):
    return await _delete_products({"batch_id": bid, "vendor_id": user["id"]}, user, bid)


@api.get("/vendor/products/{pid}/keys")
async def vendor_list_keys(pid: str, user=Depends(require_role("vendor", "admin"))):
    keys = await db.license_keys.find({"product_id": pid, "vendor_id": user["id"]},
                                      {"_id": 0}).sort("created_at", -1).to_list(2000)
    for k in keys:
        if k["status"] != "available":
            k["key"] = k["key"][:4] + "••••" + k["key"][-4:]
    return keys


@api.delete("/vendor/keys/{kid}")
async def vendor_delete_key(kid: str, user=Depends(require_approved_vendor)):
    k = await db.license_keys.find_one_and_delete({"id": kid, "vendor_id": user["id"], "status": "available"})
    if not k:
        raise HTTPException(400, "Key not found or already sold")
    await db.products.update_one({"id": k["product_id"]}, {"$inc": {"stock_count": -1}})
    return {"ok": True}


@api.get("/vendor/sales")
async def vendor_sales(user=Depends(require_role("vendor", "admin"))):
    orders = await db.orders.find({"vendor_id": user["id"]}, {"_id": 0, "license_key": 0}).sort("created_at", -1).to_list(5000)
    return orders


@api.get("/vendor/withdrawals")
async def vendor_withdrawals(user=Depends(require_role("vendor"))):
    return await db.withdrawals.find({"vendor_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(500)


@api.post("/vendor/withdrawals")
async def vendor_request_withdrawal(body: WithdrawIn, user=Depends(require_approved_vendor)):
    amt = to_cents(body.amount)
    res = await db.users.find_one_and_update({"id": user["id"], "earnings_cents": {"$gte": amt}},
                                             {"$inc": {"earnings_cents": -amt}})
    if not res:
        raise HTTPException(400, "Insufficient earnings balance")
    w = {"id": new_id(), "vendor_id": user["id"], "vendor_email": user["email"],
         "vendor_name": user.get("store_name") or user["name"], "amount_cents": amt, "coin": body.coin,
         "network": COINS[body.coin]["network"], "address": body.address.strip(), "status": "pending",
         "created_at": now_iso()}
    await db.withdrawals.insert_one(w)
    w.pop("_id", None)
    await audit(user, "withdrawal.request", w["id"], -amt, user["id"], f"{body.coin} to {body.address}")
    return w


# ---------------- Admin ----------------
@api.get("/admin/stats")
async def admin_stats(user=Depends(admin_dep)):
    orders = await db.orders.find({}, {"_id": 0, "price_cents": 1, "commission_cents": 1}).to_list(100000)
    approved = await db.deposits.find({"status": "approved"}, {"_id": 0, "credited_cents": 1}).to_list(100000)
    recent = await db.orders.find({}, {"_id": 0, "license_key": 0}).sort("created_at", -1).to_list(10)
    return {
        "users": await db.users.count_documents({"role": "buyer"}),
        "vendors": await db.users.count_documents({"role": "vendor", "vendor_status": "approved"}),
        "products_live": await db.products.count_documents({"status": "approved"}),
        "orders": len(orders), "volume_cents": sum(o["price_cents"] for o in orders),
        "commission_cents": sum(o["commission_cents"] for o in orders),
        "deposits_cents": sum(d.get("credited_cents", 0) for d in approved),
        "pending": {
            "deposits": await db.deposits.count_documents({"status": "pending"}),
            "withdrawals": await db.withdrawals.count_documents({"status": "pending"}),
            "vendors": await db.users.count_documents({"role": "vendor", "vendor_status": "pending"}),
            "listings": await db.products.count_documents({"status": "pending"}),
            "tickets": await db.tickets.count_documents({"status": "open"}),
        },
        "recent_orders": recent,
    }


@api.get("/admin/deposits")
async def admin_deposits(status: str = "pending", user=Depends(admin_dep)):
    q = {} if status == "all" else {"status": status}
    return await db.deposits.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)


@api.post("/admin/deposits/manual")
async def admin_manual_deposit(body: ManualDepositIn, user=Depends(admin_dep)):
    target = await db.users.find_one({"email": body.email.lower()}, {"_id": 0})
    if not target:
        raise HTTPException(404, "No user with that email")
    credit = to_cents(body.amount)
    dep = {"id": new_id(), "user_id": target["id"], "user_email": target["email"], "coin": body.coin,
           "network": COINS[body.coin]["network"] if body.coin in COINS else "manual", "address": "",
           "amount_cents": credit, "credited_cents": credit, "reference": "MAN-" + secrets.token_hex(4).upper(),
           "status": "approved", "manual": True, "note": body.note, "reviewed_by": user["email"],
           "reviewed_at": now_iso(), "submitted_at": now_iso(), "created_at": now_iso()}
    if body.txid and body.txid.strip():
        dep["txid"] = body.txid.strip().lower()
    try:
        await db.deposits.insert_one(dep)
    except DuplicateKeyError:
        raise HTTPException(400, "This TXID was already used for another deposit")
    await db.users.update_one({"id": target["id"]}, {"$inc": {"balance_cents": credit}})
    await audit(user, "deposit.manual", dep["id"], credit, target["id"], f"{body.coin} txid {dep.get('txid', '-')} · {body.note}")
    await notify(target["id"], "Deposit approved", f"${credit / 100:.2f} has been credited to your wallet (ref {dep['reference']}).",
                 "Deposit approved")
    dep.pop("_id", None)
    return dep


@api.post("/admin/deposits/{did}/approve")
async def admin_approve_deposit(did: str, body: ApproveDepositIn, user=Depends(admin_dep)):
    d = await db.deposits.find_one({"id": did, "status": "pending"}, {"_id": 0})
    if not d:
        raise HTTPException(400, "Deposit not pending")
    credit = to_cents(body.amount) if body.amount else d["amount_cents"]
    d = await db.deposits.find_one_and_update(
        {"id": did, "status": "pending"},
        {"$set": {"status": "approved", "credited_cents": credit, "reviewed_by": user["email"], "reviewed_at": now_iso(),
                  "chain.final": True}},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    if not d:
        raise HTTPException(400, "Deposit already processed")
    await db.users.update_one({"id": d["user_id"]}, {"$inc": {"balance_cents": credit}})
    await audit(user, "deposit.approve", did, credit, d["user_id"], f"{d['coin']} txid {d['txid']} ref {d['reference']}")
    await notify(d["user_id"], "Deposit approved", f"${credit / 100:.2f} has been credited to your wallet (ref {d['reference']}).",
                 "Deposit approved")
    return d


@api.post("/admin/deposits/{did}/recheck")
async def admin_recheck_deposit(did: str, user=Depends(admin_dep)):
    d = await db.deposits.find_one({"id": did, "status": "pending", "txid": {"$type": "string"}}, {"_id": 0})
    if not d:
        raise HTTPException(400, "Deposit not pending")
    cfg = await chain.auto_cfg(d["coin"])
    if not cfg:
        raise HTTPException(400, "Auto-verify is off for this coin")
    await db.deposits.update_one({"id": did}, {"$set": {"chain.final": False, "submitted_at": now_iso()}})
    await chain.process_deposit({**d, "submitted_at": now_iso()}, cfg)
    return await db.deposits.find_one({"id": did}, {"_id": 0})


@api.post("/admin/deposits/{did}/reject")
async def admin_reject_deposit(did: str, body: ReasonIn, user=Depends(admin_dep)):
    d = await db.deposits.find_one_and_update(
        {"id": did, "status": {"$in": ["pending", "awaiting_txid"]}},
        {"$set": {"status": "rejected", "reason": body.reason, "reviewed_by": user["email"], "reviewed_at": now_iso(),
                  "chain.final": True}},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    if not d:
        raise HTTPException(400, "Deposit not pending")
    await audit(user, "deposit.reject", did, None, d["user_id"], body.reason)
    await notify(d["user_id"], "Deposit rejected", f"Deposit {d['reference']} was rejected: {body.reason}", "Deposit update")
    return d


@api.get("/admin/withdrawals")
async def admin_withdrawals(status: str = "pending", user=Depends(admin_dep)):
    q = {} if status == "all" else {"status": status}
    return await db.withdrawals.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)


@api.post("/admin/withdrawals/{wid}/pay")
async def admin_pay_withdrawal(wid: str, body: PayIn, user=Depends(admin_dep)):
    w = await db.withdrawals.find_one_and_update(
        {"id": wid, "status": "pending"},
        {"$set": {"status": "paid", "payout_txid": body.payout_txid, "reviewed_by": user["email"], "reviewed_at": now_iso()}},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    if not w:
        raise HTTPException(400, "Withdrawal not pending")
    await audit(user, "withdrawal.paid", wid, w["amount_cents"], None, f"to {w['vendor_email']} txid {body.payout_txid or '-'}")
    await notify(w["vendor_id"], "Payout sent", f"Your withdrawal of ${w['amount_cents'] / 100:.2f} ({w['coin']}) has been paid.",
                 "Payout sent")
    return w


@api.post("/admin/withdrawals/{wid}/reject")
async def admin_reject_withdrawal(wid: str, body: ReasonIn, user=Depends(admin_dep)):
    w = await db.withdrawals.find_one_and_update(
        {"id": wid, "status": "pending"},
        {"$set": {"status": "rejected", "reason": body.reason, "reviewed_by": user["email"], "reviewed_at": now_iso()}},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    if not w:
        raise HTTPException(400, "Withdrawal not pending")
    await db.users.update_one({"id": w["vendor_id"]}, {"$inc": {"earnings_cents": w["amount_cents"]}})
    await audit(user, "withdrawal.reject_refund", wid, w["amount_cents"], w["vendor_id"], body.reason)
    await notify(w["vendor_id"], "Withdrawal rejected", f"Withdrawal rejected: {body.reason}. Funds returned to earnings.",
                 "Payout update")
    return w


@api.get("/admin/vendors")
async def admin_vendors(status: str = "all", user=Depends(admin_dep)):
    q = {"role": "vendor"}
    if status != "all":
        q["vendor_status"] = status
    return await db.users.find(q, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(5000)


async def _set_vendor_status(vid: str, status: str, actor: dict, reason: str = ""):
    res = await db.users.find_one_and_update({"id": vid, "role": "vendor"}, {"$set": {"vendor_status": status}},
                                             projection={"_id": 0, "password_hash": 0}, return_document=ReturnDocument.AFTER)
    if not res:
        raise HTTPException(404, "Vendor not found")
    await audit(actor, f"vendor.{status}", vid, details=reason)
    await notify(vid, f"Vendor application {status}", reason or f"Your vendor account is now {status}.", "Vendor account update")
    return res


@api.post("/admin/vendors/{vid}/approve")
async def admin_approve_vendor(vid: str, user=Depends(admin_dep)):
    return await _set_vendor_status(vid, "approved", user)


@api.post("/admin/vendors/{vid}/reject")
async def admin_reject_vendor(vid: str, body: ReasonIn, user=Depends(admin_dep)):
    return await _set_vendor_status(vid, "rejected", user, body.reason)


@api.put("/admin/vendors/{vid}/commission")
async def admin_vendor_commission(vid: str, body: VendorCommissionIn, user=Depends(admin_dep)):
    res = await db.users.update_one({"id": vid, "role": "vendor"}, {"$set": {"commission_pct": body.pct}})
    if not res.matched_count:
        raise HTTPException(404, "Vendor not found")
    await audit(user, "commission.vendor_override", vid, details=f"pct={body.pct if body.pct is not None else 'global default'}")
    return {"ok": True, "commission_pct": body.pct}


@api.get("/admin/products")
async def admin_products(status: str = "all", user=Depends(admin_dep)):
    q = {} if status == "all" else {"status": status}
    return await db.products.find(q, {"_id": 0}).sort("created_at", -1).to_list(5000)


@api.post("/admin/products/{pid}/approve")
async def admin_approve_product(pid: str, body: ApproveProductIn, user=Depends(admin_dep)):
    p = await db.products.find_one({"id": pid}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Product not found")
    upd = {"status": "approved", "approved_at": now_iso(), "reason": None}
    if body.price:
        upd["price_cents"] = to_cents(body.price)
        await audit(user, "product.price_override", pid,
                    details=f"{p['title']}: ${p['price_cents'] / 100:.2f} -> ${body.price:.2f}")
    await db.products.update_one({"id": pid}, {"$set": upd})
    await audit(user, "product.approve", pid, details=p["title"])
    await notify(p["vendor_id"], "Listing approved", f"{p['title']} is now live on the marketplace.")
    return {**p, **upd}


@api.post("/admin/products/{pid}/reject")
async def admin_reject_product(pid: str, body: ReasonIn, user=Depends(admin_dep)):
    p = await db.products.find_one_and_update({"id": pid}, {"$set": {"status": "rejected", "reason": body.reason}},
                                              projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    if not p:
        raise HTTPException(404, "Product not found")
    await audit(user, "product.reject", pid, details=body.reason)
    await notify(p["vendor_id"], "Listing rejected", f"{p['title']}: {body.reason}")
    return p


@api.put("/admin/products/{pid}/price")
async def admin_price_override(pid: str, body: PriceIn, user=Depends(admin_dep)):
    p = await db.products.find_one({"id": pid}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Product not found")
    await db.products.update_one({"id": pid}, {"$set": {"price_cents": to_cents(body.price)}})
    await audit(user, "product.price_override", pid,
                details=f"{p['title']}: ${p['price_cents'] / 100:.2f} -> ${body.price:.2f}")
    await notify(p["vendor_id"], "Price updated by admin", f"{p['title']} price set to ${body.price:.2f}.")
    return {"ok": True}


@api.post("/admin/batches/{bid}/approve")
async def admin_approve_batch(bid: str, body: ApproveProductIn, user=Depends(admin_dep)):
    q = {"batch_id": bid, "status": "pending"}
    first = await db.products.find_one(q, {"_id": 0})
    if not first:
        raise HTTPException(404, "No pending items in this batch")
    upd = {"status": "approved", "approved_at": now_iso(), "reason": None}
    if body.price:
        upd["price_cents"] = to_cents(body.price)
    r = await db.products.update_many(q, {"$set": upd})
    await audit(user, "product.batch_approve", bid, details=f"{r.modified_count} items" + (f" @ ${body.price:.2f}" if body.price else ""))
    await notify(first["vendor_id"], "Batch approved", f"{r.modified_count} items from your bulk import are now live.")
    return {"approved": r.modified_count}


@api.delete("/admin/products/{pid}")
async def admin_delete_product(pid: str, user=Depends(admin_dep)):
    return await _delete_products({"id": pid}, user, pid)


@api.get("/admin/settings")
async def admin_get_settings(user=Depends(admin_dep)):
    return await get_settings()


@api.put("/admin/settings")
async def admin_update_settings(body: SettingsIn, user=Depends(admin_dep)):
    s = await get_settings()
    upd = {}
    if body.commission_pct is not None and body.commission_pct != s["commission_pct"]:
        upd["commission_pct"] = body.commission_pct
        await audit(user, "commission.global", None, details=f"{s['commission_pct']}% -> {body.commission_pct}%")
    if body.addresses is not None:
        addrs = {c: body.addresses.get(c, s["addresses"].get(c, "")).strip() for c in COINS}
        upd["addresses"] = addrs
        changed = [c for c in COINS if addrs[c] != s["addresses"].get(c, "")]
        if changed:
            await audit(user, "settings.addresses", None, details=f"updated: {', '.join(changed)}")
    if body.auto_verify is not None:
        upd["auto_verify"] = {c: body.auto_verify[c].model_dump() if c in body.auto_verify else v
                              for c, v in s["auto_verify"].items()}
        await audit(user, "settings.auto_verify", None, details=", ".join(
            f"{c}:{'on' if v['enabled'] else 'off'}/{v['confirmations']}" for c, v in upd["auto_verify"].items()))
    if upd:
        await db.settings.update_one({"key": "global"}, {"$set": upd})
    return await get_settings()


@api.put("/admin/site")
async def admin_update_site(body: SiteIn, user=Depends(admin_dep)):
    s = await get_settings()
    upd = {}
    if body.notice is not None:
        n = body.notice
        if n.starts_at and n.ends_at and n.ends_at <= n.starts_at:
            raise HTTPException(400, "Notice end time must be after start time")
        norm = lambda d: (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(timezone.utc).isoformat() if d else None
        upd["notice"] = {**{k: (v.strip() if isinstance(v, str) else v) for k, v in n.model_dump(exclude={"starts_at", "ends_at"}).items()},
                         "starts_at": norm(n.starts_at), "ends_at": norm(n.ends_at)}
        await audit(user, "settings.notice", None, details=f"enabled={body.notice.enabled}, title={body.notice.title[:40]}")
    if body.categories is not None:
        names = [c.name.strip() for c in body.categories]
        if len(set(n.lower() for n in names)) != len(names) or not all(names):
            raise HTTPException(400, "Category names must be unique and not empty")
        kept = {c.original for c in body.categories if c.original}
        for old in s["categories"]:
            if old not in kept:
                n = await db.products.count_documents({"category": old})
                if n:
                    raise HTTPException(400, f"'{old}' has {n} product(s). Rename it or move/delete those products first.")
        for c in body.categories:
            if c.original and c.original in s["categories"] and c.original != c.name.strip():
                await db.products.update_many({"category": c.original}, {"$set": {"category": c.name.strip()}})
                await db.orders.update_many({"category": c.original}, {"$set": {"category": c.name.strip()}})
        upd["categories"] = names
        upd["category_style"] = {c.name.strip(): {"icon": c.icon, "color": c.color} for c in body.categories}
        await audit(user, "settings.categories", None, details=", ".join(names))
    if body.fonts is not None:
        body.fonts.check()
    for k in ("theme", "fonts", "brand", "footer"):
        if getattr(body, k) is not None:
            upd[k] = getattr(body, k).model_dump()
            await audit(user, f"settings.{k}", None, details=f"{k} updated")
    if body.sections is not None:
        upd["sections"] = clean_sections(body.sections)
        await audit(user, "settings.sections", None, details=", ".join(x["type"] for x in upd["sections"] if x["enabled"]))
    if body.hero is not None:
        upd["hero"] = body.hero.model_dump()
        await audit(user, "settings.hero", None, details=f"enabled={body.hero.enabled}, title={body.hero.title}")
    if body.banners is not None:
        seen = set()
        upd["banners"] = []
        for b in body.banners:
            bid = b.id if b.id and b.id not in seen else new_id()
            seen.add(bid)
            upd["banners"].append({**b.model_dump(), "id": bid})
        await audit(user, "settings.banners", None, details=f"{len(body.banners)} banner(s)")
    if upd:
        await db.settings.update_one({"key": "global"}, {"$set": upd})
    return await admin_get_site(user)


@api.get("/admin/users")
async def admin_users(q: str = "", role: str = "all", user=Depends(admin_dep)):
    query = {}
    if role != "all":
        query["role"] = role
    if q:
        query["$or"] = [{"email": {"$regex": q, "$options": "i"}}, {"name": {"$regex": q, "$options": "i"}}]
    return await db.users.find(query, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(5000)


@api.get("/admin/users/{uid}/details")
async def admin_user_details(uid: str, user=Depends(admin_dep)):
    u = await db.users.find_one({"id": uid}, {"_id": 0, "password_hash": 0})
    if not u:
        raise HTTPException(404, "User not found")
    orders = await db.orders.find({"buyer_id": uid}, {"_id": 0, "license_key": 0, "delivery_content": 0}) \
        .sort("created_at", -1).to_list(5000)
    deposits = await db.deposits.find({"user_id": uid}, {"_id": 0}).sort("created_at", -1).to_list(50)
    products = {}
    for o in orders:
        g = products.setdefault(o["product_id"], {"product_id": o["product_id"], "title": o["product_title"],
                                                  "category": o.get("category"), "count": 0, "spent_cents": 0,
                                                  "last_at": o["created_at"]})
        g["count"] += 1
        g["spent_cents"] += o["price_cents"]
    return {"user": u, "orders": orders[:50], "deposits": deposits, "products": list(products.values()),
            "stats": {"orders": len(orders), "spent_cents": sum(o["price_cents"] for o in orders),
                      "deposited_cents": sum(d.get("credited_cents", 0) for d in deposits if d["status"] == "approved"),
                      "pending_deposits": sum(1 for d in deposits if d["status"] == "pending")}}


# ---------------- Support tickets ----------------
TICKET_TOPICS = ["General", "Deposit", "Order", "Vendor", "Account"]


class TicketMsgIn(BaseModel):
    message: str = Field(default="", max_length=4000)
    attachments: List[str] = Field(default_factory=list, max_length=4)


class TicketIn(TicketMsgIn):
    subject: str = Field(min_length=3, max_length=120)
    topic: Literal["General", "Deposit", "Order", "Vendor", "Account"] = "General"
    order_id: Optional[str] = None


class CannedIn(BaseModel):
    title: str = Field(min_length=1, max_length=60)
    text: str = Field(min_length=1, max_length=2000)


class CannedListIn(BaseModel):
    replies: List[CannedIn] = Field(max_length=30)


DEFAULT_CANNED = [
    {"title": "Deposit delay", "text": "Hi {name}, thanks for reaching out. Crypto deposits are verified manually and need network confirmations, usually within 1–2 hours. We'll credit your wallet as soon as your transaction is confirmed. Reference: {ref}."},
    {"title": "Need TXID", "text": "Hi {name}, please reply with the transaction ID (TXID) and the coin/network you used so we can locate your payment."},
    {"title": "Wrong network", "text": "Hi {name}, it looks like the funds were sent on a different network than the one shown. Please share the TXID and network used; we'll check whether recovery is possible."},
    {"title": "Key not working", "text": "Hi {name}, sorry about that. Please send a screenshot of the activation error and the order ID. We'll check with the vendor and resolve it via wallet credit or a replacement."},
    {"title": "Resolved", "text": "Hi {name}, this has been resolved. If you need anything else just reply here. Thanks for using our marketplace!"},
]


class TicketStatusIn(BaseModel):
    status: Literal["open", "closed"]


def _msg(user: dict, body: TicketMsgIn) -> dict:
    return {"id": new_id(), "author_id": user["id"], "author_name": user.get("name") or user["email"],
            "from_admin": user["role"] == "admin", "message": body.message.strip(),
            "attachments": body.attachments, "created_at": now_iso()}


async def _check_msg(body: TicketMsgIn, user: dict):
    body.attachments = list(dict.fromkeys(body.attachments))
    if not body.message.strip() and not body.attachments:
        raise HTTPException(400, "Write a message or attach a screenshot")
    if body.attachments:
        n = await db.files.count_documents({"storage_path": {"$in": body.attachments}, "owner_id": user["id"],
                                            "kind": "ticket", "is_deleted": False})
        if n != len(body.attachments):
            raise HTTPException(400, "Invalid attachment")


@api.post("/tickets/upload")
async def upload_ticket_file(file: UploadFile = File(...), user=Depends(get_current_user)):
    if file.content_type not in ALLOWED_IMG:
        raise HTTPException(400, "Only PNG, JPG, WEBP or GIF images allowed")
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(400, "Max 5MB per image")
    path = f"{APP_NAME}/tickets/{user['id']}/{uuid.uuid4()}.{ALLOWED_IMG[file.content_type]}"
    result = await asyncio.to_thread(put_object, path, data, file.content_type)
    await db.files.insert_one({"id": new_id(), "storage_path": result["path"], "original_filename": file.filename,
                               "content_type": file.content_type, "size": result.get("size"), "kind": "ticket",
                               "owner_id": user["id"], "is_deleted": False, "created_at": now_iso()})
    return {"path": result["path"]}


@api.get("/tickets/files/{path:path}")
async def ticket_file(path: str, user=Depends(get_current_user)):
    rec = await db.files.find_one({"storage_path": path, "kind": "ticket", "is_deleted": False})
    if not rec:
        raise HTTPException(404, "File not found")
    if user["role"] != "admin" and rec["owner_id"] != user["id"] and not await db.tickets.find_one(
            {"user_id": user["id"], "messages.attachments": path}, {"_id": 1}):
        raise HTTPException(403, "Forbidden")
    data, ctype = await asyncio.to_thread(get_object, path)
    return Response(content=data, media_type=rec.get("content_type", ctype), headers={"Cache-Control": "private, max-age=3600"})


@api.get("/admin/canned-replies")
async def get_canned(user=Depends(admin_dep)):
    s = await get_settings()
    return s["canned_replies"] if "canned_replies" in s else DEFAULT_CANNED


@api.put("/admin/canned-replies")
async def put_canned(body: CannedListIn, user=Depends(admin_dep)):
    replies = [r.model_dump() for r in body.replies]
    await db.settings.update_one({"key": "global"}, {"$set": {"canned_replies": replies}})
    await audit(user, "tickets.canned_updated", None, None, None, f"{len(replies)} quick replies")
    return replies


async def _ticket_for(tid: str, user: dict) -> dict:
    q = {"id": tid} if user["role"] == "admin" else {"id": tid, "user_id": user["id"]}
    t = await db.tickets.find_one(q, {"_id": 0})
    if not t:
        raise HTTPException(404, "Ticket not found")
    return t


@api.post("/tickets")
async def create_ticket(body: TicketIn, user=Depends(get_current_user)):
    await _check_msg(body, user)
    t = {"id": new_id(), "ref": "TCK-" + secrets.token_hex(3).upper(), "user_id": user["id"],
         "user_email": user["email"], "user_name": user.get("name"), "user_role": user["role"],
         "subject": body.subject.strip(), "topic": body.topic, "order_id": body.order_id,
         "status": "open", "unread_user": False, "unread_admin": True,
         "messages": [_msg(user, body)], "created_at": now_iso(), "updated_at": now_iso()}
    await db.tickets.insert_one(t)
    t.pop("_id", None)
    return t


@api.get("/tickets")
async def my_tickets(user=Depends(get_current_user)):
    return await db.tickets.find({"user_id": user["id"]}, {"_id": 0, "messages": 0}).sort("updated_at", -1).to_list(500)


@api.get("/tickets/{tid}")
async def get_ticket(tid: str, user=Depends(get_current_user)):
    t = await _ticket_for(tid, user)
    flag = "unread_admin" if user["role"] == "admin" else "unread_user"
    if t.get(flag):
        await db.tickets.update_one({"id": tid}, {"$set": {flag: False}})
        t[flag] = False
    return t


@api.post("/tickets/{tid}/messages")
async def reply_ticket(tid: str, body: TicketMsgIn, user=Depends(get_current_user)):
    t = await _ticket_for(tid, user)
    admin = user["role"] == "admin"
    if t["status"] == "closed" and not admin:
        raise HTTPException(400, "This ticket is closed. Please open a new one.")
    await _check_msg(body, user)
    upd = {"status": "answered" if admin else "open", "updated_at": now_iso(),
           "unread_user": admin, "unread_admin": not admin}
    res = await db.tickets.find_one_and_update({"id": tid}, {"$push": {"messages": _msg(user, body)}, "$set": upd},
                                               projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    if admin:
        await notify(t["user_id"], "Support replied", f"{t['ref']} · {t['subject']}: {body.message.strip()[:200] or '(screenshot attached)'}",
                     "Support ticket reply")
    return res


@api.get("/admin/tickets")
async def admin_tickets(status: str = "all", q: str = "", user=Depends(admin_dep)):
    query = {} if status == "all" else {"status": status}
    if q:
        rx = {"$regex": re.escape(q), "$options": "i"}
        query["$or"] = [{"subject": rx}, {"user_email": rx}, {"ref": rx}]
    return await db.tickets.find(query, {"_id": 0, "messages": 0}).sort("updated_at", -1).to_list(1000)


@api.post("/admin/tickets/{tid}/status")
async def admin_ticket_status(tid: str, body: TicketStatusIn, user=Depends(admin_dep)):
    t = await _ticket_for(tid, user)
    await db.tickets.update_one({"id": tid}, {"$set": {"status": body.status, "updated_at": now_iso()}})
    await audit(user, f"ticket.{body.status}", tid, None, t["user_id"], t["ref"])
    if body.status == "closed":
        await notify(t["user_id"], "Ticket closed", f"{t['ref']} · {t['subject']} was marked resolved.")
    return {"ok": True}


@api.post("/admin/users/{uid}/adjust")
async def admin_adjust_balance(uid: str, body: AdjustIn, user=Depends(admin_dep)):
    amt = to_cents(body.amount)
    if amt == 0:
        raise HTTPException(400, "Amount cannot be zero")
    cond = {"id": uid} if amt > 0 else {"id": uid, "balance_cents": {"$gte": -amt}}
    res = await db.users.find_one_and_update(cond, {"$inc": {"balance_cents": amt}})
    if not res:
        raise HTTPException(400, "User not found or insufficient balance")
    await audit(user, "wallet.admin_adjust", uid, amt, uid, body.reason)
    await notify(uid, "Wallet adjusted", f"Admin {'credited' if amt > 0 else 'debited'} ${abs(amt) / 100:.2f}: {body.reason}")
    return {"ok": True}


@api.post("/admin/users/{uid}/status")
async def admin_user_status(uid: str, body: StatusIn, user=Depends(admin_dep)):
    if uid == user["id"]:
        raise HTTPException(400, "Cannot change your own status")
    await db.users.update_one({"id": uid}, {"$set": {"status": body.status}})
    await audit(user, f"user.{body.status}", uid)
    return {"ok": True}


@api.delete("/admin/users/{uid}")
async def admin_delete_user(uid: str, user=Depends(admin_dep)):
    if uid == user["id"]:
        raise HTTPException(400, "Cannot delete your own account")
    u = await db.users.find_one({"id": uid}, {"_id": 0})
    if not u:
        raise HTTPException(404, "User not found")
    if u["role"] == "admin":
        raise HTTPException(400, "Admin accounts cannot be deleted")
    await db.users.delete_one({"id": uid})
    pids = await db.products.distinct("id", {"vendor_id": uid})
    counts = {
        "products": (await db.products.delete_many({"vendor_id": uid})).deleted_count,
        "keys": (await db.license_keys.delete_many({"$or": [{"vendor_id": uid}, {"product_id": {"$in": pids}}]})).deleted_count,
        "orders": (await db.orders.delete_many({"$or": [{"buyer_id": uid}, {"vendor_id": uid}]})).deleted_count,
        "deposits": (await db.deposits.delete_many({"user_id": uid})).deleted_count,
        "withdrawals": (await db.withdrawals.delete_many({"vendor_id": uid})).deleted_count,
        "tickets": (await db.tickets.delete_many({"user_id": uid})).deleted_count,
    }
    await db.notifications.delete_many({"user_id": uid})
    await db.audit_logs.delete_many({"user_id": uid})
    await audit(user, "user.delete", uid, details=f"{u['email']} ({u['role']}) · " + ", ".join(f"{v} {k}" for k, v in counts.items()))
    return {"ok": True, **counts}


@api.get("/admin/orders")
async def admin_orders(user=Depends(admin_dep)):
    return await db.orders.find({}, {"_id": 0, "license_key": 0}).sort("created_at", -1).to_list(5000)


@api.get("/admin/audit")
async def admin_audit(action: str = "", user=Depends(admin_dep)):
    q = {"action": {"$regex": f"^{action}"}} if action else {}
    return await db.audit_logs.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)


@api.get("/")
async def root():
    return {"message": "CardWizard API"}


app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
                   allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.tickets.create_index("id", unique=True)
    await db.tickets.create_index([("user_id", 1), ("updated_at", -1)])
    await db.users.create_index("id", unique=True)
    await db.products.create_index("id", unique=True)
    await db.deposits.create_index("reference", unique=True)
    await db.deposits.create_index("txid", unique=True, partialFilterExpression={"txid": {"$type": "string"}})
    await db.license_keys.create_index([("product_id", 1), ("key", 1)], unique=True)
    await db.license_keys.create_index([("product_id", 1), ("status", 1)])
    await db.license_keys.create_index([("vendor_id", 1), ("key", 1)])
    await db.products.create_index("batch_id")
    await db.products.create_index([("status", 1), ("attrs.k", 1), ("attrs.v", 1)])
    await db.login_attempts.create_index("identifier")
    await db.captchas.create_index("expires_at", expireAfterSeconds=0)
    await seed_all()
    asyncio.create_task(chain.poll_loop())
    try:
        await asyncio.to_thread(init_storage)
        logger.info("Storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")


@app.on_event("shutdown")
async def shutdown():
    client.close()
