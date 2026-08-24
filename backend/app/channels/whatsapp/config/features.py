"""WhatsApp feature flags — semuanya OFF (§31)."""

from app.settings import get_settings


def is_enabled() -> bool:
    return get_settings().whatsapp_enabled


def quality_monitoring_enabled() -> bool:
    # §35: saat aktif nanti, quality monitoring wajib jalan
    return is_enabled()


def opt_in_required() -> bool:
    """§32/§33: opt-in WAJIB sebelum mengirim apa pun."""
    return True
