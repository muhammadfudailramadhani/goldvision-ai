"""WhatsApp quality monitoring (§35) — dipakai saat channel aktif.

Quality memburuk -> PAUSE BROADCAST, jangan menaikkan volume.
"""
from ..config.compliance import QUALITY_THRESHOLDS


def evaluate_quality(delivery_rate: float, block_rate: float, report_rate: float,
                     failed_rate: float) -> tuple[bool, list[str]]:
    """Return (ok_to_continue, reasons)."""
    reasons: list[str] = []
    if block_rate >= QUALITY_THRESHOLDS["block_rate_pct"]:
        reasons.append(f"block rate {block_rate}% >= {QUALITY_THRESHOLDS['block_rate_pct']}%")
    if report_rate >= QUALITY_THRESHOLDS["report_rate_pct"]:
        reasons.append(f"report rate {report_rate}% >= {QUALITY_THRESHOLDS['report_rate_pct']}%")
    if failed_rate >= QUALITY_THRESHOLDS["failed_rate_pct"]:
        reasons.append(f"failed rate {failed_rate}% >= {QUALITY_THRESHOLDS['failed_rate_pct']}%")
    return (len(reasons) == 0, reasons)
