import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Problem(Base):
    __tablename__ = "problems"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    url = Column(Text, nullable=False)
    title = Column(String(255), nullable=False)
    topic = Column(String(100), nullable=False, index=True)
    difficulty = Column(String(32), nullable=False, index=True)
    notes = Column(Text, nullable=True)
    solution_or_hints = Column(Text, nullable=True)
    content_html = Column(Text, nullable=True)
    status = Column(String(32), default="active", nullable=False)

    current_interval_days = Column(Integer, default=1, nullable=False)
    ease_factor = Column(Float, default=2.5, nullable=False)
    repetitions = Column(Integer, default=0, nullable=False)
    last_struggle_rating = Column(String(64), nullable=True)
    last_reviewed_at = Column(DateTime, nullable=True)
    next_review_due = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="problems")
    review_logs = relationship("ReviewLog", back_populates="problem", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_problems_user_next_review", "user_id", "next_review_due"),)