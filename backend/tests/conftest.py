import os
import sys
from pathlib import Path

# repo root = parent dari backend/
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT)  # chart & db relatif ke repo root

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.db import Base  # noqa: E402


@pytest.fixture()
def db_session():
    """In-memory DB per test — terisolasi, tidak menyentuh goldvision.db."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()
    yield session
    session.close()
