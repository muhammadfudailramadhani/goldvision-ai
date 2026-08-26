"""Content generator (§9 "Buatkan konten XAUUSD").

AI_MODE=mock  -> template deterministik dari AnalysisResult (tanpa klaim AI).
AI_MODE!=mock -> panggil endpoint kompatibel OpenAI (settings ai_*), output
                 WAJIB lolos guard anti-klaim & anti-injection sebelum terkirim.
                 Kegagalan apa pun -> fallback template (jangan pernah kosong).
"""
import asyncio
from dataclasses import dataclass

from app.core.compliance.abuse_guard import check_outbound_text, looks_like_injection

SYSTEM_PROMPT = (
    "Kamu copywriter edukasi trading. Buat konten Telegram singkat (maks 120 kata) "
    "dari DATA analisis yang diberikan. ATURAN KERAS: tanpa janji profit, tanpa "
    "'pasti/100%/zero risk', tanpa saran membeli/menjual pasti. Selalu akhiri dengan "
    "penanda edukasi. Bahasa Indonesia."
)


@dataclass(frozen=True)
class ContentDraft:
    title: str
    body: str
    source: str  # "template" | "ai"


def draft_from_analysis(analysis) -> ContentDraft:
    rec = analysis.recommendation
    trend = analysis.trend_by_tf.get("H4", "NEUTRAL")
    title = f"{analysis.pair} — Sorotan {trend.lower().capitalize()}"
    pola = ""
    if getattr(analysis, "patterns", None):
        pola = f" Pola terlihat: {analysis.patterns[0].name_id}."
    body = (
        f"{analysis.pair} berdagang di {analysis.price:g}. Struktur H1: {analysis.structure}, "
        f"bias SMC M15: {analysis.smc_bias}. Skor setup: {analysis.score.total}/100 "
        f"({analysis.score.category}).{pola} "
        + (f"Pelan-pelan: {rec.action} dengan level entry {rec.entry:g}, SL {rec.sl:g}."
           if rec.action in ("BUY", "SELL")
           else "Belum ada setup layak transaksi — sabar menunggu konfirmasi.")
        + "\n\nEdukasi, bukan saran finansial. Trading mengandung risiko."
    )
    return ContentDraft(title, body, "template")


async def generate_content(analysis) -> ContentDraft:
    """Template atau AI sesuai settings; AI gagal = fallback template."""
    from app.settings import get_settings

    s = get_settings()
    if s.ai_mode == "mock" or not s.ai_api_key:
        return draft_from_analysis(analysis)

    draft = draft_from_analysis(analysis)
    prompt = (
        f"DATA: pair={analysis.pair} harga={analysis.price:g} struktur={analysis.structure} "
        f"bias={analysis.smc_bias} skor={analysis.score.total}/100 "
        f"aksi={analysis.recommendation.action} "
        f"pola={analysis.patterns[0].name_id if analysis.patterns else '-'}. "
        "Tulis konten Telegram edukasinya."
    )
    try:
        import httpx

        resp = await asyncio.to_thread(
            httpx.post,
            f"{s.ai_base_url}/chat/completions",
            json={"model": s.ai_model,
                  "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                               {"role": "user", "content": prompt}],
                  "temperature": 0.7, "max_tokens": 300},
            headers={"Authorization": f"Bearer {s.ai_api_key}"},
            timeout=30.0,
        )
        resp.raise_for_status()
        text = str(resp.json()["choices"][0]["message"]["content"]).strip()
    except Exception:
        return draft  # fallback jujur

    if looks_like_injection(text) or not check_outbound_text(text)[0]:
        return draft  # output AI melanggar policy = buang, pakai template
    return ContentDraft(draft.title, text, "ai")
