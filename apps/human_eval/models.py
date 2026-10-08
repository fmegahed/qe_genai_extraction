import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import relationship

from database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class ReviewerToken(Base):
    __tablename__ = "reviewer_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    reviewer_name = Column(String(500), nullable=False)
    reviewer_email = Column(String(500), nullable=True)
    # Ordered list of [document_id, model_name] pairs fixing this reviewer's sequence
    item_order = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    ratings = relationship("Rating", back_populates="token", order_by="Rating.position")


class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token_id = Column(Integer, ForeignKey("reviewer_tokens.id"), nullable=False)
    position = Column(Integer, nullable=False)  # 1-based position in the reviewer's sequence
    document_id = Column(Integer, nullable=False)
    model_name = Column(String(100), nullable=False)

    manufacturer_rating = Column(Integer, nullable=False)
    models_rating = Column(Integer, nullable=False)
    model_years_rating = Column(Integer, nullable=False)

    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, nullable=True)

    __table_args__ = (UniqueConstraint("token_id", "position", name="uq_token_position"),)

    token = relationship("ReviewerToken", back_populates="ratings")
