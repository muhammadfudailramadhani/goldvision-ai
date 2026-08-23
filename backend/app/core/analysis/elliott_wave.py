"""Elliott Wave — FASE 2, eksplisit.

Deteksi gelombang Elliott yang bisa dipertanggungjawabkan butuh labelling
swing berbasis aturan (1-2-3-4-5, ABC, guideline alternation/Fibonacci retracement)
dan sangat sensitif terhadap pivot window. Implementasi setengah-hati di fase
foundation hanya akan menghasilkan label yang tampak meyakinkan tapi tidak
bisa diuji — itu lebih buruk daripada absen. Kembalikan status NOT_AVAILABLE
yang jujur; UI/handler wajib menampilkan "belum tersedia" daripada mengarang count.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ElliottResult:
    status: str  # NOT_AVAILABLE
    note: str


def detect_elliott(candles: list) -> ElliottResult:
    return ElliottResult(
        "NOT_AVAILABLE",
        "Modul Elliott Wave dijadwalkan FASE 2 — handler wajib menyatakan belum tersedia, bukan mengarang count.",
    )
