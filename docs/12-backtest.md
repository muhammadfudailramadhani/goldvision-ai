# Backtest

> Status: **FASE 2 — TERIMPLEMENTASI** (`backend/app/core/backtest/`). Terverifikasi test `backend/tests/test_backtest.py`.

## Prinsip

1. **Tidak ada logika sinyal duplikat.** Replay memakai `AnalysisEngine` +
   `evaluate_for_signal` yang sama persis dengan produksi, lewat
   `HistoricalProvider` yang memotong snapshot data pada cutoff waktu evaluasi.
2. **Simulasi pesimis.** Bila SL dan TP tersentuh di bar yang sama, dihitung SL.
3. **Single-exit.** TP1 tercapai = exit penuh di TP1 (tidak mengasumsikan partial TP).
4. **Jujur pada keterbatasan.** Setup yang entry-nya tak pernah tersentuh = EXPIRED;
   setup yang belum selesai saat data habis = OPEN dan tidak masuk metrik closed.

## Cara kerja

```
snapshot 5 TF (D1..M15) -> walk-forward per step_bars:
    cutoff = ts bar ke-i        -> HistoricalProvider.set_cutoff(cutoff)
    AnalysisEngine.analyze()    -> evaluate_for_signal()
    sinyal unik (fingerprint)   -> simulate_trade() ke depan (fill window 12 bar)
```

## Metrik (`BacktestSummary`)

| Metrik | Definisi |
|---|---|
| win_rate_pct | wins / (wins+losses) |
| total_r | akumulasi R semua trade closed (risk 1R = jarak entry-SL) |
| profit_factor | gross win / gross loss; `∞` bila tak pernah loss |
| max_drawdown_r | peak-to-trough terburuk pada kurva kumulatif R |
| expectancy_r | total_r / jumlah trade closed |

## Pemakaian

```bash
# via bot: /backtest <pair> [timeframe] — memakan quota (lebih berat dari 1 live analysis)
/backtest gold m15
"tolong uji historis EURUSD"
```

```python
from app.core.backtest import BacktestEngine
result = await BacktestEngine(provider).run("XAUUSD", "M15")
print(result.summary.win_rate_pct, result.summary.profit_factor)

# snapshot lebih panjang utk lebih banyak titik evaluasi (window analisis tetap 200 bar)
result = await BacktestEngine(provider).run("XAUUSD", "M15", bars=500)
```

## Batasan (didokumentasikan, tidak disembunyikan)

- Mock provider = data sintetis; angka mock BUKAN performa pasar nyata.
  Backtest bermakna hanya dengan data historis/live (Twelve Data, Alpha Vantage, MT5).
- Slippage, spread, swap, dan biaya lain belum dimodelkan.
- Hanya TF tunggal sebagai basis sinyal; multi-TF tetap dipakai untuk konteks analisis.
- **Trade tumpang tindih**: sinyal baru boleh muncul saat trade sebelumnya masih
  berjalan (fingerprint berbeda) — statistik per-setup, bukan simulasi satu posisi.
- **Gap melampaui SL** dicatat tepat -1R; kerugian riil pada gap bisa lebih besar.
