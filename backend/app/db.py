"""Database engine & session. Dev default SQLite; production PostgreSQL via DATABASE_URL."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.settings import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    url = get_settings().database_url
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Buat semua tabel (mode development). Production memakai migration terkelola."""
    from app import models  # noqa: F401 — register semua model ke Base

    Base.metadata.create_all(engine)
    _sqlite_automigrate()


def _sqlite_automigrate() -> None:
    """Tambahkan kolom yang hilang pada tabel sqlite lama (idempotent, additive-only).

    create_all TIDAK mengubah tabel eksisting — tanpa ini, DB buatan versi lama
    = OperationalError saat kolom baru dipakai. Kolom diambil dari metadata model,
    jadi tidak ada daftar manual yang bisa drift.
    """
    if engine.dialect.name != "sqlite":
        return
    from sqlalchemy import inspect, text

    from app.db import Base

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in table_names:
                continue
            existing = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing:
                    continue
                col_type = column.type.compile(engine.dialect)
                ddl = f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {col_type}'
                # Baris lama di-backfill dengan nilai default skalar model,
                # supaya tidak ada NULL untuk kolom yang semestinya 0/False.
                if column.default is not None and column.default.is_scalar:
                    val = column.default.arg
                    if isinstance(val, bool):
                        lit = "1" if val else "0"
                    elif isinstance(val, (int, float)):
                        lit = str(val)
                    else:
                        lit = "'" + str(val).replace("'", "''") + "'"
                    ddl += f" DEFAULT {lit}"
                conn.execute(text(ddl))
