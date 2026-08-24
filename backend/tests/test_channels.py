"""Test channel isolation (§2, §5) — core tidak tahu platform, WhatsApp disabled."""
import pytest

from app.channels.base import ChannelAdapter, MessageContext
from app.channels.telegram.adapter import SimulatedTransport, TelegramAdapter
from app.channels.whatsapp.adapter import ChannelDisabledError, WhatsAppAdapter


def test_message_context_shape():
    ctx = MessageContext(user_id="1", channel="telegram", message_id="2", text="hi")
    assert ctx.channel == "telegram"


def test_telegram_adapter_simulated():
    adapter = TelegramAdapter(transport=SimulatedTransport())
    assert isinstance(adapter.transport, SimulatedTransport)
    assert adapter.is_enabled()  # TELEGRAM_ENABLED=true default


@pytest.mark.asyncio
async def test_telegram_send_records():
    transport = SimulatedTransport()
    adapter = TelegramAdapter(transport=transport)
    mid = await adapter.send_text("c1", "hello")
    assert mid is not None
    assert transport.sent[0]["text"] == "hello"


@pytest.mark.asyncio
async def test_whatsapp_disabled_blocks_everything():
    adapter = WhatsAppAdapter()
    assert not adapter.is_enabled()  # §4: WHATSAPP_ENABLED=false
    with pytest.raises(ChannelDisabledError):
        await adapter.send_text("628123", "hi")
    with pytest.raises(ChannelDisabledError):
        await adapter.send_image("628123", "chart.png")


def test_core_has_no_channel_imports():
    """§2: folder core/ tidak boleh meng-import channels/ — verifikasi statis."""
    import subprocess, sys, os
    root = os.path.join(os.path.dirname(__file__), "..", "app", "core")
    violations = []
    for dirpath, _, files in os.walk(root):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(dirpath, f)
                with open(path, encoding="utf-8") as fh:
                    if "from app.channels" in fh.read() or "import app.channels" in fh.read():
                        violations.append(path)
    assert not violations, f"core/ tidak boleh import channels/: {violations}"
