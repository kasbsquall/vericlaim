# Eval — does the adversarial debate actually decide better?

A frequent (fair) critique of multi-agent demos: *"couldn't one good GPT-4o prompt do the same?"*
This eval answers it head-on — **and honestly**, with an ablation. We run the **same claims** through
three configurations:

- **VeriClaim** — the 5/6-agent adversarial debate (Coordinator → Blake → Morgan w/ RAG → Alex → [Quinn on fraud] → Sam),
- **Single GPT-4o (no RAG)** — one strong adjudication call, given only the claim, and
- **Single GPT-4o (+RAG)** — the *same* single call, but handed the same policy clauses Morgan retrieves (the **ablation arm** that isolates retrieval from the debate).

Reproduce: `.venv/Scripts/python eval/run_eval.py` (DB up). Raw output in [`results.json`](results.json).

## Results

| Case | Expected | VeriClaim (debate+RAG) | Single GPT-4o (no RAG) | Single GPT-4o (+RAG) |
|---|---|---|---|---|
| Collision — §7.3 exclusion vs §12.1 collision-exception | APPROVED $12,000 | ✅ cites **§12.1** + §7.3 | ✅ but cites only **§7.3** (the exclusion) | ✅ cites §12.1 |
| Theft — unsupported rideshare/fraud allegation | APPROVED $3,700 | ✅ **recruits Quinn (SIU)** | ✅ cites §5.2 | ✅ cites §5.2 |
| Mechanical failure — genuine wear-and-tear, no collision | **DENIED** | ✅ weighs §12.1 & **rejects** it | ✅ §7.3 | ✅ §7.3 |
| Commercial-use (§7.4) — overturned only by **§12.3** (corpus-only) | APPROVED $6,300 | ✅ §12.3 → **$6,300** | ❌ **DENIED $0** | ✅ §12.3 → $6,300 |
| Substantiated fraud — 240 concealed rideshare trips vs a signed "personal use only" attestation | **DENIED** | ✅ **Quinn UPHOLDS** — §12.3 de-minimis rejected (240≫10), §7.4 applies | ✅ DENIED | ✅ DENIED |

**Decision accuracy:** VeriClaim **5/5** · single GPT-4o **no-RAG 4/5** · single GPT-4o **+RAG 5/5**.

## What the ablation actually proves (the honest part)

1. **The decision moat is RETRIEVAL, not agent count.** Strip the policy corpus and a strong single LLM
   drops to 3/4 — it *wrongly DENIES* the §7.4 commercial-use claim because the governing safe-harbor
   (§12.3 *de-minimis*) lives only in the policy, not in general knowledge. Hand that **same single call**
   the retrieved clauses and it recovers to 4/4. So the §12.3 win is **RAG's** — and we say so plainly,
   not "six agents are smarter than one."
2. **So why the panel?** Because a verdict isn't just a decision — it's a **defensible, inspectable
   record**. A single call (even with RAG) is a black box that emits an answer. VeriClaim produces what
   that can't:
   - a **clause-by-clause adversarial transcript** — a strict insurer-side read (Blake) vs a claimant-side
     challenge (Alex), weighed by a neutral notary (Sam) — so the *reasoning* is auditable, not just the output;
   - **impartiality by construction** (the wear-and-tear control: the same panel *upholds* a valid denial → DENIED, not a rubber stamp);
   - a **dynamically-recruited fraud specialist** (Quinn) that cuts **both ways** — it *cleared* an unsupported rideshare allegation (theft case → APPROVED) *and* **upheld** a substantiated one (240 concealed trips vs a signed "personal use only" attestation → DENIED). Not a claimant rubber stamp either;
   - a **tamper-evident SHA-256 audit** over {claim + full transcript + decision + amount}.
3. **Grounding, not guessing.** Even where decisions match, VeriClaim cites the clause that *governs the
   outcome* (§12.1, the exception) — where the no-RAG single call approved while citing §7.3, the
   *exclusion* it was supposed to overcome (an internally inconsistent ruling).

**Takeaway, stated honestly:** the **decision** moat is RAG; the **trust** moat is the adversarial,
impartial, audited process. VeriClaim's value isn't "more agents decide better" — it's *"RAG-grounded
decisions delivered as a transparent, impartial, tamper-evident record, callable on-chain."*

## Honest limitations / next

n=5, hand-built — illustrative, not a benchmark. The debate does **not** beat a retrieval-equipped single
call on *decision* in this suite; its edge is auditability, impartiality, and specialist recruitment. A
fuller eval would (a) scale to dozens of corpus-only exceptions and (b) test whether the adversarial
transcript catches bad-faith or prompt-injected denials that a single call rubber-stamps. Tracked as next work.
