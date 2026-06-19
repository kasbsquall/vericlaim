-- VeriClaim database schema. Idempotent: safe to run repeatedly.
-- Auto-applied by docker-compose on a fresh DB volume, and re-applied by seed_data.py.
--
-- Differs from Recourse: a single `verifications` table captures each CAP call
-- (caller wallet, USDC paid, claim input, debate transcript, decision, audit hash)
-- instead of Recourse's separate claims/agent_messages/resolutions tables.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cap_call_id VARCHAR(200) UNIQUE,            -- CAP order/call id
    caller_wallet VARCHAR(200),                 -- wallet that hired VeriClaim
    payment_usdc DECIMAL(10,4),                 -- USDC paid for this verification
    claim_input JSONB NOT NULL,                 -- structured claim payload
    debate_transcript JSONB,                    -- ordered [{agent, content}, ...]
    decision VARCHAR(20),                       -- APPROVED / DENIED / PARTIAL
    approved_amount DECIMAL(12,2),
    legal_reasoning TEXT,
    cited_clauses JSONB,                        -- ["§7.3", "§12.1", ...]
    audit_hash VARCHAR(64),                     -- SHA-256 of the transcript
    status VARCHAR(20) DEFAULT 'pending',       -- pending / completed / failed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS policy_clauses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_type VARCHAR(50),
    clause_number VARCHAR(20),
    clause_title VARCHAR(200),
    clause_text TEXT NOT NULL,
    clause_type VARCHAR(50),
    embedding vector(384),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_policy_clauses_embedding
    ON policy_clauses USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
