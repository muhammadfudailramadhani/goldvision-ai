"""Test fitur penutup FASE 2+: admin, auto-signal scan, /pnl nyata, callback, /konten."""
import importlib

import pytest
import sqlalchemy

from app.channels.base import MessageContext
from app.channels.telegram.adapter import SimulatedTransport, TelegramAdapter
from app.channels.telegram.handlers.handler import TelegramHandler
from app.db import init_db


@pytest.fixture()
def runtime(tmp_path, monkeypatch, admin_env):
    """DB sementara + TELEGRAM_ADMIN_ID untuk test admin."""
    from app import db as db_mod

    engine = sqlalchemy.create_engine(
        f"sqlite:///{tmp_path / 'fin.db'}", connect_args={"check_same_thread": False})
    SF = sqlalchemy.orm.sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(db_mod, "engine", engine)
    monkeypatch.setattr(db_mod, "SessionLocal", SF)
    for modname in ["app.channels.telegram.compliance.consent",
                    "app.channels.telegram.compliance.unsubscribe",
                    "app.channels.telegram.handlers.handler"]:
        mod = importlib.import_module(modname)
        if hasattr(mod, "SessionLocal"):
            monkeypatch.setattr(mod, "SessionLocal", SF)
    db_mod.init_db()
    yield


@pytest.fixture()
def admin_env(monkeypatch):
    monkeypatch.setattr(
        "app.channels.telegram.config.features.get_settings",
        lambda: __import__("types").SimpleNamespace(
            telegram_enabled=True, telegram_admin_id="999"))


def _ctx(uid, text, mid="1"):
    is_admin = uid == "999"
    return MessageContext(uid, "telegram", mid, text, uid, is_admin=is_admin)


# ---------------------------------------------------------------- admin gate

@pytest.mark.asyncio
async def test_admin_blocked_for_non_admin(runtime):
    h = TelegramHandler(adapter=TelegramAdapter(SimulatedTransport()))
    await h.handle(_ctx("biasa", "/start"))
    r = await h.handle(_ctx("biasa", "/admin_stats"))
    assert r.policy == "SEND_BLOCKED_ADMIN"
    assert "admin" in r.reply.lower()


@pytest.mark.asyncio
async def test_admin_stats_and_users(runtime):
    h = TelegramHandler(adapter=TelegramAdapter(SimulatedTransport()))
    await h.handle(_ctx("999", "/start"))
    r = await h.handle(_ctx("999", "/admin_stats"))
    assert r.intent == "ADMIN" and "Users:" in r.reply
    r2 = await h.handle(_ctx("999", "/admin_users"))
    assert "User terbaru" in r2.reply


@pytest.mark.asyncio
async def test_admin_vip_grant_and_expiry_flow(runtime):
    from datetime import datetime, timezone

    from app.db import SessionLocal
    from app.repositories import UserRepo

    h = TelegramHandler(adapter=TelegramAdapter(SimulatedTransport()))
    await h.handle(_ctx("999", "/start"))
    r = await h.handle(_ctx("999", "/admin_vip 999 7"))
    assert "VIP 7 hari" in r.reply
    session = SessionLocal()
    try:
        u = UserRepo(session).get_by_external_id("telegram", "999")
        # sqlite menyimpan naive-UTC — bandingkan dengan naive (konvensi DB)
        assert u.plan == "VIP" and u.plan_expires_at > datetime.utcnow()
    finally:
        session.close()
    r2 = await h.handle(_ctx("999", "/admin_vip tidak-ada"))
    assert "tidak ditemukan" in r2.reply


@pytest.mark.asyncio
async def test_vip_survives_db_roundtrip(runtime):
    """REGRESI: VIP dari DB (naive) tidak boleh crash di QuotaService."""
    from app.core.quota.service import QuotaService
    from app.core.subscription.service import SubscriptionService
    from app.db import SessionLocal
    from app.repositories import UserRepo

    h = TelegramHandler(adapter=TelegramAdapter(SimulatedTransport()))
    await h.handle(_ctx("999", "/start"))
    await h.handle(_ctx("vip-rt", "/start"))       # target user harus ada dulu
    r = await h.handle(_ctx("999", "/admin_vip vip-rt 7"))
    assert "VIP 7 hari" in r.reply
    session = SessionLocal()
    try:
        u = UserRepo(session).get_by_external_id("telegram", "vip-rt")
        session.refresh(u)  # paksa baca ulang dari DB (naive datetime)
        from datetime import datetime as _dt

        assert u.plan == "VIP", f"plan={u.plan!r}"
        assert u.plan_expires_at is not None, "expires None"
        assert u.plan_expires_at > _dt.utcnow(), \
            f"expires {u.plan_expires_at!r} <= now — tidak lolos roundtrip"
        assert QuotaService(session)._plan(u) == "VIP"
        assert QuotaService(session).check(u).limit == 4  # 4/hari + bonus
    finally:
        session.close()


