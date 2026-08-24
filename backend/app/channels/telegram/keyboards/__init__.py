"""Keyboards — struktur data tombol, adapter yang menentukan bentuk platform spesifik."""

MAIN_MENU = [
    [{"text": "\U0001f4c8 Analyze Gold", "callback": "analyze:XAUUSD"},
     {"text": "\U0001f4c9 Analyze EURUSD", "callback": "analyze:EURUSD"}],
    [{"text": "\U0001f50d Scanner", "callback": "scanner"},
     {"text": "\U0001f4b0 PNL", "callback": "pnl"}],
    [{"text": "\u26a1 Limit", "callback": "limit"},
     {"text": "\u2139\ufe0f Subscribe", "callback": "subscribe"}],
]

NOTIFICATION_MENU = [
    [{"text": "Auto Signal: ON/OFF", "callback": "notif:auto_signal"}],
    [{"text": "Daily Summary: ON/OFF", "callback": "notif:daily_summary"}],
    [{"text": "Promotional: ON/OFF", "callback": "notif:promo"}],
]


def format_inline(rows: list) -> str:
    """Representasi teks untuk simulator/testing."""
    lines = []
    for row in rows:
        lines.append(" | ".join(b["text"] for b in row))
    return "\n".join(lines)
