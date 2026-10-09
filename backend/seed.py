import os
from core import db, COINS, now_iso, new_id, hash_password, verify_password

IMG = {
    "Software Licenses": "https://images.unsplash.com/photo-1608742213509-815b97c30b36?w=800&q=80",
    "Templates": "https://images.unsplash.com/photo-1720962158937-7ea890052166?w=800&q=80",
    "Digital Assets": "https://images.unsplash.com/photo-1705510144116-cc4d88838b14?w=800&q=80",
    "Subscriptions": "https://images.unsplash.com/photo-1663811459413-e9de4614f88f?w=800&q=80",
    "Courses": "https://images.unsplash.com/photo-1645395759348-a0dd7ccf1602?w=800&q=80",
}

DEMO_PRODUCTS = [
    ("Pro Code Editor — 1 Year License", "Software Licenses", 29.0, "Full-featured IDE license key, 1 seat, 12 months of updates."),
    ("Vector Suite Lifetime Key", "Software Licenses", 79.0, "Lifetime license for a professional vector design suite."),
    ("SaaS Dashboard UI Kit", "Templates", 19.0, "120+ dark-mode dashboard screens. Redemption code for download portal."),
    ("Landing Page Template Pack", "Templates", 12.0, "15 responsive landing page templates. Code redeemable on vendor portal."),
    ("Neon 3D Icon Pack", "Digital Assets", 9.0, "500 3D neon icons in PNG/SVG. Redemption code included."),
    ("Cloud Storage 2TB — 12 Months", "Subscriptions", 49.0, "Activation code for 2TB cloud storage, 12 months."),
    ("VPN Business — 6 Months", "Subscriptions", 24.0, "Business VPN activation code, 5 devices, 6 months."),
    ("Full-Stack Bootcamp Access", "Courses", 39.0, "Lifetime access voucher for a 60-hour full-stack course."),
]


async def _upsert_user(email, password, **fields):
    u = await db.users.find_one({"email": email})
    if u is None:
        doc = {"id": new_id(), "email": email, "password_hash": hash_password(password), "balance_cents": 0,
               "status": "active", "created_at": now_iso(), **fields}
        await db.users.insert_one(doc)
        return doc, True
    if not verify_password(password, u["password_hash"]):
        await db.users.update_one({"email": email}, {"$set": {"password_hash": hash_password(password)}})
    return u, False


async def seed_all():
    if not await db.settings.find_one({"key": "global"}):
        await db.settings.insert_one({"key": "global", "commission_pct": 10.0,
                                      "addresses": {c: f"REPLACE_WITH_YOUR_{c}_ADDRESS" for c in COINS}})
    await _upsert_user(os.environ["ADMIN_EMAIL"].lower(), os.environ["ADMIN_PASSWORD"], name="Admin", role="admin")
    await _upsert_user("buyer@market.com", "Buyer@123", name="Demo Buyer", role="buyer")
    vendor, created = await _upsert_user("vendor@market.com", "Vendor@123", name="Demo Vendor", role="vendor",
                                         vendor_status="approved", store_name="NeonSoft Labs",
                                         earnings_cents=0, commission_pct=None)
    if created:
        for i, (title, cat, price, desc) in enumerate(DEMO_PRODUCTS):
            pid = new_id()
            await db.products.insert_one({
                "id": pid, "vendor_id": vendor["id"], "vendor_name": "NeonSoft Labs", "title": title,
                "description": desc, "category": cat, "price_cents": int(price * 100),
                "vendor_price_cents": int(price * 100), "image": IMG[cat], "status": "approved",
                "stock_count": 5, "sales_count": 0, "created_at": now_iso(), "approved_at": now_iso(),
                "tags": ["instant", "global", cat.split()[0].lower()], "delivery_type": "keys",
                "delivery_content": "Thanks for your purchase! Redeem your key on the official product portal. Keep it private."})
            for k in range(5):
                await db.license_keys.insert_one({
                    "id": new_id(), "product_id": pid, "vendor_id": vendor["id"],
                    "key": f"NK{i}{k}-{new_id()[:4].upper()}-{new_id()[:4].upper()}-{new_id()[:4].upper()}",
                    "status": "available", "created_at": now_iso()})
