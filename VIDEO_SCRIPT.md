# VeriClaim — Demo Video Script (commercial + real-demo cut)

**Format:** commercial storytelling that makes the viewer *feel the problem*, then reveals the
product and proves it's real with on-screen captures. **Target length: ~2:15** (well under the
5-min cap — judges reward tight, working demos). Language: **English** (international judges).
Tone: cinematic, confident, a little defiant ("the little guy finally has leverage").

> Legend — **[VO]** = voiceover narration · **[SCREEN]** = what's on screen · **[TEXT]** = on-screen caption · **[SFX/MUSIC]** = audio.

> 🎙️ **The audio is already produced** → `vericlaim-video/final_audio.mp3` (~82s: an ElevenLabs "George" voiceover + a subtle music bed at ~16%, pre-mixed with fades). Lay it on your timeline and **record the visuals below to match it.** Master narration text: `vericlaim-video/narration.txt`.
>
> ⚡ **Updated for the 6th agent (Quinn):** the panel **adapts** — 5 agents on a normal case, **6 when fraud is alleged** (Quinn, the SIU investigator). The audio already includes this beat; showcase it with the Lisa Park fraud case.

---

### 0:00–0:15 — THE COLD OPEN (the pain)
- **[SCREEN]** Black. A denial letter fades in: *"Claim CLM-2024-04471 — DENIED. Per §7.3, Mechanical Failure Exclusion."* A red **DENIED** stamp slams down.
- **[MUSIC]** Low, tense single piano note.
- **[VO]** "Your engine seized after the crash. The damage is real. The repair is $12,000. And the insurer just said… no — hiding behind one line of fine print."
- **[TEXT]** "Every year, billions in valid claims are denied on a technicality."

### 0:15–0:30 — THE INJUSTICE (twist the knife)
- **[SCREEN]** A regular person staring at the letter. Quick cuts: a clock ticking, a lawyer's hourly rate, a "60-day appeal window."
- **[VO]** "Insurers have armies of adjusters and lawyers. You have a denial letter and a deadline. The fight isn't fair — because you're fighting it alone."
- **[MUSIC]** Tension builds.

### 0:30–0:42 — THE TURN (hope appears)
- **[SCREEN]** The letter slides away. A clean dark UI fades up: the VeriClaim shield logo.
- **[VO]** "What if you weren't alone? What if you could put that denial in front of a panel that fights *for* you?"
- **[TEXT]** "Introducing **VeriClaim**."
- **[MUSIC]** Shift to hopeful, driving.

### 0:42–1:15 — THE PRODUCT (the wow: the debate) — REAL CAPTURE
- **[SCREEN]** Screen-record the **real debate** (run it live: `python helper_agents/pipeline_demo.py`, or use the dashboard transcript). Show the agents speaking in sequence, with name labels:
  - 🔵 **Blake** (Claims Evaluator) — flags §7.3.
  - 🟣 **Morgan** (Policy Analyst) — quotes §12.1 *verbatim* from the policy.
  - 🔴 **Alex** (Devil's Advocate) — "Wait —" attacks the denial, weaponizes the mechanic report.
  - 🟢 **Sam** (Resolution Notary) — issues the ruling.
- **[VO]** "Five specialized AI agents debate your case — adversarially. One quotes the policy word for word. One attacks the denial on your behalf. They find the exception the insurer ignored."
- **[TEXT]** as Sam rules: **"DECISION: APPROVED — $12,000.00"** then **"Cited: §12.1 overrides §7.3"**.
- **[MUSIC]** Hits a confident peak on "APPROVED."

### 1:00–1:12 — ⚡ THE 6th AGENT (Quinn — the differentiator) — REAL CAPTURE
- **[SCREEN]** Cut to the **Lisa Park** fraud case (run `pipeline_demo` with `sample_claim_fraud.json`). Show the panel grow **5 → 6**: a new card lights up — 🟪 **Quinn, SIU** — recruited mid-debate to investigate the fraud allegation, which the evidence doesn't support.
- **[VO]** "And when a claim is denied on suspicion of fraud, a sixth investigator is recruited — to test whether that accusation actually holds up."
- **[TEXT]** "The panel adapts. A 6th agent — Quinn (SIU) — joins only when fraud is alleged."

### 1:15–1:35 — THE PROOF (verifiable + real money) — REAL CAPTURE
- **[SCREEN]** Show the **SHA-256 audit hash** on the dashboard card, then the **on-chain transaction** (BaseScan tx for the USDC payment / the CROO order page showing PAID).
- **[VO]** "Every verdict is sealed with a tamper-evident SHA-256 audit trail — a legally-defensible record. And it all settles on-chain: VeriClaim is hired for real USDC on Base."
- **[TEXT]** "Tamper-evident. On-chain. Real settlement."

### 1:35–2:00 — THE BIG IDEA (agents hiring agents) — REAL CAPTURE
- **[SCREEN]** Animate/show the pipeline: **ClaimIngester** (reads a raw email) → hires **VeriClaim** → **ReportExporter** (produces the PDF). Show the generated PDF + the dashboard with multiple verifications + "Total cost: $0.20 USDC."
- **[VO]** "VeriClaim doesn't just work for people — it works for *other agents*. One agent reads the insured's email, hires VeriClaim to adjudicate, and a third turns the verdict into a filed PDF. Autonomous agents, hiring each other, paying in USDC. This is the agent economy — live, on CROO."
- **[TEXT]** "3 agents. 1 pipeline. Paid in USDC."

### 2:00–2:15 — THE CLOSE (the need + CTA)
- **[SCREEN]** Back to the VeriClaim logo on dark. The old red **DENIED** stamp flips to a blue **APPROVED** check.
- **[VO]** "Insurers have a panel. Now, so do you. **VeriClaim** — adversarial AI that fights for your claim."
- **[TEXT]** "Hire VeriClaim on the CROO Agent Store · $0.10 USDC" + repo/store links.
- **[MUSIC]** Resolves on a clean, confident note.

---

## Production notes
- **Wildcard cuts:** during the debate capture, it's fine to **cut the waiting time** (the ~90s of LLM thinking) — show each agent's reply appearing, jump-cut between them. Keep momentum.
- **Real beats fake:** judges (and AI judges) reward a *working* demo. Make sure at least the debate, the audit hash, and one **real on-chain tx** are genuine captures — that's the credibility.
- **Captions always on** — many judges skim muted. The on-screen TEXT must carry the story alone.
- **Show the store listing** for ~2s (proves "listed + callable") and the **two track tags**.
- **First 5 seconds decide everything** — open on the DENIED stamp + the $12,000, not on a logo.
- Export 1080p, upload to YouTube (unlisted is fine), put the link in the BUIDL + README.
