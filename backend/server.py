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

from core import (db, client, logger, CATEGORIES, COINS, APP_NAME, now_iso, new_id, to_cents,
                  hash_password, verify_password, create_access_token, public_user, get_current_user,
                  require_role, require_approved_vendor, audit, notify, get_settings,
                  init_storage, put_object, get_object)
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
    blocks = [[ln.strip() for ln in part.splitlines() if ln.strip()] for part in parts]
    return [b for b in blocks if b]


class KeysIn(BaseModel):
    keys: str


class DepositIn(BaseModel):
    coin: Literal["BTC", "USDT_TRC20", "LTC", "ETH"]
    amount: float = Field(ge=1, le=1000000)


class TxIn(BaseModel):
    txid: str = Field(min_length=8, max_length=200)


class WithdrawIn(BaseModel):
    amount: float = Field(ge=1)
    coin: Literal["BTC", "USDT_TRC20", "LTC", "ETH"]
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


class SettingsIn(BaseModel):
    commission_pct: Optional[float] = Field(default=None, ge=0, le=100)
    addresses: Optional[Dict[str, str]] = None


class NoticeIn(BaseModel):
    enabled: bool = True
    tone: Literal["amber", "green", "cyan", "red"] = "amber"
    title: str = Field(default="", max_length=80)
    body: str = Field(default="", max_length=600)
    highlight: str = Field(default="", max_length=200)


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    original: Optional[str] = None


class SiteIn(BaseModel):
    notice: Optional[NoticeIn] = None
    categories: Optional[List[CategoryIn]] = Field(default=None, min_length=1, max_length=30)


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


# ---------------- Public catalog ----------------
@api.get("/categories")
async def categories():
    return (await get_settings())["categories"]


@api.get("/site")
async def site():
    s = await get_settings()
    return {"categories": s["categories"], "notice": s["notice"]}


def parse_attrs(lines: List[str]) -> List[dict]:
    out = []
    for ln in lines:
        k, sep, v = ln.partition(":")
        if sep and 0 < len(k.strip()) <= 30 and v.strip() and len(v.strip()) <= 60:
            out.append({"k": k.strip().title(), "v": v.strip()})
    return out


def base_query(category: str, vendor: str) -> dict:
    query = {"status": "approved"}
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
        query["$or"] = [{"title": {"$regex": q, "$options": "i"}},
                        {"description": {"$regex": q, "$options": "i"}},
                        {"vendor_name": {"$regex": q, "$options": "i"}}]
    sorts = {"new": [("approved_at", -1)], "popular": [("sales_count", -1)],
             "price_asc": [("price_cents", 1)], "price_desc": [("price_cents", -1)]}
    return await db.products.find(query, PUBLIC_PRODUCT).sort(sorts.get(sort, sorts["new"])).to_list(2000)


