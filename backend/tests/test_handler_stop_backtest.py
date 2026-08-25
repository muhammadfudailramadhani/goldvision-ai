"""Test handler /backtest, /stop, /notifications — wiring intent -> compliance -> reply."""
import pytest

from app.channels.base import MessageContext
from app.channels.telegram.adapter import SimulatedTransport, TelegramAdapter
from app.channels.telegram.handlers.handler import TelegramHandler
from app.db import init_db


@pytest.fixture()
def runtime(tmp_path, monkeypatch):
    """DB file sementara per test — pola sama dengan test_handler_e2e."""
    import importlib
    import sqlalchemy

    from app import db as db_mod

    engine = sqlalchemy.create_engine(
        f"sqlite:///{tmp_path / 'test_stop_backtest.db'}",
        connect_args={"check_same_thread": False})
    SessionFactory = sqlalchemy.orm.sessionmaker(bind=engine, autoflush=False,
                                                 expire_on_commit=False)
    monkeypatch.setattr(db_mod, "engine", engine)
    monkeypatch.setattr(db_mod, "SessionLocal", SessionFactory)

    for modname in [
        "app.channels.telegram.compliance.consent",
        "app.channels.telegram.compliance.audit",
        "app.channels.telegram.compliance.unsubscribe",
        "app.channels.telegram.handlers.handler",
        "app.core.compliance.suppression",
        "app.core.compliance.preference",
        "app.core.compliance.audit",
    ]:
        mod = importlib.import_module(modname)
        if hasattr(mod, "SessionLocal"):
            monkeypatch.setattr(mod, "SessionLocal", SessionFactory)

    db_mod.init_db()
    yield


def _ctx(uid: str, text: str, msg_id: str = "1") -> MessageContext:
    return MessageContext(uid, "telegram", msg_id, text, uid)


@pytest.mark.asyncio
async def test_stop_deactivates_user(runtime):
    from app.db import SessionLocal
    from app.repositories import UserRepo

    handler = TelegramHandler(adapter=TelegramAdapter(SimulatedTransport()))
    uid = "stop-user-1"
    await handler.handle(_ctx(uid, "/start"))
    r = await handler.handle(_ctx(uid, "/stop"))
    assert r.intent == "STOP"
    assert r.action == "STOPPED"

    session = SessionLocal()
    try:
        user = UserRepo(session).get_by_external_id("telegram", uid)
        assert user.is_active is False
        assert user.notifications_enabled is False
        assert UserRepo(session).eligible_for_broadcast() == []
    finally:
        session.close()


@pytest.mark.asyncio
async def test_notifications_off_on_status(runtime):
    from app.db import SessionLocal
    from app.repositories import UserRepo

    handler = TelegramHandler(adapter=TelegramAdapter(SimulatedTransport()))
    uid = "notif-user-1"
    await handler.handle(_ctx(uid, "/start"))

    r_off = await handler.handle(_ctx(uid, "/notifications off"))
    assert r_off.intent == "NOTIFICATIONS"
    session = SessionLocal()
    try:
        user = UserRepo(session).get_by_external_id("telegram", uid)
        assert user.notifications_enabled is False
        # status tetap aktif untuk interaksi manual (§21 opt-out parsial)
        assert user.is_active is True
    finally:
        session.close()

    r_status = await handler.handle(_ctx(uid, "/notifications"))
    assert "mati" in r_status.reply.lower()

    r_on = await handler.handle(_ctx(uid, "/notifications on"))
    assert r_on.intent == "NOTIFICATIONS"
    session = SessionLocal()
    try:
        user = UserRepo(session).get_by_external_id("telegram", uid)
        assert user.notifications_enabled is True
    finally:
        session.close()


