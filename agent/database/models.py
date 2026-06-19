"""SQLAlchemy 2.0 models mirroring schema.sql.

Simplified vs Recourse: a single Verification row captures each CAP call (caller wallet,
USDC paid, claim input, debate transcript, decision, audit hash). PolicyClause holds the
pgvector-embedded clause corpus that Morgan's RAG search reads.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pgvector.sqlalchemy import Vector
from sqlalchemy import DECIMAL, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from config import settings


class Base(DeclarativeBase):
    pass


class Verification(Base):
    __tablename__ = "verifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cap_call_id: Mapped[str | None] = mapped_column(String(200), unique=True)
    caller_wallet: Mapped[str | None] = mapped_column(String(200))
    payment_usdc: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 4))
    claim_input: Mapped[dict] = mapped_column(JSONB)
    debate_transcript: Mapped[list | None] = mapped_column(JSONB)
    decision: Mapped[str | None] = mapped_column(String(20))
    approved_amount: Mapped[Decimal | None] = mapped_column(DECIMAL(12, 2))
    legal_reasoning: Mapped[str | None] = mapped_column(Text)
    cited_clauses: Mapped[list | None] = mapped_column(JSONB, default=list)
    audit_hash: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PolicyClause(Base):
    __tablename__ = "policy_clauses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    policy_type: Mapped[str | None] = mapped_column(String(50))
    clause_number: Mapped[str] = mapped_column(String(20))
    clause_title: Mapped[str | None] = mapped_column(String(200))
    clause_text: Mapped[str] = mapped_column(Text)
    clause_type: Mapped[str | None] = mapped_column(String(50))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.embedding_dim))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
