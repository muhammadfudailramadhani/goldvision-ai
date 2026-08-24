"""WhatsAppAdapter — implementasi ChannelAdapter, DISABLED by default (§4, §31).

Saat WHATSAPP_ENABLED=false, SEMUA metode kirim menolak dengan ChannelDisabledError.
Interface lengkap & struktur compliance sudah siap — aktivasi nanti tanpa membongkar core.
"""
from app.channels.base import MessageContext

from .config import is_enabled


class ChannelDisabledError(RuntimeError):
    """Channel WhatsApp belum diaktifkan — WHATSAPP_ENABLED=false (§4)."""


class WhatsAppAdapter:
    channel_name = "whatsapp"

    def is_enabled(self) -> bool:
        return is_enabled()

    def _guard(self) -> None:
        if not is_enabled():
            raise ChannelDisabledError(
                "WhatsApp channel DISABLED (WHATSAPP_ENABLED=false). "
                "Aktivasi hanya atas permintaan eksplisit owner — lihat docs/16-whatsapp.md."
            )

    async def send_text(self, chat_id: str, text: str, **kwargs) -> str | None:
        self._guard()
        raise NotImplementedError("FASE aktivasi WhatsApp — transport Cloud API belum diimplementasikan")

    async def send_image(self, chat_id: str, image_path: str, caption: str = "", **kwargs) -> str | None:
        self._guard()
        raise NotImplementedError("FASE aktivasi WhatsApp — transport Cloud API belum diimplementasikan")

    async def send_buttons(self, chat_id: str, text: str, buttons: list, **kwargs) -> str | None:
        self._guard()
        raise NotImplementedError("FASE aktivasi WhatsApp — interactive buttons belum diimplementasikan")

    async def parse_context(self, raw_update: dict) -> MessageContext | None:
        # webhook tetap diparse supaya struktur siap, tapi guard tetap berlaku saat kirim
        msg = raw_update.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {}).get("messages", [{}])[0]
        if not msg:
            return None
        return MessageContext(
            user_id=str(msg.get("from", "")),
            channel="whatsapp",
            message_id=str(msg.get("id", "")),
            text=msg.get("text", {}).get("body", ""),
            chat_id=str(msg.get("from", "")),
        )
