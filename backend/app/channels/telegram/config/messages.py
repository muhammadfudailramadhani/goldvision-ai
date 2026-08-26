"""Telegram message templates — teks respons bot, BUKAN credentials (§7)."""

WELCOME = """Welcome to GoldVision AI \U0001f3c6\n\nAnalisis Forex real-time via Telegram.\nTipe /help untuk melihat semua command."""

HELP_TEXT = """\U0001f4cb Commands:

/analyze — Analisis live pair
/signals — Sinyal terbaru
/scanner — Cari setup terbaik
/backtest — Uji strategi pada data historis
/konten — Draft konten edukasi pair
/pnl — Ringkasan sinyal diterima 7 hari
/limit — Cek quota
/notifications on|off — Atur notifikasi broadcast
/referral — Kode & statistik referral
/status — Status bot
/subscribe — Info langganan
/menu — Menu utama
/help — Bantuan ini
/stop — Berhenti menggunakan bot

\U0001f5e3 Natural language juga bekerja:
\"Gold sekarang bagaimana?\"
\"Analisa EURUSD\"
\"Backtest gold M15\"
\"Analisa gold dengan rsi macd\"
\"Gold ema bollinger semua indikator\""""

MENU_TEXT = """\U0001f3c6 GoldVision AI\n\nPilih menu:\n"""

QUOTA_EXCEEDED = """\u26a0\ufe0f Quota live analysis habis.\n\n{plan}: {used}/{limit} ({window}).\nUpgrade ke VIP untuk 4 analisis/hari.\nTipe /subscribe untuk info."""

QUOTA_OK = """\u2705 Quota: {used}/{limit} ({window}).\nMenganalisis {pair}..."""

RATE_LIMITED = """\u23f3 Terlalu cepat. Tunggu {retry_after}s dan coba lagi."""

ANALYSIS_FORMAT = """\U0001f3c6 {pair} · {timeframe}\n\n\U0001f4c9 Harga: {price:g}\n\n{trend_block}\n\n\U0001f4ca Skor: {score}/100 — {category}\n{components_block}\n\n\U0001f3af {action}\n{levels_block}"""

SIGNAL_FORMAT = """\U0001f4c8 {direction} {pair}\n\nEntry: {entry:g}\nSL: {sl:g}\nTP1: {tp1:g}\nTP2: {tp2:g}\nScore: {score}/100\nRR: {rr:g}\n\n\u26a0\ufe0f Edukasi, bukan saran finansial."""

SUBSCRIPTION_INFO = """\U0001f3c6 GoldVision AI — Langganan\n\n\U0001f7e2 FREE: 3 analisis/minggu\n\U0001f535 VIP: 4 analisis/hari\n\nMode sandbox: hubungi admin untuk upgrade (aktivasi manual via /admin_vip)."""

NOT_FOUND = """Maaf, perintah tidak dikenali.\nTipe /help untuk melihat command yang tersedia."""

BACKTEST_FORMAT = """\U0001f9ee Backtest {pair} {timeframe}

Bars diuji: {bars} \u00b7 Evaluasi: {evaluations}
Sinyal: {signals} (terisi {filled})

\U0001f7e2 Win: {wins} \u00b7 \U0001f534 Loss: {losses} \u00b7 Open: {open_}
Win rate: {win_rate}%
Total: {total_r} R
Profit factor: {profit_factor}
Max drawdown: {max_dd} R

\u26a0\ufe0f Edukasi & riset \u2014 hasil historis bukan jaminan masa depan."""

BACKTEST_NO_DATA = """\u26a0\ufe0f Data historis {pair} {timeframe} belum cukup untuk backtest (butuh > {min_history} bars)."""

STOP_CONFIRMED = """\U0001f44b Kamu telah berhenti menggunakan GoldVision AI.

Notifikasi dimatikan dan akun dinonaktifkan. Ketik /start kapan saja untuk mulai lagi."""

NOTIFICATIONS_STATUS_ON = """\U0001f514 Notifikasi aktif. Gunakan "/notifications off" untuk mematikan."""

NOTIFICATIONS_STATUS_OFF = """\U0001f515 Notifikasi mati. Gunakan "/notifications on" untuk menyalakan lagi."""

USER_BLOCKED = """\U0001f6ab Pesan tidak terkirim — user tidak aktif atau telah memblokir bot."""

CHANNEL_DISABLED = """GoldVision AI belum tersedia di channel ini."""
