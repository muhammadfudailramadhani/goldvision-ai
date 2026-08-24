"""WhatsApp limits — dipakai saat channel diaktifkan nanti (§8)."""

OUTBOUND_PER_SEC = 40          # konservatif di bawah throughput tier default
OUTBOUND_PER_MIN = 2000
RETRY_MAX = 3
RETRY_BACKOFF_SEC = 2.0
