# { "Depends": "py-genlayer:test" }
"""ShipmentDeadlineCourt — Single-question shipment deadline dispute for GenLayer.

Evaluates ONE fact:
    "Did the shipment cross the border before [deadline]?"

Returns: TRUE | FALSE | UNDETERMINED

Verdict mapping (enforced by TradeFxSettlement on Base Sepolia):
    TRUE        → settlement proceeds
    FALSE       → settlement cancelled, importer refunded
    UNDETERMINED → settlement paused, MANUAL_REVIEW

Evidence: image URLs (IPFS gateway or HTTP). Court fetches and renders
both images for AI visual analysis.

Lifecycle:
    CREATED → EVIDENCE_SUBMITTED → EVALUATED
"""

from genlayer import *
import json


class ShipmentDeadlineCourt(gl.Contract):
    """Single-question shipment deadline court."""

    # --- Parties ---
    trade_contract: str  # Base Sepolia trade contract address (string, cross-chain ref)
    exporter: Address
    importer: Address

    # --- Case parameters ---
    court_question: str   # e.g. "Did the shipment cross the Bolivian border on or before 2026-04-05?"
    deadline_iso: str     # ISO 8601 deadline string, used in prompt
    contract_clause: str  # verbatim clause from the trade agreement
    case_id: str          # e.g. "qc-coop-2026-0003"

    # --- Evidence ---
    exporter_evidence_url: str   # IPFS gateway URL or HTTPS URL
    importer_evidence_url: str

    # --- State ---
    status: str  # created | evidence_submitted | evaluated
    verdict: str  # TRUE | FALSE | UNDETERMINED | ""
    reasoning: str

    def __init__(
        self,
        importer: Address,
        trade_contract: str,
        court_question: str,
        deadline_iso: str,
        contract_clause: str,
        case_id: str,
    ):
        self.exporter = gl.message.sender_address

        if isinstance(importer, str):
            importer = Address(importer)
        self.importer = importer

        self.trade_contract = trade_contract
        self.court_question = court_question
        self.deadline_iso = deadline_iso
        self.contract_clause = contract_clause
        self.case_id = case_id

        self.exporter_evidence_url = ""
        self.importer_evidence_url = ""

        self.status = "created"
        self.verdict = ""
        self.reasoning = ""

    # ─── Evidence submission ──────────────────────────────────────────────────

    @gl.public.write
    def submit_exporter_evidence(self, image_url: str) -> None:
        """Exporter submits evidence image URL (IPFS gateway or HTTPS)."""
        if gl.message.sender_address != self.exporter:
            raise Exception("ShipmentCourt: not exporter")
        if self.status not in ("created", "evidence_submitted"):
            raise Exception("ShipmentCourt: cannot submit evidence in current status")
        self.exporter_evidence_url = image_url
        self._check_evidence_complete()

    @gl.public.write
    def submit_importer_evidence(self, image_url: str) -> None:
        """Importer submits evidence image URL (IPFS gateway or HTTPS)."""
        if gl.message.sender_address != self.importer:
            raise Exception("ShipmentCourt: not importer")
        if self.status not in ("created", "evidence_submitted"):
            raise Exception("ShipmentCourt: cannot submit evidence in current status")
        self.importer_evidence_url = image_url
        self._check_evidence_complete()

    def _check_evidence_complete(self) -> None:
        if self.exporter_evidence_url and self.importer_evidence_url:
            self.status = "evidence_submitted"

    # ─── AI evaluation ────────────────────────────────────────────────────────

    @gl.public.write
    def evaluate(self) -> None:
        """Trigger AI evaluation. Callable by either party after both evidence URLs are submitted.
        Fetches both images and evaluates the single court question.
        """
        if self.status != "evidence_submitted":
            raise Exception("ShipmentCourt: evidence not yet complete")
        if gl.message.sender_address not in (self.exporter, self.importer):
            raise Exception("ShipmentCourt: not a party")

        result = gl.get_webpage(self.exporter_evidence_url, mode="image")
        exporter_doc = result if result else "[image not retrievable]"

        result2 = gl.get_webpage(self.importer_evidence_url, mode="image")
        importer_doc = result2 if result2 else "[image not retrievable]"

        prompt = f"""You are evaluating a shipment dispute for a cross-border trade.

Case ID: {self.case_id}
Contract clause: {self.contract_clause}
Deadline: {self.deadline_iso}
Court question: {self.court_question}

You have two documents:

EXPORTER EVIDENCE:
{exporter_doc}

IMPORTER EVIDENCE:
{importer_doc}

Your task:
1. Examine both documents carefully.
2. Determine whether the shipment crossed the border before or on the deadline.
3. Return exactly one of: TRUE, FALSE, or UNDETERMINED.

Rules:
- TRUE: evidence clearly shows the shipment crossed on or before {self.deadline_iso}
- FALSE: evidence clearly shows the shipment crossed AFTER {self.deadline_iso}
- UNDETERMINED: evidence is conflicting, illegible, or insufficient to determine the crossing date

Output format (JSON only, no other text):
{{
  "verdict": "TRUE" | "FALSE" | "UNDETERMINED",
  "reasoning": "one sentence explanation"
}}
"""

        result_json = gl.eq_principle_strict_eq(
            lambda: self._call_ai(prompt)
        )

        try:
            parsed = json.loads(result_json)
            v = parsed.get("verdict", "UNDETERMINED").strip().upper()
            if v not in ("TRUE", "FALSE", "UNDETERMINED"):
                v = "UNDETERMINED"
            self.verdict = v
            self.reasoning = parsed.get("reasoning", "")
        except Exception:
            self.verdict = "UNDETERMINED"
            self.reasoning = "Failed to parse AI response."

        self.status = "evaluated"

    def _call_ai(self, prompt: str) -> str:
        result = gl.exec_prompt(prompt)
        return result

    # ─── Views ────────────────────────────────────────────────────────────────

    @gl.public.view
    def get_verdict(self) -> dict:
        return {
            "case_id": self.case_id,
            "status": self.status,
            "verdict": self.verdict,
            "reasoning": self.reasoning,
            "court_question": self.court_question,
        }

    @gl.public.view
    def get_status(self) -> str:
        return self.status
