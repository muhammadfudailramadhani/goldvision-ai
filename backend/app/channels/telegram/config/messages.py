"""Telegram message templates — teks respons bot, BUKAN credentials (§7)."""

WELCOME = """Welcome to GoldVision AI \U0001f3c6\n\nAnalisis Forex real-time via Telegram.\nTipe /help untuk melihat semua command."""

HELP_TEXT = """\U0001f4cb Commands:\n\n/analyze — Analisis live pair\n/signals — Sinyal terbaru\n/scanner — Cari setup terbaik\n/pnl — Ringkasan PNL\n/limit — Cek quota\n/status — Status bot\n/subscribe — Info langganan\n/menu — Menu utama\n/help — Bantuan ini\n\n\U0001f5e3 Natural language juga bekerja:\n\"Gold sekarang bagaimana?\"\n\"Analisa EURUSD\""""

MENU_TEXT = """\U0001f3c6 GoldVision AI\n\nPilih menu:\n"""

QUOTA_EXCEEDED = """\u26a0\ufe0f Quota live analysis habis.\n\n{plan}: {used}/{limit} ({window}).\nUpgrade ke VIP untuk 4 analisis/hari.\nTipe /subscribe untuk info."""

QUOTA_OK = """\u2705 Quota: {used}/{limit} ({window}).\nMenganalisis {pair}..."""

RATE_LIMITED = """\u23f3 Terlalu cepat. Tunggu {retry_after}s dan coba lagi."""

ANALYSIS_FORMAT = """\U0001f3c6 {pair} · {timeframe}\n\n\U0001f4c9 Harga: {price:g}\n\n{trend_block}\n\n\U0001f4ca Skor: {score}/100 — {category}\n{components_block}\n\n\U0001f3af {action}\n{levels_block}"""

SIGNAL_FORMAT = """\U0001f4c8 {direction} {pair}\n\nEntry: {entry:g}\nSL: {sl:g}\nTP1: {tp1:g}\nTP2: {tp2:g}\nScore: {score}/100\nRR: {rr:g}\n\n\u26a0\ufe0f Edukasi, bukan saran finansial."""

SUBSCRIPTION_INFO = """\U0001f3c6 GoldVision AI — Langganan\n\n\U0001f7e2 FREE: 3 analisis/minggu\n\U0001f535 VIP: 4 analisis/hari\n\nHubungi admin untuk upgrade."""

NOT_FOUND = """Maaf, perintah tidak dikenali.\nTipe /help untuk melihat command yang tersedia."""

USER_BLOCKED = """\U0001f6ab Pesan tidak terkirim — user tidak aktif atau telah memblokir bot."""

CHANNEL_DISABLED = """GoldVision AI belum tersedia di channel ini."""
