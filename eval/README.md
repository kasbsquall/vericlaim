# Eval — does the adversarial debate actually decide better?

A frequent (fair) critique of multi-agent demos: *"couldn't one good GPT-4o prompt do the same?"*
This eval answers it head-on. We run the **same claims** through:

- **VeriClaim** — the 5/6-agent adversarial debate (Coordinator → Blake → Morgan w/ RAG → Alex → [Quinn on fraud] → Sam), and
- **Single GPT-4o** — one strong adjudication call, given the identical claim.

Reproduce: `.venv/Scripts/python eval/run_eval.py` (DB up). Raw output in [`results.json`](results.json).

## Results

| Case | Expected | VeriClaim (debate) | Single GPT-4o (1 call) |
|---|---|---|---|
| Collision — denial cites **§7.3** exclusion; **§12.1** collision-exception applies | APPROVED $12,000 | ✅ APPROVED $12,000 · cites **§12.1** (the exception) + §7.3 | APPROVED $12,000 · cites only **§7.3** (the exclusion) |
| Theft — denial alleges undisclosed rideshare (fraud), unsupported | APPROVED $3,700 | ✅ APPROVED $3,700 · **recruits Quinn (SIU)** · cites §7.4 | APPROVED $3,700 · cites only §5.2 |
| Mechanical failure — genuine wear-and-tear, **no collision**; §7.3 applies, no exception | **DENIED** | ✅ **DENIED** · weighs §12.1/§2.1 and **rejects** them (no collision) | DENIED · cites §7.3 |
| Commercial-use denial (**§7.4**) — overturned **only** by the **§12.3 de-minimis** exception, which lives in the policy corpus | APPROVED $6,300 | ✅ **APPROVED $6,300** · RAG surfaces **§12.3** (under-10 incidental trips) → §7.4 doesn't bar | ❌ **DENIED $0** · applies §7.4; **never sees §12.3** |

**Decision accuracy:** VeriClaim **4/4** · single GPT-4o **3/4**.

## What the numbers actually show

1. **A real decision-level delta where retrieval is load-bearing (the headline).** On the §7.4
   commercial-use case the insured was rear-ended *while making a paid delivery* — so the exclusion
   applies on its face, and the single LLM correctly-but-wrongly **DENIES** the whole claim. The thing
   that overturns it — **§12.3**, a *de-minimis incidental-use* safe harbor (fewer than 10 paid trips
   per month) — exists **only in the policy corpus**, not in general knowledge or the claim text.
   VeriClaim's RAG (Morgan) retrieves it; the panel applies it; the verdict flips to **APPROVED
   $6,300**. A single call cannot reach the right answer because it never has the governing clause.
   *This is the debate + RAG changing the outcome, not just the citation.*
2. **Correct clause grounding even when the decision matches.** On the collision case both APPROVE, but
   the single LLM **approved while citing §7.3 — the *exclusion*, the reason to *deny*** (internally
   inconsistent). VeriClaim cites **§12.1**, the exception that actually *justifies* the approval,
   retrieved verbatim. A verdict you can defend has to cite the clause that *governs the outcome*.
3. **Impartial — not a rubber stamp.** The wear-and-tear case is the **control**: the same engine that
   overturns two wrong denials *upholds* a valid one (DENIED), and on the way it actively weighs the
   §12.1 exception and *rejects* it (no collision) rather than ignoring it.
4. **Dynamic specialist recruitment.** The fraud case recruits **Quinn (SIU)** — a sixth agent that
   exists only to test the allegation. A single call has no notion of escalating to a specialist.
5. **Auditability.** VeriClaim emits the full transcript and seals it with a tamper-evident SHA-256 hash
   over {claim + transcript + decision + amount}. The single call is a black box.

**Takeaway:** when the deciding clause is in the claim, a strong single LLM matches the *decision* (and
VeriClaim still wins on grounding, impartiality, and audit). When the governing clause lives **in the
policy** — the realistic case — the single LLM gets the **decision wrong**, and the RAG-grounded panel
gets it right.

## Honest limitations / next

Three of four cases carry the deciding evidence in the claim itself, so the single LLM matches the
decision there; the §12.3 case is the one that *requires* retrieval. This is a small, hand-built suite
(n=4) meant to be illustrative, not a benchmark — a fuller eval would scale to dozens of corpus-only
exceptions and genuine fraud cases. Tracked as next work.
