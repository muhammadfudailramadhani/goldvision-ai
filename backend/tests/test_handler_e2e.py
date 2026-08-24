"""Test handler end-to-end via DB nyata (repo root) — alur §48 lengkap dengan chart."""
import pytest

from app.channels.base import MessageContext
from app.channels.telegram.adapter import SimulatedTransport, TelegramAdapter
from app.channels.telegram.handlers.handler import TelegramHandler
from app.db import SessionLocal, init_db
from app.repositories import UserRepo


@pytest.fixture()
def runtime(tmp_path, monkeypatch):
    """DB file sementara per test — patch engine & SessionLocal di semua titik import."""
    import sqlalchemy
    from app import db as db_mod

    engine = sqlalchemy.create_engine(
        f"sqlite:///{tmp_path / 'test_handler.db'}", connect_args={"check_same_thread": False})
    SessionFactory = sqlalchemy.orm.sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(db_mod, "engine", engine)
    monkeypatch.setattr(db_mod, "SessionLocal", SessionFactory)

    # modul yang melakukan `from app.db import SessionLocal` saat import time
    import importlib
    for modname in [
        "app.channels.telegram.compliance.consent",
        "app.channels.telegram.compliance.audit",
        "app.channels.telegram.compliance.unsubscribe",
        "app.channels.telegram.handlers.handler",
        "app.core.compliance.suppression",
        "app.core.compliance.preference",
        "app.core.compliance.audit",
        "app.channels.whatsapp.compliance.opt_in",
    ]:
        mod = importlib.import_module(modname)
        if hasattr(mod, "SessionLocal"):
            monkeypatch.setattr(mod, "SessionLocal", SessionFactory)

    db_mod.init_db()
    yield


@pytest.mark.asyncio
async def test_full_flow_analysis_with_chart(runtime, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # chart keluar di tmp, bukan repo
    transport = SimulatedTransport()
    handler = TelegramHandler(adapter=TelegramAdapter(transport=transport))
    uid = "e2e-user-1"

    # 1. /start dulu (consent §20)
    r0 = await handler.handle(MessageContext(uid, "telegram", "0", "/start", uid))
    assert r0.intent == "START"

    # 2. minta analysis NL
    r1 = await handler.handle(MessageContext(uid, "telegram", "1", "Gold sekarang bagaimana?", uid))
    assert r1.intent == "LIVE_ANALYSIS"
    assert r1.pair == "XAUUSD"
    assert r1.quota_used == 1 and r1.quota_limit == 3
    assert r1.score is not None and 0 <= r1.score <= 100
    assert r1.action in ("BUY", "SELL", "WAIT", "NO_TRADE")
    assert r1.chart_path and __import__("os").path.exists(r1.chart_path)  # TEPAT 1 chart (§10)


@pytest.mark.asyncio
async def test_quota_blocks_fourth_analysis(runtime):
    handler = TelegramHandler(adapter=TelegramAdapter(SimulatedTransport()))
    uid = "e2e-user-2"
    await handler.handle(MessageContext(uid, "telegram", "0", "/start", uid))
    results = []
    for i in range(4):
        r = await handler.handle(MessageContext(uid, "telegram", str(i + 1),
                                                "Analisa XAUUSD", uid))
        results.append(r.policy)
    assert results == ["ALLOWED", "ALLOWED", "ALLOWED", "SEND_BLOCKED_QUOTA"]


@pytest.mark.asyncio
async def test_light_commands_dont_burn_quota(runtime):
    handler = TelegramHandler(adapter=TelegramAdapter(SimulatedTransport()))
    uid = "e2e-user-3"
    await handler.handle(MessageContext(uid, "telegram", "0", "/start", uid))
    for _ in range(10):
        await handler.handle(MessageContext(uid, "telegram", "1", "/help", uid))
        await handler.handle(MessageContext(uid, "telegram", "2", "/limit", uid))
    r = await handler.handle(MessageContext(uid, "telegram", "3", "Analisa XAUUSD", uid))
    assert r.policy == "ALLOWED" and r.quota_used == 1  # §16: command ringan gratis


@pytest.mark.asyncio
async def test_no_consent_blocked(runtime):
    handler = TelegramHandler(adapter=TelegramAdapter(SimulatedTransport()))
    r = await handler.handle(MessageContext("stranger-1", "telegram", "1",
                                            "Gold sekarang bagaimana?", "stranger-1"))
    assert r.policy == "SEND_BLOCKED_NO_CONSENT"
    assert r.chart_path is None
