"""AnalysisEngine — orkestrator multi-timeframe (§10, §14).

Satu analysis = satu chart (default XAUUSD M15) + analisis D1+H4+H1+M30+M15.
Core tidak menyentuh channel apa pun (§2): output murni data.
"""
from dataclasses import dataclass, field

from app.core.analysis.confluence import analyze_confluence
from app.core.analysis.elliott_wave import detect_elliott
from app.core.analysis.market_structure import analyze_structure
from app.core.analysis.recommendation import Recommendation, build_recommendation
from app.core.analysis.smc import detect_smc
from app.core.analysis.supply_demand import find_zones
from app.core.analysis.support_resistance import find_levels
from app.core.analysis.trend import detect_trend
from app.core.market.provider import MarketDataProvider
from app.core.scoring.engine import ScoreResult, score_components

ANALYSIS_TFS = ["D1", "H4", "H1", "M30", "M15"]
CHART_TIMEFRAME = "M15"  # §10: TEPAT 1 chart


@dataclass(frozen=True)
class AnalysisResult:
    pair: str
    price: float
    trend_by_tf: dict
    structure: str
    smc_bias: str
    levels: list
    zones: list
    score: ScoreResult
    confluence: object
    recommendation: Recommendation
    elliott_status: str
    chart_timeframe: str = CHART_TIMEFRAME
    notes: list = field(default_factory=list)


class AnalysisEngine:
    def __init__(self, provider: MarketDataProvider):
        self.provider = provider

    async def analyze(self, pair: str) -> AnalysisResult:
        candles_by_tf = {tf: await self.provider.get_candles(pair, tf) for tf in ANALYSIS_TFS}
        # Kegagalan jujur: provider yang kembali kosong = error, bukan crash index
        for tf, candles in candles_by_tf.items():
            if not candles:
                raise ValueError(
                    f"Data {pair} {tf} kosong — provider gagal atau pair tidak tersedia."
                )
        m15 = candles_by_tf["M15"]

        trend_by_tf = {tf: detect_trend([c.close for c in candles]).direction for tf, candles in candles_by_tf.items()}
        structure = analyze_structure(candles_by_tf["H1"])
        smc = detect_smc(m15)
        levels = find_levels(candles_by_tf["H1"])
        zones = find_zones(m15)
        confluence = analyze_confluence(trend_by_tf)
        elliott = detect_elliott(m15)

        # Confidence per komponen (0..1) — bahan scoring, bukan skor akhir.
        tf_votes = [1 if trend_by_tf[tf] == "BULLISH" else -1 if trend_by_tf[tf] == "BEARISH" else 0
                    for tf in ANALYSIS_TFS]
        dominant = max(set(tf_votes), key=tf_votes.count)
        raw = {
            "trend_alignment": abs(sum(tf_votes)) / len(ANALYSIS_TFS) * (0.6 + 0.4 * (dominant != 0)),
            "market_structure": min((0.35 if structure.structure != "RANGE" else 0.1)
                                    + (0.45 if structure.last_event == "BOS" else 0.2), 1.0),
            "smc": (0.35 if smc.bias != "NEUTRAL" else 0.1) + min(len(smc.order_blocks) * 0.15, 0.3)
                   + min(len(smc.fvgs) * 0.1, 0.2),
            "supply_demand": min(0.2 + sum(z.strength for z in zones) / 2, 1.0),
            "support_resistance": min(0.2 + len(levels) * 0.12, 1.0),
            "entry_confirmation": 0.4 if confluence.aligned >= 3 and not confluence.tf_blocked else 0.1,
        }
        score = score_components(raw)

        bias = "BULLISH" if dominant >= 0 and smc.bias != "BEARISH" else \
               "BEARISH" if dominant <= 0 and smc.bias != "BULLISH" else "NEUTRAL"
        recommendation = build_recommendation(m15, bias, score.total, confluence.tf_blocked)

        return AnalysisResult(
            pair=pair,
            price=m15[-1].close,
            trend_by_tf=trend_by_tf,
            structure=structure.structure,
            smc_bias=smc.bias,
            levels=levels,
            zones=zones,
            score=score,
            confluence=confluence,
            recommendation=recommendation,
            elliott_status=elliott.status,
        )
