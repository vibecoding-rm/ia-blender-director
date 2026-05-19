from pathlib import Path
from sqlalchemy import create_engine, Column, String, Integer, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker

ROOT = Path(__file__).resolve().parents[2]
DB_DIR = ROOT / "renders"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "jobs.db"

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
