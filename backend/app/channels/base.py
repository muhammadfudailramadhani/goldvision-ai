"""Channel adapter interface (§6) — kontrak yang dipenuhi TelegramAdapter & WhatsAppAdapter.

Core engine hanya berinteraksi dengan ChannelAdapter, bukan platform spesifik.
"""
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class MessageContext:
    user_id: str
    channel: str       # "telegram" | "whatsapp"
    message_id: str
    text: str
    chat_id: str = ""
    is_admin: bool = False
    callback_id: str | None = None  # id callback_query (untuk answerCallbackQuery)


@runtime_checkable
class ChannelAdapter(Protocol):
    channel_name: str

    async def send_text(self, chat_id: str, text: str, **kwargs) -> str | None:
        """Kirim teks. Return message_id channel atau None."""
        ...

    async def send_image(self, chat_id: str, image_path: str, caption: str = "", **kwargs) -> str | None:
        """Kirim gambar. Return message_id channel atau None."""
        ...

    async def send_buttons(self, chat_id: str, text: str, buttons: list, **kwargs) -> str | None:
        """Kirim teks + inline/reply keyboard. Return message_id channel atau None."""
        ...

    async def parse_context(self, raw_update: object) -> MessageContext | None:
        """Parse raw platform update jadi MessageContext. Return None jika bukan pesan relevan."""
        ...

    def is_enabled(self) -> bool:
        ...
