"""Local persistence layer using SQLite + SQLAlchemy.

Stores Playlists, Curators, and Submissions for offline workflow.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

# Placeholder — full ORM models + migrations (alembic) will live here in next iteration.


class Base(DeclarativeBase):
    pass


# Example future table
# class PlaylistDB(Base):
#     __tablename__ = "playlists"
#     id: Mapped[int] = mapped_column(primary_key=True)
#     ...


def get_engine(db_path: Optional[Path] = None):
    """Get SQLAlchemy engine. Defaults to data/dkplaylister.db"""
    if db_path is None:
        db_path = Path("data") / "dkplaylister.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{db_path}", echo=False)


def get_session(db_path: Optional[Path] = None):
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()
