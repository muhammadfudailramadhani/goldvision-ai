"""PnlEngine — pelacakan hasil sinyal & ringkasan mingguan (FASE FOUNDATION: pencatatan + ringkasan sederhana).

Backtest engine lengkap = FASE 2 (docs/12-backtest.md).
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.models import Signal
from app.repositories import UserRepo


@dataclass(frozen=True)
class PnlSummary:
    total_signals: int
    wins: int
    losses: int
    open_: int
    win_rate: float
    r_gained: float  # total dalam satuan R (risk = 1)


def outcome_r(signal: Signal, exit_price: float) -> float:
    """Hitung hasil dalam R. Long: (exit-entry)/(entry-sl). Short dibalik."""
    risk = abs(signal.entry - signal.sl)
    if risk == 0:
        return 0.0
    if signal.direction == "BUY":
        return round((exit_price - signal.entry) / risk, 2)
    return round((signal.entry - exit_price) / risk, 2)


def summarize(signals_with_outcomes: list[tuple[Signal, float | None]]) -> PnlSummary:
    wins = losses = open_ = 0
    r_gained = 0.0
    for signal, exit_price in signals_with_outcomes:
        if exit_price is None:
            open_ += 1
            continue
        r = outcome_r(signal, exit_price)
        r_gained += r
        wins += 1 if r > 0 else 0
        losses += 1 if r <= 0 else 0
    total = len(signals_with_outcomes)
    closed = wins + losses
    return PnlSummary(total, wins, losses, open_,
                      round(wins / closed * 100, 1) if closed else 0.0, round(r_gained, 2))


def weekly_window(now: datetime | None = None) -> tuple[datetime, datetime]:
    now = now or datetime.now(timezone.utc)
    return now - timedelta(days=7), now


class PnlEngine:
    """Layer service — dipakai channel untuk /pnl."""

    def __init__(self, session):
        self.session = session
        self.users = UserRepo(session)
