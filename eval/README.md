# Eval — does the adversarial debate actually decide better?

A frequent (fair) critique of multi-agent demos: *"couldn't one good GPT-4o prompt do the same?"*
This eval answers it head-on. We run the **same claims** through:

- **VeriClaim** — the 5/6-agent adversarial debate (Coordinator → Blake → Morgan w/ RAG → Alex → [Quinn on fraud] → Sam), and
- **Single GPT-4o** — one strong adjudication call, given the identical claim.

Reproduce: `.venv/Scripts/python eval/run_eval.py` (DB up). Raw output in [`results.json`](results.json).

## Results

| Case | Expected | VeriClaim (debate) | Single GPT-4o (1 call) |
|---|---|---|---|
| Collision — denial cites **§7.3** exclusion; **§12.1** collision-exception applies | APPROVED $12,000 | ✅ APPROVED $12,000 · cites **§12.1** (the exception) + §7.3 · 4 agents | APPROVED $12,000 · cites only **§7.3** |
| Theft — denial alleges undisclosed rideshare (fraud), unsupported | APPROVED $3,700 | ✅ APPROVED $3,700 · cites §7.4 (the fraud clause it overturns) · **recruits Quinn (SIU)** · 5 agents | APPROVED $3,700 · cites only §5.2 |

**Decision accuracy:** VeriClaim 2/2 · single GPT-4o 2/2.

## What the numbers actually show

On the **decision**, a strong single call reaches the same outcome — these claims include supporting
documents that make the right answer reachable. The measurable delta is in **grounding and
auditability**, which is precisely what separates *an answer* from a *legally-defensible verdict*:

1. **Correct clause grounding (the key delta).** On the collision case the single LLM **approved the
   claim while citing §7.3 — the *exclusion*, i.e. the reason to *deny***. That is an internally
   inconsistent ruling. VeriClaim cites **§12.1**, the actual exception that *justifies* the approval,
   retrieved verbatim from the policy by Morgan's RAG. A verdict you can defend has to cite the clause
   that *governs the outcome*, not the one it overrides.
2. **Dynamic specialist recruitment.** The fraud case caused VeriClaim to recruit **Quinn (SIU)** — a
   sixth agent that exists only to test fraud allegations. A single call has no notion of escalating to
   a specialist; the panel composition itself adapts to the case.
3. **Auditability.** VeriClaim emits the full multi-agent transcript and seals it with a tamper-evident
   SHA-256 hash over {claim + transcript + decision + amount}. The single call is a black box.

**Takeaway:** the debate isn't a stylistic flourish — it produces **correctly-grounded, specialist-
augmented, tamper-evident rulings** where a single LLM produces a bare (and here, mis-cited) answer.

## Honest limitations / next

These two cases don't force a *decision* divergence (the evidence is in the claim). A stronger eval
would add cases where the governing exception lives **only** in the policy corpus (so RAG is required
to find it) and cases of genuine exclusions where a naive call tends to **over-approve** — that's where
a decision-level delta would appear. Tracked as future work.
