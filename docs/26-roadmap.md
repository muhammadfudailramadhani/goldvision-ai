# Roadmap

> Status: **FASE 2 SELESAI PENUH** — seluruh item yang bisa dibangun sudah terimplementasi & terverifikasi (145 test PASS).

- FASE 1 ✅: foundation + simulator + compliance + test (57/57 PASS)
- FASE 2 ✅ (145/145 PASS):
  - Twelve Data / Alpha Vantage / MT5 live (§12)
  - Bot polling nyata + webhook script + secret auth
  - Elliott Wave, 17 chart pattern (pivot asli), 8 indikator kategori (docs/27)
  - Referral end-to-end, backtest walk-forward, /stop, /notifications
  - Admin suite: /admin_stats, /admin_users, /admin_vip (sandbox §18), /admin_broadcast, /admin_scan
  - Auto-signal pipeline: core/signals/scan.py + scripts/auto_signal.py
  - /pnl nyata (delivery-based), /konten (template/AI + guard), callback query buttons
  - CI (GitHub Actions), deployment guide + systemd unit (docs/25)
- FASE 3 sisa (butuh eksternal):
  - Payment gateway asli (butuh kredensial Midtrans/Tripay dkk) — sandbox manual ✅
  - ~~AI asli~~ ✅ AKTIF: NVIDIA NIM (nemotron) via settings ai_* — reasoning-model
    safe (fallback template bila content kosong), guard §28, terverifikasi live
  - Exit-price tracking utk win-rate riil /pnl
  - WhatsApp (§4 — HANYA atas permintaan eksplisit owner)
  - Alembic migration utk PostgreSQL skala besar
