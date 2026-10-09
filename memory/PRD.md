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

## Iteration 2 (2026-06)
- Math captcha (server-side, single-use, 10-min TTL) on login + register, drawn as a distorted canvas image with a refresh button
- Login/register restyled after the user's reference (centered brand, icon inputs, password eye, confirm password, big green CTA)
- Product form: buyer-facing section (title, category, price, description, tags) and a private "what buyers receive" delivery box
- Delivery types: unique key per buyer (stock) or same content for every buyer (unlimited); delivery content hidden from public APIs, shown after purchase + in vault
- Default cover images (5 presets; category default applied automatically if none chosen)
- Admin listing Preview shows the private delivery content before approval
- Tested: 30/30 backend tests and 100% of frontend flows passed (iteration_2)

## Backlog
- P1: Real deposit addresses must be set by admin (seeded placeholders)
- P1: Support tickets / disputes, 2FA for admin & vendors
- P2: Blockchain API auto-verification, amount-encoded QR, vendor ratings, file-download delivery, Stripe/PayPal rails

## Iteration 3 (2026-06)
- Vendor bulk import (3 steps): paste a sample item, pick separator (dashes / blank line / custom), mark Public/Hidden lines plus a title line, choose delivery (all lines / hidden only), set batch price, category, tags, image, then paste or upload a .txt/.csv; preview, then each item becomes its own pending listing (stock 1); duplicates skipped
- Admin "Approve batch" for pending batch items; permanent delete (vendor per product/batch, admin per product), which removes unsold keys and keeps past orders
- Cards show the public preview lines; multi-line items are blurred in the vault until revealed
- Tested: 38/38 backend tests and 100% of frontend flows passed (iteration_3)

## Iteration 4 (2026-06)
- Vendor multi-select (row checkboxes, select all, select batch), with bulk Set price (sends listings back to admin review) and bulk Delete (permanent)
- Buyer filters: public "Key: Value" lines from bulk imports become attributes; the marketplace shows a dropdown per key (e.g. Region) with counts and AND filtering; GET /api/products/facets, /api/products?attrs=JSON
- Tested: 52/52 backend tests and 100% of frontend flows passed (iteration_4)
