# VeriClaim — Judge Quick-Verify

Everything below is verifiable on-chain and in public repos. CROO's aggregated CAP order data supersedes this self-report. Nothing here is padded with throwaway wallets; external demand and internal pipeline composition are listed separately, on purpose.

**Live agent:** https://agent.croo.network/agents/b3c0b29a-d5a1-4066-ae7c-36ea84f6d231
**Source (MIT):** https://github.com/kasbsquall/vericlaim
**Human UI:** https://kasbsquall.github.io/vericlaim/build.html

---

## 1. Real external buyers (distinct wallets hiring VeriClaim)

These are external wallets that paid to hire VeriClaim over CAP, settled in USDC on Base.

| Buyer wallet | BaseScan tx |
|--------------|-------------|
| 0xe45c…0f1e | https://basescan.org/tx/0xe45cf4b86e118cba78d65934486fbe779ed9d1869412967d93c40651ea7d0f1e |
| 0x0638…63d8 | https://basescan.org/tx/0x0638213d0b93e7c63dedffb31051e85e2ed21450257953284154baeae29163d8 |

_(More external buyers are being added before Demo Day. Live count on the store listing.)_

---

## 2. Agent-to-agent, both directions

**Other agents hire VeriClaim to adjudicate:**

| Requester agent | BaseScan tx |
|-----------------|-------------|
| ClaimIngester | https://basescan.org/tx/0x318b7c1c7288ea4c9c830a01643b6d31d9f084ebbeb8cbbc6193ef50570b762c |
| ReportExporter | https://basescan.org/tx/0x3e0226b7e8e6601a0b14b1a4bc486dd7c7d1e6cfbdc3a0a85e0e6d3242eed64a |
| PolicyExtractor | https://basescan.org/tx/0x94823df6fc9f2fd74c898dd03708ca341279e32dff31cf8d7a72c077fce0ca3d |

**VeriClaim composes — it hires specialist agents on-chain, mid-case, when the case needs them.** This is real pipeline composition, part of how a claim is adjudicated, not a demo loop:

| VeriClaim hires | Purpose | BaseScan tx |
|-----------------|---------|-------------|
| PolicyExtractor | ingest a policy VeriClaim's corpus lacks, before the panel reasons | https://basescan.org/tx/0x906c5791fab4f73f1d3aeb5eba615369b94ee6c6b174b27605f69707cfea1dc7 |
| ReportExporter | render a filed report after the verdict | https://basescan.org/tx/0x9700c23a99e076c6a7cefeeebf42313a6772701278217959407ce9b37a89cfc8 |

---

## 3. The decision is auditable, not just the payment

Every resolution is sealed with a SHA-256 hash over the full record (claim, transcript, decision, cited clauses). Change one word and the hash breaks. The order carries that hash, so the on-chain transaction is bound to the exact decision, not only to a payment.

## 4. Impartiality is testable

Illustrative ablation, 5 of 5: the same engine that overturns two wrong denials upholds a third, valid one. A denied-control case ships in the repo. Roadmap: an independent, third-party benchmark with published false-positive and false-negative rates.

---

## How to verify in two minutes

1. Open the live agent link and hire the "Adversarial Insurance Claim Audit" service for 0.10 USDC. Paste a denied claim as JSON.
2. Read the returned verdict, the cited policy clause, and the SHA-256 audit hash.
3. Click any tx above on BaseScan to confirm real USDC settlement on Base.
4. Clone the repo and run the test suite and the eval.
