# Oracle Cloud Always Free — Complete Deployment Guide

Deploy Smartdecision on a **permanently free** Oracle Cloud VM (Ampere A1:
4 ARM cores, 24 GB RAM, 200 GB storage, ~10 TB egress/month). The VM never
sleeps — this is the only free tier with a real always-on server.

## 1. Create the VM (once, ~15 min)

1. Go to https://cloud.oracle.com and sign up (may ask for a card for
   identity — you are never charged while staying inside Always Free limits).
2. Create a **Compute → Instances → Create instance**:
   - Image: **Ubuntu 24.04** (or 22.04)
   - Shape: **Ampere A1** — set OCPU = 4, RAM = 24 GB (Always Free eligible)
   - Add your **SSH public key** (download the key pair or paste yours)
   - Keep the default VCN/subnet; assign a **public IPv4 address**
3. **Open the firewall (VCN security list):** in the subnet's security list,
   add ingress rules for **TCP 22, 80, 443** (source `0.0.0.0/0`).

## 2. Deploy (copy-paste, ~5 min)

SSH into the VM (from your machine — note: `bash -c` with curl pipes the
script, and the args after `--` pass the domain):

```bash
ssh -i your-key.pem ubuntu@<VM_PUBLIC_IP>

sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/arpitsingh40/Smartdecision/main/deploy/oracle/setup.sh)" -- smartdecigen.com
```

The script: installs Docker + Caddy, opens the firewall, clones the repo to
`/opt/smartdecision`, generates a random `JWT_SECRET`, writes a `.env`,
configures Caddy for your domain with free Let's Encrypt HTTPS, builds and
starts the app. **The app starts in DRY-RUN mode** (`DRY_RUN=1`) so nothing
executes autonomously until you flip it off.

## 3. Add secrets

```bash
sudo nano /opt/smartdecision/.env
```

Set at minimum:
- `MONGO_URL` — your **MongoDB Atlas** connection string (or use the local
  Mongo fallback: `mongodb://mongo:27017/smartdecision` and run
  `sudo docker compose -f /opt/smartdecision/docker-compose.yml --profile local-mongo up -d`)
- `DEEPSEEK_API_KEY` — your DeepSeek key
- Optional connectors: `STRIPE_API_KEY`, `GMAIL_ACCESS_TOKEN`, `GITHUB_TOKEN`, `COMPOSIO_API_KEY`...

Then apply:

```bash
sudo bash /opt/smartdecision/deploy/oracle/update.sh
```

## 4. Point the domain (DNS)

At your DNS provider (wherever `smartdecigen.com` is hosted — it currently
points at the deleted Railway app):

- `A` record: `smartdecigen.com` → `<VM_PUBLIC_IP>`
- `A` record: `www` → `<VM_PUBLIC_IP>`

Caddy auto-issues/renews HTTPS certificates; the site goes live within
minutes of DNS propagation.

## 5. Verify

```bash
curl -fsS https://smartdecigen.com/api/health
```

Expect a JSON health response. Open `https://smartdecigen.com` in a browser.

## Updates

```bash
sudo bash /opt/smartdecision/deploy/oracle/update.sh   # git pull + rebuild + reload
```

## Operations cheat sheet

```bash
# Logs
sudo docker compose -f /opt/smartdecision/docker-compose.yml logs -f backend

# Restart / stop / start
sudo docker compose -f /opt/smartdecision/docker-compose.yml restart backend

# Kill switch (halt ALL autonomous execution instantly, no rebuild needed)
sudo docker exec -it <backend-container> sh -c 'echo KILL_SWITCH=1 >> /proc/1/environ'  # alternative: restart with env
# Cleaner: set KILL_SWITCH=1 in .env then run update.sh

# Backups (MongoDB Atlas does automatic backups; for local Mongo):
sudo docker compose -f /opt/smartdecision/docker-compose.yml exec mongo mongodump --archive=/backup.dump
```

## Cost check

Everything above stays free: Ampere A1 instance, public IP, storage, and
egress within Always Free limits. MongoDB Atlas M0 (free cluster) for the DB
(choose Atlas only if you need the 3rd replica; local Mongo also works).

## Security notes

- Only ports 22/80/443 are open; the app port 8000 is bound to `127.0.0.1`
  and only reachable through Caddy's HTTPS.
- Start with `DRY_RUN=1` (default in `.env.example`); flip to `DRY_RUN=0`
  only after you confirm the automation loops behave.
- Set `WEEKLY_SPEND_CAP_INR` before enabling autonomous execution.