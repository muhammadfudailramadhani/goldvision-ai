"""Scoring engine (§15) — bobot tetap, skor DIHITUNG dari komponen, AI tidak boleh mengarang."""
from dataclasses import dataclass

WEIGHTS = {
    "trend_alignment": 30,
    "market_structure": 20,
    "smc": 20,
    "supply_demand": 15,
    "support_resistance": 10,
    "entry_confirmation": 5,
}


@dataclass(frozen=True)
class ComponentScore:
    name: str
    weight: int
    score: int


@dataclass(frozen=True)
class ScoreResult:
    total: int
    category: str  # STRONG SETUP | MODERATE | WEAK | NO TRADE
    components: list


def categorize(total: int) -> str:
    if total >= 80:
        return "STRONG SETUP"
    if total >= 60:
        return "MODERATE"
    if total >= 40:
        return "WEAK"
    return "NO TRADE"


def score_components(raw: dict[str, float]) -> ScoreResult:
    """raw: nama komponen -> confidence 0..1. Setiap komponen dikonversi proporsional ke bobotnya."""
    components: list[ComponentScore] = []
    total = 0
    for name, weight in WEIGHTS.items():
        conf = max(0.0, min(float(raw.get(name, 0.0)), 1.0))
        pts = round(conf * weight)
        components.append(ComponentScore(name, weight, pts))
        total += pts
    total = min(total, 100)
    return ScoreResult(total, categorize(total), components)
