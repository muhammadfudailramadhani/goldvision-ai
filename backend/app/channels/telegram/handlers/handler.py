"""TelegramHandler — alur lengkap: intent -> consent -> quota -> analysis -> chart -> reply.

Command ringan (/help /status /limit /subscription) TIDAK menghabiskan quota (§16).
Hanya LIVE_ANALYSIS yang mengonsumsi.
"""
import asyncio
from dataclasses import dataclass

from app.channels.base import MessageContext
from app.core.analysis.engine import AnalysisEngine
from app.core.chart.generator import render_chart
from app.core.market.provider import get_provider
from app.core.quota.service import QuotaService
from app.db import SessionLocal
from app.repositories import UserRepo

from ..compliance.consent import check_user_consented, register_consent
from ..config import messages
from ..messages.intent import parse_intent


@dataclass(frozen=True)
class HandlerResult:
    reply: str
    chart_path: str | None = None
    intent: str = ""
    pair: str | None = None
    quota_used: int | None = None
    quota_limit: int | None = None
    score: int | None = None
    action: str | None = None
    policy: str = "ALLOWED"


class TelegramHandler:
    def __init__(self, adapter=None, provider=None):
        self.adapter = adapter
        self.provider = provider or get_provider()

    async def handle(self, ctx: MessageContext) -> HandlerResult:
        intent = parse_intent(ctx.text)

        # /start = consent pertama (§20)
        if intent.kind == "START":
            register_consent("telegram", ctx.user_id)
            return HandlerResult(reply=messages.WELCOME, intent="START")

        # user belum pernah /start -> DO NOT SEND analysis (§20)
        if not check_user_consented("telegram", ctx.user_id):
            return HandlerResult(reply="Ketik /start dulu untuk mulai menggunakan GoldVision AI.",
                                 intent=intent.kind, policy="SEND_BLOCKED_NO_CONSENT")

        # command ringan — tanpa quota (§16)
        if intent.kind == "HELP":
            return HandlerResult(reply=messages.HELP_TEXT, intent="HELP")
        if intent.kind == "MENU":
            return HandlerResult(reply=messages.MENU_TEXT, intent="MENU")
        if intent.kind == "SUBSCRIBE":
            return HandlerResult(reply=messages.SUBSCRIPTION_INFO, intent="SUBSCRIBE")
        if intent.kind == "STATUS":
            return HandlerResult(reply="\U0001f7e2 GoldVision AI aktif — mode localhost/mock.", intent="STATUS")
        if intent.kind == "LIMIT":
            return await self._limit(ctx)
        if intent.kind == "PNL":
            return HandlerResult(reply="PNL engine fase foundation: pencatatan & ringkasan R siap; "
                                       "backtest menyusul (docs/12-backtest.md).", intent="PNL")
        if intent.kind in ("SIGNALS", "SCANNER"):
            pair = intent.pair or "XAUUSD"
            return await self._analyze(ctx, pair, consume_quota=False, intent_kind=intent.kind)

        if intent.kind == "LIVE_ANALYSIS":
            pair = intent.pair or "XAUUSD"
            return await self._analyze(ctx, pair, consume_quota=True, intent_kind="LIVE_ANALYSIS")

        return HandlerResult(reply=messages.NOT_FOUND, intent="UNKNOWN")

    async def _limit(self, ctx: MessageContext) -> HandlerResult:
        session = SessionLocal()
        try:
            user = UserRepo(session).get_by_external_id("telegram", ctx.user_id)
            if user is None:
                return HandlerResult(reply="Ketik /start dulu.", intent="LIMIT")
            decision = QuotaService(session).check(user)
            return HandlerResult(
                reply=f"Plan: {decision.plan}\nQuota terpakai: {decision.used}/{decision.limit} "
                      f"({decision.window})",
                intent="LIMIT", quota_used=decision.used, quota_limit=decision.limit)
        finally:
            session.close()

    async def _analyze(self, ctx: MessageContext, pair: str, *, consume_quota: bool,
                       intent_kind: str) -> HandlerResult:
        # quota server-side (§16)
        session = SessionLocal()
        try:
            user = UserRepo(session).get_by_external_id("telegram", ctx.user_id)
            if user is None:
                return HandlerResult(reply="Ketik /start dulu.", intent=intent_kind,
                                     policy="SEND_BLOCKED_NO_CONSENT")
            quota = QuotaService(session)
            decision = quota.consume(user) if consume_quota else quota.check(user)
            if not decision.allowed:
                return HandlerResult(
                    reply=messages.QUOTA_EXCEEDED.format(
                        plan=decision.plan, used=decision.used,
                        limit=decision.limit, window=decision.window),
                    intent=intent_kind, pair=pair,
                    quota_used=decision.used, quota_limit=decision.limit,
                    policy="SEND_BLOCKED_QUOTA")
        finally:
            session.close()

        # analysis (mock provider di localhost)
        engine = AnalysisEngine(self.provider)
        analysis = await engine.analyze(pair)

        # tepat 1 chart per analysis (§10, §11)
        m15 = await self.provider.get_candles(pair, analysis.chart_timeframe)
        rec = analysis.recommendation
        chart_path = render_chart(
            pair=pair, timeframe=analysis.chart_timeframe, candles=m15,
            levels=analysis.levels, zones=analysis.zones,
            entry=rec.entry, sl=rec.sl, tp1=rec.tp1, tp2=rec.tp2,
        )

        trend_block = "\n".join(f"  {tf}: {d}" for tf, d in analysis.trend_by_tf.items())
        components_block = "\n".join(f"  {c.name}: {c.score}/{c.weight}"
                                     for c in analysis.score.components)
        levels_block = ""
        if rec.action in ("BUY", "SELL"):
            levels_block = (f"Entry: {rec.entry:g}\nSL: {rec.sl:g}\n"
                            f"TP1: {rec.tp1:g} · TP2: {rec.tp2:g} · RR: {rec.rr:g}\n"
                            + "\n".join(f"  \u2022 {r}" for r in rec.reasons))
        else:
            levels_block = "\n".join(f"  \u2022 {r}" for r in rec.reasons)

        reply = messages.ANALYSIS_FORMAT.format(
            pair=pair, timeframe=analysis.chart_timeframe, price=analysis.price,
            trend_block=trend_block, score=analysis.score.total,
            category=analysis.score.category, components_block=components_block,
            action=rec.action, levels_block=levels_block)

        return HandlerResult(
            reply=reply, chart_path=str(chart_path), intent=intent_kind, pair=pair,
            quota_used=decision.used, quota_limit=decision.limit,
            score=analysis.score.total, action=rec.action)


async def handle_update(raw_update: dict, adapter=None) -> HandlerResult | None:
    """Entry point webhook/polling — parse, handle, kirim balik via adapter."""
    handler = TelegramHandler(adapter=adapter)
    ctx = await handler.adapter.parse_context(raw_update) if handler.adapter else None
    if ctx is None:
        return None
    result = await handler.handle(ctx)
    if handler.adapter and ctx.chat_id:
        await handler.adapter.send_text(ctx.chat_id, result.reply)
        if result.chart_path:
            await handler.adapter.send_image(ctx.chat_id, result.chart_path, caption=pair_caption(result))
    return result


def pair_caption(result: HandlerResult) -> str:
    return f"{result.pair} · {result.action or ''} · skor {result.score}".strip()
