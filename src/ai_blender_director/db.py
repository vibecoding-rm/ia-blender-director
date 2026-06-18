from pathlib import Path
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, func
from sqlalchemy.orm import declarative_base, sessionmaker

ROOT = Path(__file__).resolve().parents[2]
DB_DIR = ROOT / "renders"
DB_PATH = DB_DIR / "jobs.db"

Base = declarative_base()
_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
    return _engine


def ensure_database() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=get_engine())


class _LazySessionLocal:
    def __call__(self):
        global _session_factory
        ensure_database()
        if _session_factory is None:
            _session_factory = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
        return _session_factory()


SessionLocal = _LazySessionLocal()


class JobRecord(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, nullable=False)
    event = Column(String, nullable=False)
    profile = Column(String, nullable=False)
    job_dir = Column(String, nullable=False)
    source_shot = Column(String, nullable=False)
    returncode = Column(Integer, nullable=True)
    timestamp = Column(DateTime, server_default=func.now(), onupdate=func.now())


class PlanRecord(Base):
    """Persistent storage for Director plans — survives server restarts."""
    __tablename__ = "plans"

    plan_id = Column(String, primary_key=True, index=True, nullable=False)
    status = Column(String, nullable=False, default="running")
    job_ids = Column(Text, nullable=False, default="[]")  # JSON-encoded list
    video = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
