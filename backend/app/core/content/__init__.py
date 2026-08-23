"""Content generator (§9 "Buatkan konten XAUUSD") — FASE 2 dengan AI asli (AI_MODE != mock).

FASE FOUNDATION: template deterministik dari AnalysisResult — bukan klaim AI.
Ketika AI_MODE diisi provider asli, modul ini diganti menjadi call ke LLM
dengan validasi output (prompt-injection guard ada di core/compliance/abuse_guard.py).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ContentDraft:
    title: str
    body: str
    source: str  # "template" | "ai"


def draft_from_analysis(analysis) -> ContentDraft:
    rec = analysis.recommendation
    trend = analysis.trend_by_tf.get("H4", "NEUTRAL")
    title = f"{analysis.pair} — Sorotan {trend.lower().capitalize()}"
    body = (
        f"{analysis.pair} berdagang di {analysis.price:g}. Struktur H1: {analysis.structure}, "
        f"bias SMC M15: {analysis.smc_bias}. Skor setup: {analysis.score.total}/100 "
        f"({analysis.score.category}). "
        + (f"Pelan-pelan: {rec.action} dengan level entry {rec.entry:g}, SL {rec.sl:g}."
           if rec.action in ("BUY", "SELL") else "Belum ada setup layak transaksi — sabar menunggu konfirmasi.")
        + "\n\nEdukasi, bukan saran finansial. Trading mengandung risiko."
    )
    return ContentDraft(title, body, "template")
