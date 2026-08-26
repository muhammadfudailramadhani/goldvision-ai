# Chart Patterns & Indikator Teknikal

> Status: **FASE 2+ — TERIMPLEMENTASI** (`core/analysis/patterns.py`, `core/analysis/indicators.py`).
> Semua nilai dihitung dari candle ASLI; garis/kurva digambar pada pivot asli.

## Pola Chart (17)

| Keluarga | Pola | Arah |
|---|---|---|
| Segitiga | Ascending / Descending / Symmetrical Triangle | Bullish / Bearish / Netral |
| Wedge | Rising / Falling Wedge | Bearish / Bullish |
| Channel | Channel Up / Down, Rectangle | Bullish / Bearish / Netral |
| Reversal | Double Top / Bottom, Triple Top / Bottom, Head & Shoulders (+inverse) | Bearish / Bullish |
| Kontinuasi | Bull Flag / Bear Flag, Pennant, Cup & Handle | sesuai tiang |

Aturan mutlak:
1. Garis & kurva DITITIKKAN pada pivot asli (`find_pivots`) — bentuk selalu sesuai data.
2. Tidak ada pola lolos aturan = tidak dilaporkan (anti-karangan).
3. Confidence = f(touches garis, kualitas struktur); maksimal 3 pola per chart.
4. Cup & Handle dengan handle terlalu dalam (>45% cup) = DITOLAK jujur.

## Indikator (8 kategori pilihan)

`sma` · `ema` · `bb` (Bollinger) · `rsi` · `macd` · `stoch` (Stochastic) · `obv` · `atr`

- Overlay (di chart utama): SMA 20/50, EMA 9/21, Bollinger 20/2
- Panel osilator (di bawah chart): RSI, MACD, Stochastic, OBV, ATR
- Nilai awal sebelum periode terbentuk = `None` (jujur, bukan 0)
- RSI netral 50 saat tidak ada pergerakan; batas 0–100 dijaga

## Cara Pakai

```
analisa gold dengan rsi macd        -> chart + panel RSI & MACD + ringkasan angka
/analyze eurusd ema bollinger       -> overlay EMA + BB
gold semua indikator                -> seluruh 8 kategori
/backtest gold h1                   -> backtest (pola ikut terdeteksi per evaluasi)
```

Ringkasan indikator di balasan = FAKTA angka + status zona (jenuh beli/jual),
ditandi eksplisit "bukan saran finansial" (§28 anti-klaim).
