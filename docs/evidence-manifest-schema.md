# Evidence Manifest Schema

Each shipment dispute case has a manifest at:
```
evidence/<case-id>/manifest.json
```

---

## Schema

```json
{
  "case_id": "string",            // e.g. "qc-coop-2026-0003"
  "scenario": "string",           // "A", "B", or "C"
  "label": "string",              // "TIMELY SHIPMENT" | "LATE SHIPMENT" | "INSUFFICIENT EVIDENCE"
  "verdict": "string",            // expected: "TRUE" | "FALSE" | "UNDETERMINED"
  "consequence": "string",        // "settlement_proceeds" | "settlement_cancelled" | "manual_review"
  "trade_ref": "string",          // invoice reference, e.g. "INV-BOL-2026-0003"
  "contract_clause": "string",    // verbatim clause from the trade agreement
  "court_question": "string",     // exact question submitted to ShipmentDeadlineCourt
  "exporter_evidence": {
    "label": "Exporter Evidence",
    "description": "string",      // human-readable summary of the document
    "file": "string",             // filename in evidence/images/
    "ipfs_cid": "string"         // IPFS CID (stub during development)
  },
  "importer_evidence": {
    "label": "Importer Evidence",
    "description": "string",
    "file": "string",
    "ipfs_cid": "string"
  },
  "settlement_consequence": "string"  // human-readable outcome description
}
```

---

## Required Fields

| Field | Type | Notes |
|-------|------|-------|
| `case_id` | string | Unique identifier. Format: `<org>-<year>-<seq>` |
| `scenario` | string | A, B, or C |
| `label` | string | TIMELY SHIPMENT / LATE SHIPMENT / INSUFFICIENT EVIDENCE |
| `verdict` | string | Expected verdict for this fixture |
| `consequence` | string | Machine-readable outcome |
| `trade_ref` | string | Links to the invoice |
| `contract_clause` | string | Exact clause text used as input to the court |
| `court_question` | string | Exact question submitted to ShipmentDeadlineCourt |
| `exporter_evidence` | object | See evidence object schema below |
| `importer_evidence` | object | See evidence object schema below |

## Evidence Object Schema

| Field | Type | Notes |
|-------|------|-------|
| `label` | string | UI label: "Exporter Evidence" or "Importer Evidence" |
| `description` | string | Human-readable summary of what the document shows |
| `file` | string | Filename in `evidence/images/` directory |
| `ipfs_cid` | string | IPFS CID after pinning (stub value during development) |

---

## Example — qc-coop-2026-0003 (Scenario A: TIMELY SHIPMENT)

```json
{
  "case_id": "qc-coop-2026-0003",
  "scenario": "A",
  "label": "TIMELY SHIPMENT",
  "verdict": "TRUE",
  "consequence": "settlement_proceeds",
  "trade_ref": "INV-BOL-2026-0003",
  "contract_clause": "Shipment must cross Bolivian border before 2026-04-05T00:00:00Z",
  "court_question": "Did the shipment cross the Bolivian border on or before 2026-04-05?",
  "exporter_evidence": {
    "label": "Exporter Evidence",
    "description": "Bill of lading signed by COSCO at Santa Cruz customs — 2026-04-03T14:22:00Z",
    "file": "03_COSCO_Bill_of_Lading.jpg",
    "ipfs_cid": "QmTIMELY3aBillOfLadingCOSCO2026Apr03"
  },
  "importer_evidence": {
    "label": "Importer Evidence",
    "description": "Importer's internal logistics note citing 'expected late April' — pre-dispute misunderstanding, not proof of late shipment",
    "file": "07_Purchase_Contract_Excerpt.jpg",
    "ipfs_cid": "QmCONTRACT7PurchaseExcerpt2026"
  },
  "settlement_consequence": "Settlement proceeds as agreed. 73,950 PEN transferred to exporter."
}
```

---

## Consequence Values

| consequence | On-chain action |
|-------------|----------------|
| `settlement_proceeds` | `resolveShipmentVerdict(1, ref)` — unpauses, settlement continues |
| `settlement_cancelled` | `resolveShipmentVerdict(2, ref)` — cancelAndRefund to importer |
| `manual_review` | `resolveShipmentVerdict(3, ref)` — stays paused, MANUAL_REVIEW state |

---

## Usage with prepare-shipment-evidence.mjs

```bash
# Print evidence pack to stdout
node scripts/prepare-shipment-evidence.mjs --case qc-coop-2026-0003

# Write to file
node scripts/prepare-shipment-evidence.mjs --case qc-coop-2026-0004 --out /tmp/pack-B.json

# Pin to IPFS (requires PINATA_JWT env var)
node scripts/prepare-shipment-evidence.mjs --case qc-coop-2026-0005 --pin
```
