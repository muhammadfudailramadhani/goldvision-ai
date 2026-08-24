"""Test scoring engine (§15) — bobot tetap, kategori benar, skor tidak bisa >100."""
from app.core.scoring.engine import WEIGHTS, categorize, score_components


def test_weights_sum_to_100():
    assert sum(WEIGHTS.values()) == 100


def test_perfect_score_strong():
    result = score_components({k: 1.0 for k in WEIGHTS})
    assert result.total == 100
    assert result.category == "STRONG SETUP"


def test_zero_score_no_trade():
    result = score_components({k: 0.0 for k in WEIGHTS})
    assert result.total == 0
    assert result.category == "NO TRADE"


def test_categories():
    assert categorize(80) == "STRONG SETUP"
    assert categorize(79) == "MODERATE"
    assert categorize(60) == "MODERATE"
    assert categorize(59) == "WEAK"
    assert categorize(40) == "WEAK"
    assert categorize(39) == "NO TRADE"


def test_confidence_clamped():
    result = score_components({"trend_alignment": 5.0, "smc": -3.0})
    comp = {c.name: c for c in result.components}
    assert comp["trend_alignment"].score == 30  # clamp ke 1.0
    assert comp["smc"].score == 0               # clamp ke 0.0
