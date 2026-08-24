"""Test intent parser (§9, §18) — natural language wajib bekerja."""
from app.channels.telegram.messages.intent import parse_intent


def test_command_start():
    assert parse_intent("/start").kind == "START"


def test_command_analyze():
    intent = parse_intent("/analyze")
    assert intent.kind == "LIVE_ANALYSIS"
    assert intent.is_command


def test_nl_gold_sekarang():
    intent = parse_intent("Gold sekarang bagaimana?")
    assert intent.kind == "LIVE_ANALYSIS"
    assert intent.pair == "XAUUSD"


def test_nl_emas():
    assert parse_intent("Emas sekarang?").pair == "XAUUSD"


def test_nl_eurusd():
    intent = parse_intent("Analisa EURUSD")
    assert intent.kind == "LIVE_ANALYSIS"
    assert intent.pair == "EURUSD"


def test_nl_pnl():
    assert parse_intent("PNL minggu ini").kind == "PNL"


def test_nl_cari_setup():
    assert parse_intent("Cari setup terbaik").kind == "SCANNER"


def test_nl_konten():
    intent = parse_intent("Buatkan konten XAUUSD")
    assert intent.pair == "XAUUSD"


def test_unknown():
    assert parse_intent("halo selamat pagi").kind == "UNKNOWN"


def test_admin_command():
    assert parse_intent("/admin stats").kind == "ADMIN"
