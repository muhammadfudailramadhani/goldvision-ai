"""WhatsApp settings — credential via env, provider DISABLED by default (§8, §31)."""

from app.settings import get_settings

# Batas Cloud API (indikatif, verifikasi ulang saat aktivasi — docs/17-whatsapp-compliance.md)
MESSAGES_PER_SECOND = 80      # throughput default tier
TEMPLATE_WINDOW_HOURS = 24    # §34: customer-service window


def is_enabled() -> bool:
    return get_settings().whatsapp_enabled  # WAJIB false sekarang


def required_credentials() -> list[str]:
    return ["WHATSAPP_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_VERIFY_TOKEN"]
