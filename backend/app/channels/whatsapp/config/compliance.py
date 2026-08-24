"""WhatsApp compliance config (§8) — aturan yang berlaku saat channel diaktifkan."""

# §32: alur wajib sebelum messaging
PIPELINE = [
    "Opt-in",              # izin tereksplicit
    "Messaging Permission",
    "24h Service Window",  # §34
    "Template Handling",
    "Rate Limit",
    "Quality Monitoring",  # §35
    "Opt-out",
    "Suppression",
]

# §35: threshold pause broadcast
QUALITY_THRESHOLDS = {
    "block_rate_pct": 2.0,
    "report_rate_pct": 1.0,
    "failed_rate_pct": 5.0,
}
