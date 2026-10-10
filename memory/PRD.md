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

## Iteration 5 (2026-06)
- Slimmer UI site-wide: root font-size 14px (all rem sizing ~12% smaller), lighter weights (bold->600, semibold->500), smaller page titles, prices and the account menu

## Iteration 6 (2026-06)
- Admin "Shop notice & categories" section: edit the shop notice (show/hide, color tone, title, message, highlight line, live preview) and manage categories (add, rename which moves existing products, reorder, remove only when unused)
- Categories are now dynamic (settings.categories) and used by the shop tabs, product form and bulk import; GET /api/site, PUT /api/admin/site
- Tested: 100% of backend + frontend checks for this feature (iteration_5)

## Iteration 7 (2026-06)
- Admin "Shop content": Marketplace header (title, subtitle with {count}, background image upload/URL, show/hide), promo banners (CRUD, reorder, live toggle, image upload, safe internal/external links, auto-sliding carousel), category icon (24 options) + color per tab, notice scheduling (show from / hide after, server-evaluated `active`)
- Generated hero and banner images (green glass-cube vibe)

## Iteration 8 (2026-06)
- Admin manual deposit (Add-fund requests -> "Add funds manually": email, amount, coin, optional TXID (uniqueness enforced, case-insensitive), note), credited instantly with notification, email and audit
- Admin "My store (sell)": embedded vendor dashboard; admin listings are auto-approved, sold as "NeonKeys Official", 100% platform revenue
- Sold-out products are hidden from the shop list, facets, product count and vendor product counts (the product page stays reachable by direct link)
- Banner text was already editable in Shop content -> Promo banners

## Iteration 9 (2026-06)
- Auth split: /login and /register are buyer-only (role toggle removed) with an "Are you a vendor? Vendor login" link; /vendor/login and /vendor/register are the vendor portal (badge, store name required, role=vendor), with a "Not a vendor? Buyer login" link back

## Iteration 10 (2026-06)
- Admin "User details" section: searchable/filterable user list (name, email, role, balance); click a row to expand balance, products bought (grouped with count + spent), total spent, deposited, recent deposits, plus Add balance / Deduct
- GET /api/admin/users/{uid}/details (hides license keys/delivery content)
- Fixed the wallet adjust dialog (old 2-step prompt closed itself after step 1) -> single amount + reason dialog, shared with the Users tab

## Iteration 11 (2026-06)
- Support tickets + floating green chat button (/support, admin "Support tickets" section, notifications on reply) — iteration_8 100%
- Self-hosted VPS bundle: install.sh (Docker, prompts, data import), deploy/docker-compose.yml (mongo, backend, Caddy web with auto HTTPS), deploy/{backend,web}.Dockerfile, Caddyfile, update/backup/restore scripts, VPS_INSTALL.md, deploy/initial-data DB dump
- Backend env switches: STORAGE_MODE (emergent|local), EMAIL_PROVIDER (emergent|resend|none), SEED_DEMO; hero/banner images now bundled at /assets/

## Iteration 12 (2026-06)
- Change password for every account (Account → Change password); env admin password no longer overwrites a UI-changed password on restart (password_changed_at)
- Admin quick replies in support tickets (5 defaults, {name}/{ref} placeholders, manage dialog) stored in settings.canned_replies
- Ticket screenshot attachments (up to 4 per message, 5MB, private: owner/admin only via /api/tickets/files)
- Tested: 100% backend + frontend (iteration_9)
- Iteration 13: bulk import splits "Label: value" fields even on one line, vendor taps "Name" on 1-3 fields (auto-guesses Product/Name/Title), product name uses field values without labels (e.g. "GameForge Runtime License")
- Iteration 14: Admin panel redesigned as tile boxes (Website builder box, Requests, Manage) with ?s= deep links, back button + jump select. Website builder: Name & colors (brand name parts, logo icon, tab title, official store name; 7 theme presets + 8 editable colors via CSS variables --nk-*), Home sections (reorder/hide built-ins, add/edit/delete text & image and columns sections), Footer (columns + links + bottom text). Tested 100% (iteration_10)
- Iteration 15: Custom fonts (heading/body/mono from curated Google Fonts lists, 6 font pairs, live preview) in Admin → Name, colors & fonts; CSS vars --nk-font-*
