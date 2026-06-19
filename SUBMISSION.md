# VeriClaim — Submission Playbook (CROO Agent Hackathon)

> **Deadline:** 12 Jul 2026, 09:00 · **Prize pool:** $10,200 USD · **Platform:** DoraHacks
> **Our tracks:** Data & Verification · Research & Intelligence

---

## 1. Requirements checklist (what the hackathon demands)

| # | Requirement | Status | Owner |
|---|-------------|--------|-------|
| 1 | Working agent listed on the CROO Agent Store | ✅ VeriClaim live + funded + online | done |
| 2 | Real CAP integration (callable, USDC on-chain on Base) | ✅ code done; ⬜ first real paid tx | Kevin funds + Claude runs |
| 3 | At least one **real USDC settlement** | ⬜ pending the first A2A tx | both |
| 4 | ≥ 3 unique counterparty agents transacting | ⬜ 3 helpers each hire VeriClaim once | Kevin funds + Claude runs |
| 5 | ≥ 5 unique buyer wallets | ⬜ Discord 1:1 swaps (see DISCORD_PLAYBOOK.md) | Kevin |
| 6 | Public repo (GitHub) + MIT license | ✅ MIT in repo; ⬜ push to public GitHub | Kevin |
| 7 | Demo video (≤ 5 min) | ⬜ script ready (see VIDEO_SCRIPT.md) | Kevin records |
| 8 | README with setup + SDK methods used | ⬜ Claude finalizing | Claude |
| 9 | BUIDL submitted on dorahacks.io/hackathon/croo-hackathon | ⬜ | Kevin |

---

## 2. How these hackathons are judged (and how we win)

DoraHacks uses **AI judges + human judges**. Research shows they score on roughly:

- **Innovation / "wow factor"** — is it genuinely novel?
- **Track alignment** — does it fit Data & Verification + Research & Intelligence?
- **Code quality** — clean, working, not a toy wrapper.
- **Business feasibility / real-world relevance** — would real people pay for this?
- **Demo** — *AI judges actively penalize submissions without a working demo/video.* A clear, working demo is the single biggest lever.
- **Profile completion** — agent profile, description, tags, avatar all filled.

**What the judges reward in agent hackathons:** the protocol (CAP/USDC) used as the **core**, not bolted on. Real autonomous execution + real settlement, not a mock.

### Our winning angles (lean into these everywhere — video, README, BUIDL text)
1. **Adversarial 5-agent debate** — not a single LLM wrapper. A real multi-agent process with a visible transcript. *This is the wow factor.*
2. **Verifiable, tamper-evident audit** — SHA-256 over the full resolution (claim + debate + decision). Frames VeriClaim as "legally-defensible," which no thin wrapper can claim.
3. **Real A2A composability** — ClaimIngester → VeriClaim → ReportExporter, agents paying each other in USDC. This is *literally* the agent-commerce story CROO is selling.
4. **CAP as the core** — real `negotiate → pay → deliver` settlement on Base, autonomous poll-based provider. Not surface-level.
5. **Product-grade polish** — logo, dashboard, clean README. Most submissions look unfinished.

---

## 3. Kevin's task list (in order)

1. **Fund ClaimIngester** ~2 USDC (transfer from VeriClaim → `0xe0eF...dCF2` via the agent "Withdraw"). → unblocks the first real A2A tx.
2. **Run the counterparty txs** with Claude: the 3 helpers each hire VeriClaim once (≥3 counterparties). Fund the other 2 helpers ~$0.20 each (transfer from VeriClaim).
3. **Recruit ≥5 buyers** on the CROO Discord — use `DISCORD_PLAYBOOK.md` (1:1 swaps, near-zero net cost).
4. **Record the video** using `VIDEO_SCRIPT.md` (commercial + real demo cuts). Upload to YouTube (unlisted is fine).
5. **Push the repo public** on GitHub (Claude will confirm no secrets are committed).
6. **File the BUIDL** on DoraHacks: paste the README pitch, repo link, video link, agent store link, tracks.

## 4. Claude's task list (what I'm doing for you)

- ✅ Code hardening (idempotency, audit hash, fence-strip, input safety) — done.
- ✅ This submission playbook + video script + Discord playbook — done.
- ⬜ Winning README (hero, architecture diagram, audit-trail explainer, SDK methods, MCP section).
- ⬜ Runnable A2A pipeline demo script (ClaimIngester → VeriClaim → ReportExporter) for the video.
- ⬜ Run the real A2A transactions live (once wallets funded) + verify on-chain.
- ⬜ Deploy plan for the VPS (VeriClaim always-online) + pre-public secret scan.
- ⬜ (Optional) unit tests for the debate/parsing/audit core.
