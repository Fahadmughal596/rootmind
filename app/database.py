from datetime import datetime, timezone
from sqlalchemy import create_engine, DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from app.config import settings

class Base(DeclarativeBase):
    pass

class IncidentRecord(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    service: Mapped[str] = mapped_column(String(255))
    deployment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(64))
    result_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

def create_tables():
    Base.metadata.create_all(bind=engine)
