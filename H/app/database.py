from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from . import models  # noqa: F401  确保模型注册到 Base.metadata
    Base.metadata.create_all(bind=engine)
    _migrate_legacy()
    from .seed_topics import seed_topics
    seed_topics()


def _migrate_legacy():
    """老库补列(SQLite 只能 ALTER ADD COLUMN)。新库建表已含这些列。"""
    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            words_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(words)"))}
            if "groups" not in words_cols:
                conn.execute(text("ALTER TABLE words ADD COLUMN groups JSON DEFAULT '[]'"))
            article_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(reading_articles)"))}
            if "stage" not in article_cols:
                conn.execute(text("ALTER TABLE reading_articles ADD COLUMN stage VARCHAR DEFAULT ''"))
            topic_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(writing_topics)"))}
            if "stage" not in topic_cols:
                conn.execute(text("ALTER TABLE writing_topics ADD COLUMN stage VARCHAR DEFAULT ''"))
            if "groups" not in topic_cols:
                conn.execute(text("ALTER TABLE writing_topics ADD COLUMN groups JSON DEFAULT '[]'"))
            conn.commit()
    except Exception:  # noqa: BLE001 非 SQLite 或表未建等情况忽略,由 create_all 兜底
        pass
