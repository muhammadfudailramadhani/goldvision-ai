# Roadmap

> Status dokumen: FASE 2 — mayoritas selesai dan terverifikasi test.

- FASE 1 ✅: foundation + simulator + compliance + test (57/57 PASS)
- FASE 2 ✅ (terverifikasi 83/83 PASS):
  - Twelve Data live (`core/market/twelvedata.py`)
  - Alpha Vantage fallback (`core/market/alphavantage.py`) — FX_INTRADAY/FX_DAILY, H4 agregasi H1
  - MT5 provider (`core/market/mt5.py`) — integrasi terminal broker
  - Bot Telegram nyata polling (`scripts/run_telegram.py`)
  - Elliott Wave rule-based (`core/analysis/elliott_wave.py`)
  - Referral end-to-end (`core/referral/`, `/referral`, deep-link `/start <kode>`)
  - Backtest walk-forward (`core/backtest/`, `/backtest`) — docs/12-backtest.md
  - `/stop` opt-out penuh + `/notifications on|off`
- FASE 2 sisa: PostgreSQL prod (compose siap, belum dipakai), deployment (§25)
- FASE 3: payment (§18), AI content asli (§21), WhatsApp aktivasi (atas permintaan §4)
