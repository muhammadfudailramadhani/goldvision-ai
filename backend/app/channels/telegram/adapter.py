"""TelegramAdapter — implementasi ChannelAdapter untuk Telegram.

Transport nyata (Bot API via httpx) = FASE 2 saat bot token dipasang.
Untuk foundation + localhost, adapter berjalan penuh lewat SimulatedTransport
yang merekam pesan tanpa pernah menyentuh Telegram production.
"""
from dataclasses import dataclass, field

from app.channels.base import MessageContext

from .config.features import is_admin, is_enabled


class TransportError(RuntimeError):
    pass


@dataclass
class SimulatedTransport:
    """Merekam pesan keluar — untuk simulator & test, tidak pernah kirim nyata."""
    sent: list = field(default_factory=list)

    def send_message(self, chat_id: str, text: str, **kwargs) -> str:
        self.sent.append({"chat_id": chat_id, "text": text, "kind": "text", **kwargs})
        return f"sim-{len(self.sent)}"

    def send_photo(self, chat_id: str, photo_path: str, caption: str = "", **kwargs) -> str:
        self.sent.append({"chat_id": chat_id, "text": caption, "photo": photo_path,
                          "kind": "photo", **kwargs})
        return f"sim-{len(self.sent)}"

    def raise_429(self, retry_after: float = 3.0) -> None:
        from .delivery.queue import RetryAfterError
        raise RetryAfterError(retry_after)

    def answer_callback_query(self, callback_query_id: str, text: str = "") -> None:
        pass  # simulator: tidak ada loading spinner yang perlu dihentikan


@dataclass
class HttpTransport:
    """Bot API nyata — FASE 2. Token WAJIB via env TELEGRAM_BOT_TOKEN (§29)."""
    token: str
    api_base: str = "https://api.telegram.org"

    def _url(self, method: str) -> str:
        if not self.token:
            raise TransportError("TELEGRAM_BOT_TOKEN kosong — jangan pernah hardcode token (§29)")
        return f"{self.api_base}/bot{self.token}/{method}"

    def send_message(self, chat_id: str, text: str, **kwargs) -> str:
        import httpx
        resp = httpx.post(self._url("sendMessage"), json={"chat_id": chat_id, "text": text, **kwargs})
        data = resp.json()
        if resp.status_code == 429:
            from .delivery.queue import RetryAfterError
            raise RetryAfterError(float(data.get("parameters", {}).get("retry_after", 5)))
        resp.raise_for_status()
        return str(data.get("result", {}).get("message_id", ""))

    def send_photo(self, chat_id: str, photo_path: str, caption: str = "", **kwargs) -> str:
        import httpx
        with open(photo_path, "rb") as fh:
            resp = httpx.post(self._url("sendPhoto"),
                              data={"chat_id": chat_id, "caption": caption},
                              files={"photo": fh})
        data = resp.json()
        if resp.status_code == 429:
            from .delivery.queue import RetryAfterError
            raise RetryAfterError(float(data.get("parameters", {}).get("retry_after", 5)))
        resp.raise_for_status()
        return str(data.get("result", {}).get("message_id", ""))

    def answer_callback_query(self, callback_query_id: str, text: str = "") -> None:
        import httpx
        try:
            httpx.post(self._url("answerCallbackQuery"),
                       json={"callback_query_id": callback_query_id, "text": text},
                       timeout=10.0)
        except Exception:
            pass  # spinner hilang sendiri; jangan gagalkan alur karena ini


class TelegramAdapter:
    channel_name = "telegram"

    def __init__(self, transport=None):
        from app.settings import get_settings
        if transport is not None:
            self.transport = transport
        elif get_settings().telegram_bot_token:
            self.transport = HttpTransport(get_settings().telegram_bot_token)
        else:
            self.transport = SimulatedTransport()

    def is_enabled(self) -> bool:
        return is_enabled()

    async def send_text(self, chat_id: str, text: str, **kwargs) -> str | None:
        return self.transport.send_message(chat_id, text, **kwargs)

    async def send_image(self, chat_id: str, image_path: str, caption: str = "", **kwargs) -> str | None:
        return self.transport.send_photo(chat_id, image_path, caption, **kwargs)

    async def send_buttons(self, chat_id: str, text: str, buttons: list, **kwargs) -> str | None:
        return self.transport.send_message(chat_id, text, buttons=buttons, **kwargs)

    async def parse_context(self, raw_update: dict) -> MessageContext | None:
        """Parse update object Telegram (message / edited_message / callback_query).

        Murni parsing — TANPA side effect; consent dicatat satu tempat
        (handler START branch) supaya tidak double-write per /start.
        Callback data dipetakan ke teks command yang setara.
        """
        msg = raw_update.get("message") or raw_update.get("edited_message")
        if msg:
            user = msg.get("from") or {}
            text = msg.get("text", "")
            return MessageContext(
                user_id=str(user.get("id", "")),
                channel="telegram",
                message_id=str(msg.get("message_id", "")),
                text=text,
                chat_id=str(msg.get("chat", {}).get("id", "")),
                is_admin=is_admin(str(user.get("id", ""))),
            )

        cb = raw_update.get("callback_query")
        if cb:
            data = str(cb.get("data", ""))
            text = _callback_to_text(data)
            user = cb.get("from") or {}
            return MessageContext(
                user_id=str(user.get("id", "")),
                channel="telegram",
                message_id=str(cb.get("id", "")),
                text=text,
                chat_id=str(cb.get("message", {}).get("chat", {}).get("id", "")),
                is_admin=is_admin(str(user.get("id", ""))),
                callback_id=str(cb.get("id", "")),
            )
        return None


def _callback_to_text(data: str) -> str:
    """'analyze:XAUUSD' -> '/analyze XAUUSD'; 'pnl' -> '/pnl'."""
    if ":" in data:
        action, arg = data.split(":", 1)
        return f"/{action} {arg}".strip()
    known = {"scanner", "pnl", "limit", "subscribe", "menu", "status", "help",
             "referral", "backtest", "notifications"}
    return f"/{data}" if data in known else data
