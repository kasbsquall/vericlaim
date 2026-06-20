"""pgvector cosine search over policy_clauses. Ported from Recourse's rag_service.search_clauses.

Morgan calls this to ground citations in verbatim clause text.
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import PolicyClause
from rag.embedder import embed_text


async def search_clauses(
    session: AsyncSession,
    query: str,
    policy_type: str | None = None,
    limit: int = 5,
) -> list[dict]:
    """Semantic search over policy clauses, ordered by cosine distance.

    Returns dicts with clause metadata + a similarity score (1 - distance).
    """
    # Run the (CPU-bound) encode off the event loop so it never blocks concurrent LLM I/O.
    query_embedding = await asyncio.to_thread(embed_text, query)

    distance = PolicyClause.embedding.cosine_distance(query_embedding)
    stmt = select(PolicyClause, distance.label("distance"))
    if policy_type is not None:
        stmt = stmt.where(PolicyClause.policy_type == policy_type)
    stmt = stmt.order_by(distance).limit(limit)

    rows = (await session.execute(stmt)).all()
    if not rows and policy_type is not None:
        # No clauses carry this exact policy_type label (e.g. clauses ingested by
        # PolicyExtractor under a different label). Fall back to semantic search across
        # all clauses so Morgan still gets grounded, verbatim text to cite.
        rows = (
            await session.execute(
                select(PolicyClause, distance.label("distance")).order_by(distance).limit(limit)
            )
        ).all()
    return [
        {
            "clause_number": clause.clause_number,
            "clause_title": clause.clause_title,
            "clause_text": clause.clause_text,
            "clause_type": clause.clause_type,
            "similarity": round(1.0 - float(dist), 4),
        }
        for clause, dist in rows
    ]
