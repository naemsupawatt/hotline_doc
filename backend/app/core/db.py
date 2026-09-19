from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session]:
    """FastAPI dependency — เปิด/ปิด session ให้อัตโนมัติต่อ 1 request"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
