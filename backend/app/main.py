"""GoldVision AI — FastAPI skeleton (localhost mode §47).

Endpoint webhook Telegram = FASE 2 (butuh token). Untuk foundation:
health, info, dan endpoint analyze internal untuk developer preview.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.core.analysis.engine import AnalysisEngine
from app.core.market.provider import get_provider
from app.db import init_db
from app.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="GoldVision AI", version="0.1.0-foundation", lifespan=lifespan)


class AnalyzeRequest(BaseModel):
    pair: str = "XAUUSD"


@app.get("/health")
async def health():
    s = get_settings()
    return {
        "status": "ok",
        "app_env": s.app_env,
        "channels": {"telegram": s.telegram_enabled, "whatsapp": s.whatsapp_enabled},
        "modes": {"market_data": s.market_data_mode, "ai": s.ai_mode, "payment": s.payment_mode},
    }


@app.get("/")
async def root():
    return {
        "name": "GoldVision AI",
        "phase": "foundation (localhost/mock)",
        "docs": "/docs",
        "health": "/health",
    }


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    """Developer preview — jalankan analysis via HTTP tanpa Telegram."""
    try:
        engine = AnalysisEngine(get_provider())
        result = await engine.analyze(req.pair.upper())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    rec = result.recommendation
    return {
        "pair": result.pair,
        "price": result.price,
        "trend_by_tf": result.trend_by_tf,
        "score": result.score.total,
        "category": result.score.category,
        "components": [{"name": c.name, "score": c.score, "weight": c.weight}
                       for c in result.score.components],
        "recommendation": {
            "action": rec.action, "entry": rec.entry, "sl": rec.sl,
            "tp1": rec.tp1, "tp2": rec.tp2, "rr": rec.rr, "reasons": rec.reasons,
        },
        "elliott": result.elliott_status,
    }


@app.post("/webhook/telegram")
async def telegram_webhook(update: dict):
    """FASE 2 — butuh TELEGRAM_BOT_TOKEN. Tanpa token: tolak, jangan pura-pura jalan."""
    s = get_settings()
    if not (s.telegram_enabled and s.telegram_bot_token):
        raise HTTPException(status_code=503, detail="Webhook belum dikonfigurasi (FASE 2)")
    from app.channels.telegram.handlers import handle_update
    result = await handle_update(update)
    return {"processed": result is not None, "intent": result.intent if result else None}
