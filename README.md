# GoldVision AI

Telegram AI Forex Analyst — **Telegram-first, WhatsApp disiapkan tapi DISABLED**, full localhost.

> **Prinsip build**: BUILD → DOCUMENT → TEST → VERIFY → FIX. Fitur dianggap selesai hanya jika
> CODE + TEST + DOCUMENTATION + LOCAL RUN + LOCAL VERIFICATION + COMPLIANCE CHECK (§53).

## Status: FASE 2 — Live Data & Fitur ✅

| Komponen | Status |
|---|---|
| Repository structure (§3) | ✅ |
| Core engine (analysis/scoring/signal/quota/pnl/chart) | ✅ mock mode |
| Telegram adapter + handler + NL intent | ✅ SimulatedTransport + polling nyata |
| Compliance engine universal + telegram | ✅ 9/9 skenario PASS |
| Rate limiter + broadcast queue + 429 handling | ✅ |
| WhatsApp folder | ✅ struktur siap, DISABLED |
| FastAPI skeleton | ✅ /health /api/analyze |
| Database (SQLite dev / PostgreSQL prod) | ✅ |
| Elliott Wave rule-based | ✅ FASE 2 |
| Referral end-to-end (/referral, deep-link) | ✅ FASE 2 |
| Twelve Data / Alpha Vantage / MT5 live | ✅ FASE 2 |
| Backtest walk-forward (/backtest) | ✅ FASE 2 |
| 17 chart pattern (pivot asli) + 8 indikator | ✅ FASE 2+ (docs/27) |
| Bot Telegram nyata (polling/webhook) | ✅ polling (`scripts/run_telegram.py`) |
| Payment / AI content asli | 🔒 FASE 3 |
| WhatsApp aktivasi, deployment prod | 🔒 FASE 3 / atas permintaan |

## Arsitektur (§2, §58)

```
Telegram Channel → Telegram Adapter → Application Layer → Core Engine → Database
                                              ↑
WhatsApp (DISABLED) → WhatsApp Adapter ───────┘
```

**Core engine tidak berisi logic platform** — tidak ada `TelegramAnalysisEngine`.
Hanya ada: `AnalysisEngine`, `SignalEngine`, `ScoringEngine`, `PnlEngine`,
`QuotaService`, `SubscriptionService`. Channel = adapter yang bisa diganti.

## Quickstart (localhost, tanpa API key apa pun)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

# 1. Jalankan test suite (semua harus PASS)
pytest backend/tests -v

# 2. Simulator pesan Telegram (§48)
python scripts/simulate_message.py "Gold sekarang bagaimana?"

# 3. Simulator compliance — 8 skenario (§49)
python scripts/test_compliance.py

# 4. Simulator broadcast 100 user (§50)
python scripts/demo_broadcast.py --users 100

# 5. API developer preview
uvicorn app.main:app --app-dir backend --reload
#    → http://localhost:8000/health  |  /docs  |  POST /api/analyze {"pair":"XAUUSD"}
```

Chart hasil analysis tersimpan di `generated/charts/xauusd_m15.png` (dark terminal style, §11).

## Environment

Salin `.env.example` → `.env`. **Semua credential via env, tidak pernah hardcode (§29).**
Mode localhost default: `MARKET_DATA_MODE=mock`, `AI_MODE=mock`, `PAYMENT_MODE=sandbox`,
`TELEGRAM_ENABLED=true`, `WHATSAPP_ENABLED=false` (§4 — WhatsApp diaktifkan hanya atas
permintaan eksplisit owner).

## Compliance & Account Health (§57)

Ini **bukan** sistem anti-ban. Fungsinya mencegah GoldVision mengirim pesan ketika
pengiriman berpotensi melanggar consent, rate limit, user preference, duplicate policy,
atau platform rules. Lapisan wajib sebelum setiap send (§37):

```
Consent → Preference → Suppression → Rate Limit → Duplicate → Channel Policy → Queue → Send → Log
```

Yang TIDAK pernah dibangun (§38): delay acak untuk menghindari deteksi, rotasi bot/token,
proxy rotation, fake user, kontak scraping, mass unsolicited messaging.

## Testing

```bash
pytest backend/tests -v          # unit + integration + e2e handler
python scripts/test_compliance.py # 9 skenario compliance §49
python scripts/demo_broadcast.py --users 1000 --with-429  # §46 stress
```

## Dokumentasi

Lihat `docs/00-overview.md` sampai `docs/26-roadmap.md` (§51).

## Lisensi & Disclaimer

Edukasi & riset — bukan saran finansial. Trading mengandung risiko.
