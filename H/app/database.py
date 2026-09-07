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
    _migrate_user_isolation()
    _cleanup_stale_auth()
    from .seed_topics import seed_topics
    seed_topics()


def _cleanup_stale_auth():
    """启动时清理过期的登录会话与密码重置 token(数量极小,全表删除即可)。"""
    from datetime import datetime

    from sqlalchemy import delete

    from .models import AuthSession, PasswordResetToken

    try:
        with engine.begin() as conn:
            now = datetime.now()
            conn.execute(delete(AuthSession).where(AuthSession.expires_at <= now))
            conn.execute(delete(PasswordResetToken).where(PasswordResetToken.expires_at <= now))
    except Exception:  # noqa: BLE001 表未建等情况忽略,由 create_all 兜底
        pass


def _migrate_user_isolation():
    """多用户改造迁移(幂等,单事务):
    - words:加 user_id 列,全局唯一索引换成 (user_id, word) 复合唯一
    - word_groups / topic_groups:重建表,把 name 的唯一约束改成每用户唯一
    - 其余业务表:加 user_id 列 + 索引
    - 老的自建作文题打 'legacy' 哨兵,避免被当成内置共享题泄漏给所有用户

    幂等判断:word_groups 表是否已有 user_id 列(该表只能靠重建迁移,是最可靠的标志)。
    """
    from sqlalchemy import text

    with engine.begin() as conn:
        wg_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(word_groups)"))}
        if "user_id" in wg_cols:
            return

        # 1) words:加列 + 换复合唯一索引(SQLite 唯一索引中 NULL 行互不冲突,老数据安全)
        conn.execute(text("ALTER TABLE words ADD COLUMN user_id VARCHAR"))
        conn.execute(text("DROP INDEX ix_words_word"))
        conn.execute(text("CREATE UNIQUE INDEX uq_words_user_word ON words (user_id, word)"))

        # 2) word_groups / topic_groups:重建表(无入向外键,显式列序拷贝)
        for tbl in ("word_groups", "topic_groups"):
            new = f"{tbl}_new"
            conn.execute(text(
                f"CREATE TABLE {new} ("
                "id VARCHAR NOT NULL, name VARCHAR NOT NULL, created_at DATETIME NOT NULL, "
                "user_id VARCHAR, PRIMARY KEY (id), UNIQUE (user_id, name))"
            ))
            conn.execute(text(
                f"INSERT INTO {new} (id, name, created_at, user_id) "
                f"SELECT id, name, created_at, NULL FROM {tbl}"
            ))
            conn.execute(text(f"DROP TABLE {tbl}"))
            conn.execute(text(f"ALTER TABLE {new} RENAME TO {tbl}"))
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{tbl}_user_id ON {tbl} (user_id)"))

        # 3) 其余业务表:加列 + 索引
        for tbl in ("chat_sessions", "quizzes", "reading_articles", "writing_topics"):
            cols = {row[1] for row in conn.execute(text(f"PRAGMA table_info({tbl})"))}
            if "user_id" not in cols:
                conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN user_id VARCHAR"))
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{tbl}_user_id ON {tbl} (user_id)"))

        # 4) 老的自建作文题(非内置 t_1..t_15)打哨兵。
        #    不能用 GLOB 't_[0-9]*' 判断:gen_id("t") 的 hex 首字符可为数字,会误伤自建题
        builtin_ids = ", ".join(f"'{f't_{i}'}'" for i in range(1, 16))
        conn.execute(text(
            f"UPDATE writing_topics SET user_id = 'legacy' WHERE id NOT IN ({builtin_ids})"
        ))


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