@pytest.mark.asyncio
async def test_notifications_bare_shows_status_without_mutating(runtime):
    """REGRESI BUG: '/notifications' mengandung substring 'on' -> salah enable.

    Bare command HARUS hanya menampilkan status, tidak mengubah state."""
    from app.db import SessionLocal
    from app.repositories import UserRepo

    handler = TelegramHandler(adapter=TelegramAdapter(SimulatedTransport()))
    uid = "notif-user-2"
    await handler.handle(_ctx(uid, "/start"))

    r = await handler.handle(_ctx(uid, "/notifications"))
    assert "aktif" in r.reply.lower()  # status awal = on (default user baru)
    session = SessionLocal()
    try:
        assert UserRepo(session).get_by_external_id("telegram", uid).notifications_enabled is True
    finally:
        session.close()

    # matikan lalu bare command lagi -> tetap off, tidak menyala sendiri
    await handler.handle(_ctx(uid, "/notifications off"))
    r2 = await handler.handle(_ctx(uid, "/notifications"))
    assert "mati" in r2.reply.lower()
    session = SessionLocal()
    try:
        assert UserRepo(session).get_by_external_id("telegram", uid).notifications_enabled is False
    finally:
        session.close()


@pytest.mark.asyncio
async def test_notifications_unknown_arg_shows_status(runtime):
    handler = TelegramHandler(adapter=TelegramAdapter(SimulatedTransport()))
    uid = "notif-user-3"
    await handler.handle(_ctx(uid, "/start"))
    r = await handler.handle(_ctx(uid, "/notifications xyz"))
    assert r.intent == "NOTIFICATIONS"
    assert "aktif" in r.reply.lower()  # status, bukan aksi


@pytest.mark.asyncio
async def test_stop_blocks_subsequent_analysis(runtime):
    """/stop menonaktifkan consent — analysis berikutnya DITOLAK sampai /start lagi."""
    handler = TelegramHandler(adapter=TelegramAdapter(SimulatedTransport()))
    uid = "stop-user-2"
    await handler.handle(_ctx(uid, "/start"))
    await handler.handle(_ctx(uid, "/stop"))
    r = await handler.handle(_ctx(uid, "Analisa XAUUSD"))
    assert r.policy == "SEND_BLOCKED_NO_CONSENT"


@pytest.mark.asyncio
async def test_backtest_consumes_quota_and_replies(runtime, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # chart dir tidak dipakai backtest, jaga kebersihan
    handler = TelegramHandler(adapter=TelegramAdapter(SimulatedTransport()))
    uid = "bt-user-1"
    await handler.handle(_ctx(uid, "/start"))

    r = await handler.handle(_ctx(uid, "/backtest gold m15"))
    assert r.intent == "BACKTEST"
    assert r.pair == "XAUUSD"
    assert r.policy == "ALLOWED"
    assert r.quota_used == 1  # backtest memakan quota (lebih berat dari live analysis)
    assert "Backtest XAUUSD M15" in r.reply
    assert "Win rate" in r.reply


@pytest.mark.asyncio
async def test_backtest_nl_intent(runtime):
    handler = TelegramHandler(adapter=TelegramAdapter(SimulatedTransport()))
    uid = "bt-user-2"
    await handler.handle(_ctx(uid, "/start"))
    r = await handler.handle(_ctx(uid, "tolong uji historis EURUSD"))
    assert r.intent == "BACKTEST"
    assert r.pair == "EURUSD"


@pytest.mark.asyncio
async def test_backtest_blocked_by_quota(runtime):
    handler = TelegramHandler(adapter=TelegramAdapter(SimulatedTransport()))
    uid = "bt-user-3"
    await handler.handle(_ctx(uid, "/start"))
    for i in range(3):  # habiskan quota FREE mingguan
        await handler.handle(_ctx(uid, "Analisa XAUUSD", str(i + 1)))
    r = await handler.handle(_ctx(uid, "/backtest XAUUSD", "9"))
    assert r.policy == "SEND_BLOCKED_QUOTA"


@pytest.mark.asyncio
async def test_backtest_no_consent_blocked(runtime):
    handler = TelegramHandler(adapter=TelegramAdapter(SimulatedTransport()))
    r = await handler.handle(_ctx("stranger-bt", "/backtest gold"))
    assert r.policy == "SEND_BLOCKED_NO_CONSENT"
