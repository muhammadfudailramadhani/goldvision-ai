"""Skema Pydantic untuk API internal & antar-lapisan."""
from pydantic import BaseModel


class AnalysisComponent(BaseModel):
    name: str
    weight: int
    score: int  # 0..weight — dihitung engine, bukan dikarang AI (§15)


class RecommendationOut(BaseModel):
    action: str  # BUY | SELL | WAIT | NO_TRADE
    entry: float | None = None
    sl: float | None = None
    tp1: float | None = None
    tp2: float | None = None
    rr: float | None = None
    reasons: list[str] = []


class AnalysisOut(BaseModel):
    pair: str
    timeframe: str
    price: float
    trend_by_tf: dict[str, str]
    score: int
    category: str
    components: list[AnalysisComponent]
    recommendation: RecommendationOut
    chart_path: str | None = None


class SignalOut(BaseModel):
    pair: str
    direction: str
    timeframe: str
    entry: float
    sl: float
    tp1: float
    tp2: float
    score: int
    fingerprint: str
