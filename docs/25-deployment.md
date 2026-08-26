# Deployment Produksi (FASE 2+)

> Status: panduan lengkap siap pakai. WhatsApp tetap DISABLED (§4) sampai diminta owner.

## Opsi A — VPS + systemd (polling, paling sederhana)

1. Provision VPS Ubuntu 22.04+ (1 vCPU/1GB cukup), buat user `goldvision`.
2. Clone repo + venv:
   ```bash
   git clone https://github.com/muhammadfudailramadhani/goldvision-ai.git /opt/goldvision-ai
   cd /opt/goldvision-ai && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
   ```
3. Isi `.env` (TELEGRAM_BOT_TOKEN, TWELVEDATA_API_KEY, TELEGRAM_ADMIN_ID, dst).
4. Pasang service:
   ```bash
   sudo cp deploy/goldvision.service /etc/systemd/system/
   sudo systemctl daemon-reload && sudo systemctl enable --now goldvision
   sudo journalctl -u goldvision -f
   ```

## Opsi B — Docker Compose (API + PostgreSQL)

```bash
docker compose up -d --build      # app :8000 + postgres :5432
```
Catatan: compose menjalankan FastAPI (webhook mode), bukan polling.
Skema DB dibuat otomatis oleh SQLAlchemy; `database/schema.sql` = referensi.

## Webhook (alternatif polling)

```bash
python scripts/set_webhook.py --set https://domainmu.com/webhook/telegram
python scripts/set_webhook.py --info
```
WAJIB isi `TELEGRAM_WEBHOOK_SECRET` di .env (server cek header secret, 401 bila salah).

## Auto-signal scheduler (terpisah dari bot)

```bash
python scripts/auto_signal.py --interval 900   # atau --once via cron
```

## Checklist go-live
- [ ] TELEGRAM_BOT_TOKEN valid (getMe OK)
- [ ] TELEGRAM_ADMIN_ID diisi (untuk /admin_*)
- [ ] TELEGRAM_WEBHOOK_SECRET bila webhook
- [ ] MARKET_DATA_MODE: mt5 (unlimited, butuh terminal) / twelvedata / alphavantage
- [ ] Backup goldvision.db (sqlite) atau pg_dump
- [ ] `pytest` + `scripts/test_compliance.py` hijau di server
