"""Telegram rate limit constants (§22) — digunakan rate_limit/ & delivery/."""

# Per-chat
CHAT_MSG_PER_SEC = 1
CHAT_MSG_PER_MIN = 30

# Group
GROUP_MSG_PER_MIN = 20

# Broadcast bulk
BULK_MSG_PER_SEC = 30

# 429 handling (§23)
MAX_RETRY_429 = 3
DEFAULT_RETRY_AFTER_SEC = 5
