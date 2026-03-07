# { "Depends": "py-genlayer:test" }
"""ShipmentDeadlineCourt — Single-question shipment deadline court for GenLayer.

Evaluates ONE factual statement:
    "Shipment under Contract [REF] crossed Bolivian export customs at
     Desaguadero on or before [DEADLINE]."

Returns: TRUE | FALSE | UNDETERMINED

Verdict mapping (enforced by TradeFxSettlement on Base Sepolia):
    TRUE        → shipmentStatus = TIMELY   → settlement proceeds
    FALSE       → shipmentStatus = LATE     → settlement cancelled, importer refunded
    UNDETERMINED → shipmentStatus = UNDETERMINED → MANUAL_REVIEW

Evidence: exactly two composite court sheet images (IPFS CIDs).
    court_sheet_a: contract summary snippet + exporter evidence
    court_sheet_b: contract summary snippet + importer evidence

Guideline is frozen and versioned. Do not allow ad hoc prompts per case.
Current version: shipment-deadline-v1

Lifecycle:
    CREATED → EVIDENCE_SUBMITTED → EVALUATED
"""

from genlayer import *
import json

# ─── Frozen guideline versions ────────────────────────────────────────────────

GUIDELINES = {
    "shipment-deadline-v1": (
        "Evaluate the statement using only the two submitted court sheet images. "
        "Confirm that the shipment reference matches the contract reference. "
        "Determine whether the evidence shows that the shipment crossed Bolivian export "
        "customs at Desaguadero on or before the stated deadline. "
        "Prefer explicit timestamps tied to customs-crossing events over generic issue dates. "
        "If the evidence clearly shows a qualifying timestamp on or before the deadline, return TRUE. "
        "If the evidence clearly shows the earliest reliable customs-crossing timestamp is after "
        "the deadline, return FALSE. "
        "If the images are unreadable, references do not match, or the evidence conflicts "
        "without a clearly more reliable timestamp, return UNDETERMINED."
    )
}


class ShipmentDeadlineCourt(gl.Contract):
    """Single-question shipment deadline court. Accepts exactly two court sheet images."""

    # --- Identity ---
    case_id: str
    trade_contract: str          # Base Sepolia trade contract address (cross-chain ref)
    manifest_cid: str            # IPFS CID of the full evidence manifest

    # --- Parties ---
    exporter: Address
    importer: Address

    # --- Case definition ---
    statement: str               # Exact factual statement to evaluate
    guideline_version: str       # Must be a key in GUIDELINES

    # --- Evidence (two court sheet CIDs) ---
    court_sheet_a_cid: str       # contract snippet + exporter evidence
    court_sheet_b_cid: str       # contract snippet + importer evidence

    # --- Status ---
    status: str                  # created | evaluated

    # --- Result ---
    verdict: str                 # TRUE | FALSE | UNDETERMINED | ""
    verdict_reason_summary: str
    verdict_timestamp: int       # Unix timestamp of evaluation

    def __init__(
        self,
        importer: Address,
        case_id: str,
        trade_contract: str,
        manifest_cid: str,
        statement: str,
        guideline_version: str,
        court_sheet_a_cid: str,
        court_sheet_b_cid: str,
    ):
        self.exporter = gl.message.sender_address

        if isinstance(importer, str):
            importer = Address(importer)
        self.importer = importer

        if guideline_version not in GUIDELINES:
            raise Exception(f"ShipmentCourt: unknown guideline version '{guideline_version}'")

        self.case_id           = case_id
        self.trade_contract    = trade_contract
        self.manifest_cid      = manifest_cid
        self.statement         = statement
        self.guideline_version = guideline_version
        self.court_sheet_a_cid = court_sheet_a_cid
        self.court_sheet_b_cid = court_sheet_b_cid

        self.status                = "created"
        self.verdict               = ""
        self.verdict_reason_summary = ""
        self.verdict_timestamp     = 0

    # ─── Evaluation ──────────────────────────────────────────────────────────

    @gl.public.write
    def evaluate(self) -> None:
        """Trigger AI evaluation. Callable by either party.
        Fetches the two court sheet images and evaluates the statement.
        Uses the frozen guideline for this case's guideline_version.
        """
        if self.status == "evaluated":
            raise Exception("ShipmentCourt: already evaluated")
        if gl.message.sender_address not in (self.exporter, self.importer):
            raise Exception("ShipmentCourt: not a party")

        guideline = GUIDELINES[self.guideline_version]

        # Fetch court sheets from IPFS gateway
        gateway = "https://ipfs.io/ipfs/"
        sheet_a_url = gateway + self.court_sheet_a_cid.lstrip("ipfs://")
        sheet_b_url = gateway + self.court_sheet_b_cid.lstrip("ipfs://")

        sheet_a = gl.get_webpage(sheet_a_url, mode="image")
        sheet_b = gl.get_webpage(sheet_b_url, mode="image")

        if not sheet_a:
            sheet_a = "[Court sheet A not retrievable]"
        if not sheet_b:
            sheet_b = "[Court sheet B not retrievable]"

        prompt = f"""You are an AI juror evaluating a single disputed shipment fact.

STATEMENT TO EVALUATE:
{self.statement}

GUIDELINE:
{guideline}

COURT SHEET A (contract summary + exporter evidence):
{sheet_a}

COURT SHEET B (contract summary + importer evidence):
{sheet_b}

You must return exactly one of: TRUE, FALSE, or UNDETERMINED.
- TRUE: the statement is supported by the evidence
- FALSE: the evidence clearly contradicts the statement
- UNDETERMINED: evidence is conflicting, unreadable, or insufficient

Output ONLY valid JSON:
{{
  "verdict": "TRUE" | "FALSE" | "UNDETERMINED",
  "reason": "One sentence explaining the verdict based on the documents."
}}
"""

        result_json = gl.eq_principle_strict_eq(
            lambda: gl.exec_prompt(prompt)
        )

        try:
            parsed = json.loads(result_json)
            v = parsed.get("verdict", "UNDETERMINED").strip().upper()
            if v not in ("TRUE", "FALSE", "UNDETERMINED"):
                v = "UNDETERMINED"
            self.verdict               = v
            self.verdict_reason_summary = parsed.get("reason", "")
        except Exception:
            self.verdict               = "UNDETERMINED"
            self.verdict_reason_summary = "Failed to parse AI evaluation response."

        self.verdict_timestamp = int(gl.message.timestamp)
        self.status = "evaluated"

    # ─── Views ───────────────────────────────────────────────────────────────

    @gl.public.view
    def get_verdict(self) -> dict:
        return {
            "case_id":               self.case_id,
            "status":                self.status,
            "verdict":               self.verdict,
            "verdict_reason_summary": self.verdict_reason_summary,
            "verdict_timestamp":     self.verdict_timestamp,
            "statement":             self.statement,
            "guideline_version":     self.guideline_version,
        }

    @gl.public.view
    def get_status(self) -> str:
        return self.status
