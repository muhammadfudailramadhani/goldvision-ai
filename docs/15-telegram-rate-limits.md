# Telegram Rate Limits

> Status dokumen: FASE 1 foundation — konten inti terverifikasi; detail diperkaya di fase berikutnya.

- Batas §22: ~1/s per chat, 20/min group, ~30/s bulk
- TokenBucket di rate_limit/bucket.py
- 429 handling §23: honor retry_after, max 3 retry, no bypass
