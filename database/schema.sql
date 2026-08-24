-- GoldVision AI — PostgreSQL reference schema (dokumentasi; aplikasi dev pakai SQLAlchemy create_all)
-- Identik dengan backend/app/models/__init__.py

CREATE TABLE IF NOT EXISTS "user" (
    id            SERIAL PRIMARY KEY,
    channel       VARCHAR(20)  NOT NULL,
    external_id   VARCHAR(64)  NOT NULL,
    started_bot_at TIMESTAMPTZ,
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    auto_signal_enabled    BOOLEAN NOT NULL DEFAULT TRUE,
    quiet_hours_start INTEGER,
    quiet_hours_end   INTEGER,
    timezone      VARCHAR(50)  NOT NULL DEFAULT 'UTC',
    language      VARCHAR(10)  NOT NULL DEFAULT 'id',
    plan          VARCHAR(10)  NOT NULL DEFAULT 'FREE',
    plan_expires_at TIMESTAMPTZ,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT uq_user_channel_external UNIQUE (channel, external_id)
);

CREATE TABLE IF NOT EXISTS whatsapp_opt_in (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES "user"(id),
    opt_in_source VARCHAR(100),
    opt_in_timestamp TIMESTAMPTZ,
    opt_in_category VARCHAR(50),
    opt_out_timestamp TIMESTAMPTZ,
    is_suppressed BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS quota_usage (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES "user"(id),
    kind       VARCHAR(30) NOT NULL DEFAULT 'live_analysis',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_quota_usage_user ON quota_usage(user_id);
CREATE INDEX IF NOT EXISTS ix_quota_usage_created ON quota_usage(created_at);

CREATE TABLE IF NOT EXISTS signal (
    id          SERIAL PRIMARY KEY,
    pair        VARCHAR(12) NOT NULL,
    direction   VARCHAR(6)  NOT NULL,
    timeframe   VARCHAR(6)  NOT NULL,
    entry       DOUBLE PRECISION NOT NULL,
    sl          DOUBLE PRECISION NOT NULL,
    tp1         DOUBLE PRECISION NOT NULL,
    tp2         DOUBLE PRECISION NOT NULL,
    score       INTEGER     NOT NULL,
    fingerprint VARCHAR(64) NOT NULL UNIQUE,  -- §25 dedup
    status      VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS signal_delivery (
    id           SERIAL PRIMARY KEY,
    broadcast_id VARCHAR(40) NOT NULL,
    signal_id    INTEGER REFERENCES signal(id),
    user_id      INTEGER NOT NULL REFERENCES "user"(id),
    message_id   VARCHAR(64),
    status       VARCHAR(20) NOT NULL DEFAULT 'QUEUED',
    attempts     INTEGER NOT NULL DEFAULT 0,
    scheduled_at TIMESTAMPTZ,
    sent_at      TIMESTAMPTZ,
    failed_at    TIMESTAMPTZ,
    error        VARCHAR(200)
);
CREATE INDEX IF NOT EXISTS ix_delivery_broadcast ON signal_delivery(broadcast_id);
CREATE INDEX IF NOT EXISTS ix_delivery_user ON signal_delivery(user_id);

CREATE TABLE IF NOT EXISTS audit_log (
    id                SERIAL PRIMARY KEY,
    user_id           INTEGER,
    channel           VARCHAR(20) NOT NULL,
    action            VARCHAR(40) NOT NULL,
    message_type      VARCHAR(40),
    reason            VARCHAR(200),
    policy_result     VARCHAR(40),
    rate_limit_result VARCHAR(40),
    delivery_status   VARCHAR(40),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_audit_user ON audit_log(user_id);
