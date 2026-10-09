# NeonKeys Market: install on your own VPS

This sets up the full site on your server, the same as the preview: design, fonts, images, admin panel, wallet, vendors, tickets, and all other features.

## What you need
- A VPS running **Ubuntu 22.04/24.04 or Debian 12**, with at least 2 GB RAM (1 GB works with swap) and root access.
- Optional: a **domain**, such as `market.example.com`, with an **A record** pointing to your VPS IP. You need it for automatic HTTPS.
- Optional: a **Resend API key** (https://resend.com) with a verified sender domain, if you want emails to be sent.

## Install (3 commands)
```bash
git clone https://github.com/YOUR_USER/YOUR_REPO.git neonkeys
cd neonkeys
sudo ./install.sh
```
The installer:
1. Installs Docker if it is missing.
2. Asks for your domain, admin email/password, and Resend key (optional).
3. Offers to **import the bundled data** (products, categories, banners, notice, wallet addresses, accounts) so the site matches the preview.
4. Builds and starts MongoDB, the backend API and the website (Caddy, which handles automatic HTTPS).

When it finishes, open `https://your-domain` (or `http://SERVER_IP` if you left the domain blank).

## Everyday commands
| Task | Command |
|---|---|
| Update after pushing new code to GitHub | `sudo ./deploy/update.sh` |
| Backup database + uploaded images | `sudo ./deploy/backup.sh` |
| Restore a backup | `sudo ./deploy/restore.sh deploy/backups/db-XXXX.archive.gz` |
| View logs | `docker compose -f deploy/docker-compose.yml logs -f backend` |
| Stop / start | `docker compose -f deploy/docker-compose.yml down` / `up -d` |
| Change settings (email, admin password…) | edit `deploy/.env`, then `sudo ./deploy/update.sh` |

## Notes
- **Keep the GitHub repo PRIVATE.** `deploy/initial-data/` contains a copy of the preview database (user accounts with hashed passwords, products and license keys).
- After importing data, the demo accounts `buyer@market.com / Buyer@123` and `vendor@market.com / Vendor@123` exist. Suspend them in Admin → Users, or change their passwords.
- If you chose an admin email other than `admin@market.com`, the imported `admin@market.com` account is disabled automatically.
- Uploaded images are stored on the VPS in `deploy/data/uploads` (included in backups).
- Emails: set `EMAIL_PROVIDER=resend`, `RESEND_API_KEY` and `EMAIL_FROM` (from a domain verified in Resend) in `deploy/.env`. With `EMAIL_PROVIDER=none`, emails are skipped and in-app notifications still work.
- Older VPS CPUs without AVX can't run MongoDB 7. The installer detects this and uses `mongo:4.4`.
- Open ports **80** and **443** in your VPS firewall (for example `ufw allow 80,443/tcp`).
