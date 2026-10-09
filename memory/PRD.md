# NeonKeys Market — PRD

## Original problem statement
Multi-vendor, wallet-based B2B marketplace for digital goods (license keys/codes). Buyers top up an internal USD wallet via manual crypto deposits (BTC, USDT TRC20, LTC, ETH), then buy and get keys instantly. Vendors self-serve (signup → admin approval, products, key stock, pricing, sales, earnings, withdrawals). Admin controls approvals, deposit verification, payouts, price override, global 10% + per-vendor commission, crypto addresses, users, analytics, audit log. Dark UI styled after the user's reference screenshots (visual style only). Clean categories: Software Licenses, Templates, Digital Assets, Subscriptions, Courses.

## User choices
- React JS (not TS) for MVP; all phases end-to-end, lean; Resend email + object storage included
- Admin seeded: admin@market.com / Admin@123
- Admin panel has a separate section for each request type (add-funds, withdrawals, vendors, listings)
- Visual style from the user's screenshots: charcoal + green, list cards with an accent bar, account menu, bottom nav

## Architecture
- Backend: FastAPI (`server.py` routes, `core.py` db/auth/email/storage, `seed.py`), MongoDB (uuid `id`, cents integers)
- Auth: JWT Bearer (24h) + bcrypt, roles buyer/vendor/admin, brute-force lockout
- Atomicity: key reserve via find_one_and_update → conditional balance debit → compensation on failure; unique partial index on deposits.txid; unique reference; unique (product_id,key)
- Email: Emergent-managed Resend (fire-and-forget on deposit approved, order confirmation, payouts, vendor status)
- Storage: Emergent Object Storage for product images (/api/upload, /api/files/{path})

## Implemented (2026-06)
- Auth/register (buyer/vendor), account page, notifications
- Marketplace: search, category tabs, sort, featured vendors, /vendors directory, vendor filter
- Wallet: coin dropdown, QR + address, network warning, reference, TXID submit, history, balance log
- Checkout with atomic key delivery, vault (masked/copy), orders
- Vendor dashboard: overview, products (image upload, edit → re-review), key stock, sales, withdrawals
- Admin: overview/analytics, add-fund requests, withdrawal requests, vendor requests (+custom commission), listing requests (+price override), commission & wallet addresses, users (credit/debit, suspend), audit log
- Tested: 22/22 backend tests and the frontend flows passed (iteration_1)

## Backlog
- P1: Real deposit addresses must be set by admin (seeded placeholders)
- P1: Support tickets / disputes, 2FA for admin & vendors
- P2: Blockchain API auto-verification, amount-encoded QR, vendor ratings, file-download delivery, Stripe/PayPal rails
