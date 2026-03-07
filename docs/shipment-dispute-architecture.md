# Shipment Dispute Architecture

## Overview

The court evaluates **one disputed fact**. The settlement contract maps that fact to an outcome.

> "Did the shipment cross the Bolivian border on or before 2026-04-05?"

That is the entire scope of the court interaction. It does not decide the whole trade. It returns TRUE, FALSE, or UNDETERMINED — and the settlement contract maps those verdicts to outcomes automatically.

---

## State Machine

### Main settlement flow (no dispute)

```
DRAFT → RATE_PENDING → RATE_LOCKED → FUNDED → SETTLED
                              ↓
                       ROLL_PENDING → ROLLED → FUNDED → SETTLED
```

### Shipment dispute branch (exception path)

```
FUNDED
  │
  ▼ (importer calls contestShipment)
shipmentStatus = CONTESTED
exceptionPaused = true
  │
  ▼ (ShipmentDeadlineCourt evaluates evidence)
  │
  ├── verdict TRUE  → shipmentStatus = TIMELY
  │                   exceptionPaused = false
  │                   settlement can proceed normally
  │
  ├── verdict FALSE → shipmentStatus = LATE
  │                   cancelAndRefund(2)
  │                   importer receives full refund
  │
  └── verdict UNDETERMINED → shipmentStatus = MANUAL_REVIEW
                              exceptionPaused remains true
                              human arbitration required
```

---

## Component Map

```
TradeFxSettlement (Base Sepolia)
  │
  ├── contestShipment(evidenceCid)          ← importer calls
  │     sets shipmentStatus = CONTESTED
  │     sets exceptionPaused = true
  │
  ├── resolveShipmentVerdict(code, ref)     ← relayer delivers verdict
  │     maps code to outcome (see below)
  │
  └── (standard rate lock / roll unchanged)

ShipmentDeadlineCourt (GenLayer Studionet)
  │
  ├── submit_exporter_evidence(image_url)   ← exporter
  ├── submit_importer_evidence(image_url)   ← importer
  └── evaluate()                            ← either party triggers
        AI fetches both images
        Returns TRUE | FALSE | UNDETERMINED

Evidence (IPFS)
  ├── Exporter image URL → court fetches for AI analysis
  └── Importer image URL → court fetches for AI analysis
```

---

## Verdict Mapping Table

| Court verdict  | verdictCode | shipmentStatus | Outcome                              |
|----------------|-------------|----------------|--------------------------------------|
| TRUE           | 1           | TIMELY         | Settlement proceeds                  |
| FALSE          | 2           | LATE           | cancelAndRefund → importer refunded  |
| UNDETERMINED   | 3           | MANUAL_REVIEW  | Paused → human arbitration           |

---

## Three Scenarios

| Scenario | Label                | Verdict       | Consequence                   |
|----------|----------------------|---------------|-------------------------------|
| A        | TIMELY SHIPMENT      | TRUE          | 73,950 PEN → exporter         |
| B        | LATE SHIPMENT        | FALSE         | 73,950 PEN → importer refund  |
| C        | INSUFFICIENT EVIDENCE| UNDETERMINED  | MANUAL_REVIEW, paused         |

---

## Key Design Principle

**The court asks one question. The contract maps the answer to an outcome.**

If the court is asked to decide the whole trade, the flow becomes unbounded and loses legibility. The narrow question keeps both the AI evaluation and the on-chain logic understandable.

---

## Out of Scope (this version)

- Cargo quality disputes
- Multi-issue court cases  
- Open-ended "who was right overall?" prompts
- Tokenized payment rails
- Full PDF parsing in GenVM
- Unlimited evidence submission
- Legal interpretation of Incoterms

---

## Files

| File | Purpose |
|------|---------|
| `base-sepolia/src/TradeFxSettlement.sol` | Main settlement contract (extended with shipment dispute) |
| `contracts/ShipmentDeadlineCourt.py` | GenLayer AI court contract |
| `scripts/prepare-shipment-evidence.mjs` | Build evidence pack from manifest |
| `scripts/fx-settlement-relayer.mjs` | Extended with `verdict` command |
| `evidence/qc-coop-2026-0003/` | Scenario A: TIMELY |
| `evidence/qc-coop-2026-0004/` | Scenario B: LATE |
| `evidence/qc-coop-2026-0005/` | Scenario C: INSUFFICIENT EVIDENCE |

---

## Evidence Schema

See `docs/evidence-manifest-schema.md` for the full schema.
