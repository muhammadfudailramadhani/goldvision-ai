"""Test regresi hasil audit QA menyeluruh — bug yang ditemukan WAJIB punya test."""
import re
from types import SimpleNamespace

import pytest


# ---------------------------------------------------------------- engine data kosong

@pytest.mark.asyncio
async def test_engine_empty_provider_raises_value_error_not_crash():
    """REGRESI: provider kembali 0 candle = ValueError jujur, bukan IndexError."""
    from app.core.analysis.engine import AnalysisEngine

    class EmptyProvider:
        name = "empty"

        async def get_candles(self, pair, timeframe, limit=200):
            return []

    with pytest.raises(ValueError, match="kosong"):
        await AnalysisEngine(EmptyProvider()).analyze("XAUUSD")


@pytest.mark.asyncio
async def test_engine_partial_empty_tf_raises(monkeypatch):
    """Satu TF kosong (mis. H4 gagal) juga harus ditolak jujur."""
    from app.core.analysis.engine import ANALYSIS_TFS, AnalysisEngine
    from app.core.market.provider import Candle

    class PartialProvider:
        name = "partial"

        async def get_candles(self, pair, timeframe, limit=200):
            if timeframe == "H4":
                return []
            return [Candle(ts=i, open=1, high=1, low=1, close=1, volume=0)
                    for i in range(200)]

    with pytest.raises(ValueError, match="H4"):
        await AnalysisEngine(PartialProvider()).analyze("EURUSD")


# ---------------------------------------------------------------- schema parity

def test_schema_sql_parity_with_models():
    """REGRESI DRIFT: schema.sql WAJIB memuat semua kolom model User.

    Bug dulu: 4 kolom referral hilang -> deployment Postgres baru crash."""
    from pathlib import Path

    from app.models import User

    sql = Path("database/schema.sql").read_text(encoding="utf-8")
    m = re.search(r'CREATE TABLE IF NOT EXISTS "user" \((.*?)\);', sql, re.S)
    assert m, "blok CREATE TABLE user tidak ditemukan"
    sql_cols = set()
    for line in m.group(1).splitlines():
        line = line.strip().rstrip(",")
        if not line or line.startswith("--") or line.upper().startswith("CONSTRAINT"):
            continue
        sql_cols.add(line.split()[0])
    model_cols = {c.name for c in User.__table__.columns}
    missing = model_cols - sql_cols
    assert not missing, f"schema.sql kehilangan kolom: {missing}"


# ---------------------------------------------------------------- webhook security

def _client():
    from fastapi.testclient import TestClient

    from app.main import app
    return TestClient(app)


def test_webhook_503_without_token(monkeypatch):
    monkeypatch.setattr("app.main.get_settings",
                        lambda: SimpleNamespace(telegram_enabled=True,
                                                telegram_bot_token="",
                                                telegram_webhook_secret=""))
    resp = _client().post("/webhook/telegram", json={})
    assert resp.status_code == 503


def test_webhook_401_wrong_secret(monkeypatch):
    monkeypatch.setattr("app.main.get_settings",
                        lambda: SimpleNamespace(telegram_enabled=True,
                                                telegram_bot_token="tok",
                                                telegram_webhook_secret="rahasia"))
    resp = _client().post("/webhook/telegram", json={},
                          headers={"X-Telegram-Bot-Api-Secret-Token": "salah"})
    assert resp.status_code == 401
    resp2 = _client().post("/webhook/telegram", json={})  # tanpa header = tolak
    assert resp2.status_code == 401


def test_webhook_accepts_matching_secret(monkeypatch):
    monkeypatch.setattr("app.main.get_settings",
                        lambda: SimpleNamespace(telegram_enabled=True,
                                                telegram_bot_token="tok",
                                                telegram_webhook_secret="rahasia"))
    # handler berjalan offline: update tanpa message -> processed False, BUKAN 401
    resp = _client().post("/webhook/telegram", json={"update_id": 1},
                          headers={"X-Telegram-Bot-Api-Secret-Token": "rahasia"})
    assert resp.status_code == 200
    assert resp.json()["processed"] is False


# ---------------------------------------------------------------- sqlite automigrate

def test_init_db_migrates_old_schema_additive_columns(tmp_path, monkeypatch):
    """REGRESI: DB sqlite versi lama (tanpa kolom referral) WAJIB termigrasi."""
    import sqlite3
    import sqlalchemy

    from app import db as db_mod

    db_path = tmp_path / "old.db"
    con = sqlite3.connect(db_path)
    con.execute('CREATE TABLE "user" (id INTEGER PRIMARY KEY, channel TEXT, external_id TEXT)')
    con.execute("INSERT INTO \"user\" (channel, external_id) VALUES ('telegram', 'legacy-1')")
    con.commit()
    con.close()

    eng = sqlalchemy.create_engine(f"sqlite:///{db_path}",
                                   connect_args={"check_same_thread": False})
    monkeypatch.setattr(db_mod, "engine", eng)
    db_mod.init_db()

    con = sqlite3.connect(db_path)
    cols = {r[1] for r in con.execute("PRAGMA table_info(user)")}
    con.close()
    assert {"referral_code", "referred_by", "referral_rewarded", "bonus_quota"} <= cols

    # data lama selamat & baris lama bisa dibaca ORM
    SessionF = sqlalchemy.orm.sessionmaker(bind=eng)
    s = SessionF()
    from app.models import User
    legacy = s.query(User).filter_by(external_id="legacy-1").one()
    assert legacy.bonus_quota == 0
    s.close()


# ---------------------------------------------------------------- delivery policy & queue

def test_classify_failure_categories():
    from app.channels.telegram.compliance.delivery_policy import classify_failure

    assert classify_failure("Forbidden: bot was blocked by the user") == "PERMANENT"
    assert classify_failure("Bad Request: chat not found") == "PERMANENT"
    assert classify_failure("Connection timeout") == "TEMPORARY"
    assert classify_failure("Too Many Requests: retry after 3") == "RATE_LIMIT"
    assert classify_failure("HTTP 429 received") == "RATE_LIMIT"
    assert classify_failure("weird error") == "UNKNOWN"


@pytest.mark.asyncio
async def test_queue_honors_retry_after_via_pause_fn():
    """§23: queue WAJIB memanggil pause dengan nilai retry_after sebelum requeue."""
    from app.channels.telegram.delivery.queue import (BroadcastQueue, DeliveryItem,
                                                      RetryAfterError)

    pauses = []
    calls = {"n": 0}

    def sender(chat_id, item):
        if calls["n"] == 0:
            calls["n"] += 1
            raise RetryAfterError(1.5)
        return "msg-1"

    policy = SimpleNamespace(check_outgoing=lambda chat_id: SimpleNamespace(
        allowed=True, reason=""))

    q = BroadcastQueue(sender, policy, max_retries=3, retry_pause=pauses.append)
    item = DeliveryItem(broadcast_id="b1", user_id=1, chat_id="c1", text="hi")
    assert q.enqueue(item) is True
    report = q.drain()
    assert pauses == [1.5]
    assert report.sent == 1 and report.retried == 1 and item.status == "SENT"


# ---------------------------------------------------------------- intent fuzz spot-checks

def test_parse_intent_edge_samples_no_crash():
    from app.channels.telegram.messages.intent import parse_intent

    samples = ["", " ", "/", "/@", "/unknowncmd", "/analyze@OtherBot", "?", "!!!",
               "/start ab", "/start TOOLONGCODE123456"]
    for s in samples:
        parse_intent(s)  # tidak boleh raise
