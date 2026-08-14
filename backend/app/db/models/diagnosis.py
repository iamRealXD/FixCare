import uuid
from datetime import datetime, UTC
from typing import TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SQLEnum, Integer, Float, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
import enum


if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.device import Device


class DiagnosisSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskLevel(str, enum.Enum):
    SAFE = "safe"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class DiagnosisStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("devices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    device_category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    problem_summary: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[DiagnosisSeverity] = mapped_column(
        SQLEnum(DiagnosisSeverity),
        nullable=False,
        default=DiagnosisSeverity.MEDIUM,
    )
    status: Mapped[DiagnosisStatus] = mapped_column(
        SQLEnum(DiagnosisStatus),
        nullable=False,
        default=DiagnosisStatus.PENDING,
        index=True,
    )
    technician_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    technician_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ai_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="diagnoses")
    device: Mapped["Device"] = relationship(back_populates="diagnoses")
    messages: Mapped[list["DiagnosisMessage"]] = relationship(back_populates="diagnosis", cascade="all, delete-orphan")
    results: Mapped[list["DiagnosisResult"]] = relationship(back_populates="diagnosis", cascade="all, delete-orphan")
    feedback: Mapped[list["DiagnosisFeedback"]] = relationship(back_populates="diagnosis", cascade="all, delete-orphan")
    ai_logs: Mapped[list["AIRequestLog"]] = relationship(back_populates="diagnosis", cascade="all, delete-orphan")


class DiagnosisMessage(Base):
    __tablename__ = "diagnosis_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    diagnosis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("diagnoses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    diagnosis: Mapped["Diagnosis"] = relationship(back_populates="messages")


class DiagnosisResult(Base):
    __tablename__ = "diagnosis_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    diagnosis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("diagnoses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    possible_causes: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    safe_steps: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    risks: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    follow_up_questions: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    disclaimer: Mapped[str] = mapped_column(Text, nullable=False)
    raw_ai_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    diagnosis: Mapped["Diagnosis"] = relationship(back_populates="results")


class DiagnosisFeedback(Base):
    __tablename__ = "diagnosis_feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    diagnosis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("diagnoses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    was_helpful: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    resolved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    diagnosis: Mapped["Diagnosis"] = relationship(back_populates="feedback")


class AIRequestLog(Base):
    __tablename__ = "ai_request_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    diagnosis_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("diagnoses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    request_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    response_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped.column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    diagnosis: Mapped["Diagnosis"] = relationship(back_populates="ai_logs")