@pytest.mark.asyncio
async def test_admin_broadcast_spam_guard(runtime):
    h = TelegramHandler(adapter=TelegramAdapter(SimulatedTransport()))
    await h.handle(_ctx("999", "/start"))
    r = await h.handle(_ctx("999", "/admin_broadcast pasti profit 100%"))
    assert r.policy == "SEND_BLOCKED_CHANNEL_POLICY"


# ---------------------------------------------------------------- scan auto-signal

@pytest.mark.asyncio
async def test_admin_scan_creates_and_dedups_signals(runtime, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    from app.core.signals.scan import scan_pairs
    from app.db import SessionLocal
    from app.core.market.mock import MockMarketDataProvider

    session = SessionLocal()
    try:
        first = await scan_pairs(MockMarketDataProvider(), session, pairs=["XAUUSD"])
        second = await scan_pairs(MockMarketDataProvider(), session, pairs=["XAUUSD"])
    finally:
        session.close()
    # mock deterministic per hari -> scan kedua semua dedup/cooldown
    assert isinstance(first, list)
    assert second == []


# ---------------------------------------------------------------- /pnl nyata

@pytest.mark.asyncio
async def test_pnl_shows_received_signals(runtime):
    from datetime import datetime, timezone

    from app.db import SessionLocal
    from app.models import Signal, SignalDelivery
    from app.repositories import SignalRepo, UserRepo

    h = TelegramHandler(adapter=TelegramAdapter(SimulatedTransport()))
    await h.handle(_ctx("pnl-user", "/start"))

    session = SessionLocal()
    try:
        u = UserRepo(session).get_by_external_id("telegram", "pnl-user")
        sig = SignalRepo(session).save(
            pair="XAUUSD", direction="BUY", timeframe="M15", entry=100, sl=98,
            tp1=103, tp2=105, score=77, fingerprint="fp-pnl-test-1")
        session.add(SignalDelivery(broadcast_id="b", signal_id=sig.id, user_id=u.id,
                                   status="SENT", sent_at=datetime.now(timezone.utc)))
        session.commit()
    finally:
        session.close()

    r = await h.handle(_ctx("pnl-user", "/pnl"))
    assert r.intent == "PNL"
    assert "Sinyal diterima: 1" in r.reply
    assert "Exit price belum ditrack" in r.reply  # jujur, tidak mengarang win-rate


# ---------------------------------------------------------------- callback query

@pytest.mark.asyncio
async def test_callback_query_mapped_to_command(runtime, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app.channels.telegram.handlers.handler import handle_update

    adapter = TelegramAdapter(SimulatedTransport())
    update = {"update_id": 1, "callback_query": {
        "id": "cbq-1",
        "from": {"id": 42, "is_bot": False, "first_name": "T"},
        "message": {"message_id": 5, "chat": {"id": 42, "type": "private"}},
        "data": "analyze:XAUUSD"}}
    # belum /start -> diblokir consent, tapi PROSES parsing callback terbukti jalan
    r = await handle_update(update, adapter=adapter)
    assert r is not None and r.policy == "SEND_BLOCKED_NO_CONSENT"

    update2 = dict(update)
    update2["message"] = {"message_id": 6, "from": {"id": 42},
                          "chat": {"id": 42, "type": "private"}, "text": "/start"}
    await handle_update(update2, adapter=adapter)
    r2 = await handle_update(update, adapter=adapter)
    assert r2.intent == "LIVE_ANALYSIS" and r2.pair == "XAUUSD"


# ---------------------------------------------------------------- /konten

@pytest.mark.asyncio
async def test_konten_template_and_quota(runtime, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    h = TelegramHandler(adapter=TelegramAdapter(SimulatedTransport()))
    await h.handle(_ctx("kt-1", "/start"))
    r = await h.handle(_ctx("kt-1", "/konten gold"))
    assert r.intent == "KONTEN"
    assert "[template]" in r.reply  # AI_MODE mock -> template jujur
    assert "Edukasi" in r.reply or "edukasi" in r.reply
    assert r.quota_used == 1  # konten makan quota (menjalankan analysis penuh)


@pytest.mark.asyncio
async def test_konten_ai_mode_guarded_fallback(runtime, tmp_path, monkeypatch):
    """AI_MODE aktif tapi API gagal -> fallback template (tidak pernah kosong)."""
    monkeypatch.chdir(tmp_path)
    import httpx as _httpx

    from types import SimpleNamespace

    import app.settings as settings_mod

    real = settings_mod.get_settings
    monkeypatch.setattr(settings_mod, "get_settings", lambda: SimpleNamespace(
        **{**real().__dict__, "ai_mode": "openai", "ai_api_key": "k"}))
    monkeypatch.setattr(_httpx, "post", lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError("down")))

    h = TelegramHandler(adapter=TelegramAdapter(SimulatedTransport()))
    await h.handle(_ctx("kt-2", "/start"))
    r = await h.handle(_ctx("kt-2", "buatkan konten gold"))
    assert "[template]" in r.reply  # fallback jujur
