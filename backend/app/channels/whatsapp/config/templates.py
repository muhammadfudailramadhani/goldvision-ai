"""WhatsApp templates (§34) — struktur only, belum dipakai (channel disabled).

Saat aktif nanti: free-form hanya dalam 24h service window; di luar window
wajib template yang approved. Simpan status window per user.
"""

TEMPLATES = {
    "signal_alert": {
        "name": "signal_alert",
        "language": {"code": "id"},
        "components": [{"type": "body", "parameters": [
            {"type": "text", "text": "{{1}}"},   # pair
            {"type": "text", "text": "{{2}}"},   # direction
            {"type": "text", "text": "{{3}}"},   # entry
        ]}],
        "status": "NOT_SUBMITTED",  # belum diajukan ke Meta — channel disabled
    },
}


def render_template(name: str, params: list[str]) -> str:
    """Validasi keberadaan template; rendering nyata = saat channel diaktifkan."""
    if name not in TEMPLATES:
        raise ValueError(f"template {name} tidak terdaftar")
    if len(params) != 3:
        raise ValueError("signal_alert butuh 3 parameter: pair, direction, entry")
    return f"[template:{name}] " + " ".join(params)