@api.get("/vendors")
async def public_vendors():
    vendors = await db.users.find({"role": "vendor", "vendor_status": "approved", "status": "active"},
                                  {"_id": 0, "id": 1, "store_name": 1, "name": 1, "created_at": 1}).to_list(500)
    stats = await db.products.aggregate([
        {"$match": {"status": "approved"}},
        {"$group": {"_id": "$vendor_id", "products": {"$sum": 1}, "sales": {"$sum": "$sales_count"},
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
    rec = await db.files.find_one({"storage_path": path, "is_deleted": False})
    if not rec:
        raise HTTPException(404, "File not found")
    data, ctype = await asyncio.to_thread(get_object, path)
    return Response(content=data, media_type=rec.get("content_type", ctype),
                    headers={"Cache-Control": "public, max-age=86400"})


# ---------------- Vendor ----------------
@api.get("/vendor/stats")
async def vendor_stats(user=Depends(require_role("vendor"))):
    s = await get_settings()
    orders = await db.orders.find({"vendor_id": user["id"]}, {"_id": 0}).to_list(5000)
    return {"vendor_status": user.get("vendor_status"), "earnings_cents": user.get("earnings_cents", 0),
            "total_sales": len(orders), "gross_cents": sum(o["price_cents"] for o in orders),
            "net_cents": sum(o["vendor_earning_cents"] for o in orders),
            "commission_pct": user.get("commission_pct") if user.get("commission_pct") is not None else s["commission_pct"],
            "products": await db.products.count_documents({"vendor_id": user["id"]}),
            "live_products": await db.products.count_documents({"vendor_id": user["id"], "status": "approved"})}


@api.get("/vendor/products")
async def vendor_products(user=Depends(require_role("vendor"))):
    return await db.products.find({"vendor_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(5000)


@api.post("/vendor/products")
async def vendor_create_product(body: ProductIn, user=Depends(require_approved_vendor)):
    await check_category(body.category)
    p = {"id": new_id(), "vendor_id": user["id"], "vendor_name": user.get("store_name") or user["name"],
         **product_fields(body), "status": "pending", "stock_count": 0, "sales_count": 0, "created_at": now_iso()}
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
    upd = {**product_fields(body), "status": "pending", "updated_at": now_iso()}
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
    vname = user.get("store_name") or user["name"]
    products, keys, skipped = [], [], 0
    for n, (b, secret) in enumerate(items, 1):
        if secret in seen or secret in existing:
            skipped += 1
            continue
        seen.add(secret)
        preview = [b[i] for i in pub if i < len(b) and i != body.title_line]
        title = b[body.title_line] if body.title_line is not None and body.title_line < len(b) else f"{body.title_prefix} #{n}"
        pid = new_id()
        products.append({"id": pid, "vendor_id": user["id"], "vendor_name": vname, "title": title[:120],
                         "description": "\n".join(preview), "preview_lines": preview, "attrs": parse_attrs(preview),
                         "category": body.category,
                         "price_cents": cents, "vendor_price_cents": cents,
                         "image": body.image or default_image(body.category), "tags": clean_tags(body.tags),
                         "delivery_type": "keys", "delivery_content": "", "batch_id": batch_id,
                         "status": "pending", "stock_count": 1, "sales_count": 0, "created_at": now})
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
                                      {"$set": {"vendor_price_cents": cents, "price_cents": cents, "status": "pending",
                                                "reason": None, "updated_at": now_iso()}})
    await audit(user, "product.bulk_price", None, details=f"{r.modified_count} listings -> ${body.price:.2f} (resubmitted for review)")
    return {"updated": r.modified_count}


@api.post("/vendor/products/bulk-delete")
async def vendor_bulk_delete(body: BulkIdsIn, user=Depends(require_role("vendor"))):
    return await _delete_products({"id": {"$in": body.ids}, "vendor_id": user["id"]}, user, f"{len(body.ids)} selected")


@api.delete("/vendor/products/{pid}")
async def vendor_delete_product(pid: str, user=Depends(require_role("vendor"))):
    return await _delete_products({"id": pid, "vendor_id": user["id"]}, user, pid)


@api.delete("/vendor/batches/{bid}")
async def vendor_delete_batch(bid: str, user=Depends(require_role("vendor"))):
    return await _delete_products({"batch_id": bid, "vendor_id": user["id"]}, user, bid)


@api.get("/vendor/products/{pid}/keys")
async def vendor_list_keys(pid: str, user=Depends(require_role("vendor"))):
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
async def vendor_sales(user=Depends(require_role("vendor"))):
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
        },
        "recent_orders": recent,
    }


@api.get("/admin/deposits")
async def admin_deposits(status: str = "pending", user=Depends(admin_dep)):
    q = {} if status == "all" else {"status": status}
    return await db.deposits.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)


@api.post("/admin/deposits/{did}/approve")
async def admin_approve_deposit(did: str, body: ApproveDepositIn, user=Depends(admin_dep)):
    d = await db.deposits.find_one({"id": did, "status": "pending"}, {"_id": 0})
    if not d:
        raise HTTPException(400, "Deposit not pending")
    credit = to_cents(body.amount) if body.amount else d["amount_cents"]
    d = await db.deposits.find_one_and_update(
        {"id": did, "status": "pending"},
        {"$set": {"status": "approved", "credited_cents": credit, "reviewed_by": user["email"], "reviewed_at": now_iso()}},
        projection={"_id": 0}, return_document=ReturnDocument.AFTER)
    if not d:
        raise HTTPException(400, "Deposit already processed")
    await db.users.update_one({"id": d["user_id"]}, {"$inc": {"balance_cents": credit}})
    await audit(user, "deposit.approve", did, credit, d["user_id"], f"{d['coin']} txid {d['txid']} ref {d['reference']}")
    await notify(d["user_id"], "Deposit approved", f"${credit / 100:.2f} has been credited to your wallet (ref {d['reference']}).",
                 "Deposit approved")
    return d


@api.post("/admin/deposits/{did}/reject")
async def admin_reject_deposit(did: str, body: ReasonIn, user=Depends(admin_dep)):
    d = await db.deposits.find_one_and_update(
        {"id": did, "status": {"$in": ["pending", "awaiting_txid"]}},
        {"$set": {"status": "rejected", "reason": body.reason, "reviewed_by": user["email"], "reviewed_at": now_iso()}},
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
    if upd:
        await db.settings.update_one({"key": "global"}, {"$set": upd})
    return await get_settings()


@api.put("/admin/site")
async def admin_update_site(body: SiteIn, user=Depends(admin_dep)):
    s = await get_settings()
    upd = {}
    if body.notice is not None:
        upd["notice"] = {k: (v.strip() if isinstance(v, str) else v) for k, v in body.notice.model_dump().items()}
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
        await audit(user, "settings.categories", None, details=", ".join(names))
    if upd:
        await db.settings.update_one({"key": "global"}, {"$set": upd})
    return await get_settings()


@api.get("/admin/users")
async def admin_users(q: str = "", role: str = "all", user=Depends(admin_dep)):
    query = {}
    if role != "all":
        query["role"] = role
    if q:
        query["$or"] = [{"email": {"$regex": q, "$options": "i"}}, {"name": {"$regex": q, "$options": "i"}}]
    return await db.users.find(query, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(5000)


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


@api.get("/admin/orders")
async def admin_orders(user=Depends(admin_dep)):
    return await db.orders.find({}, {"_id": 0, "license_key": 0}).sort("created_at", -1).to_list(5000)


@api.get("/admin/audit")
async def admin_audit(action: str = "", user=Depends(admin_dep)):
    q = {"action": {"$regex": f"^{action}"}} if action else {}
    return await db.audit_logs.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)


@api.get("/")
async def root():
    return {"message": "NeonKeys Market API"}


app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
                   allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
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
    try:
        await asyncio.to_thread(init_storage)
        logger.info("Storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")


@app.on_event("shutdown")
async def shutdown():
    client.close()
