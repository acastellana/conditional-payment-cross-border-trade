# v0.1.0
# { "Depends": "py-genlayer:latest" }
"""ShipmentDeadlineCourt — Single-question shipment deadline court for GenLayer.

Evaluates ONE factual statement:
    "Shipment under Contract [REF] crossed Bolivian export customs at
     Desaguadero on or before [DEADLINE]."

Returns verdict to Base Sepolia via the InternetCourt bridge:
    TIMELY      (uint8=1) → shipmentStatus = TIMELY   → settlement proceeds
    LATE        (uint8=2) → shipmentStatus = LATE     → settlement cancelled, importer refunded
    UNDETERMINED (uint8=0) → shipmentStatus = UNDETERMINED → MANUAL_REVIEW

Evidence: exactly two composite court sheet images (IPFS CIDs).
    court_sheet_a: contract summary snippet + exporter evidence (ANB customs exit)
    court_sheet_b: contract summary snippet + importer evidence (SUNAT border gate)

Guideline is frozen and versioned.
Current version: shipment-deadline-v1

On construction:
    1. Fetches both court sheet images from IPFS
    2. AI jury evaluates the statement against the images
    3. Encodes verdict and calls BridgeSender.send_message() → bridge → Base Sepolia
"""

from genlayer import *
import json

genvm_eth = gl.evm

# ─── Frozen guideline versions ────────────────────────────────────────────────

GUIDELINES = {
    "shipment-deadline-v1": (
        "Evaluate the statement using only the two submitted court sheet images. "
        "Confirm that the shipment reference and truck plate match across both documents. "
        "Determine whether the evidence shows that the shipment crossed Bolivian export "
        "customs at Desaguadero on or before the stated deadline. "
        "Evidence hierarchy: official customs exit records showing the vehicle physically "
        "crossing the border are the most authoritative evidence of crossing time. "
        "Secondary gate or administrative records (e.g. arrival scans, issue dates, "
        "pre-clearance stamps) are weaker and should only be preferred if the primary "
        "customs exit record is missing, unreadable, or clearly inapplicable. "
        "Apply this hierarchy when evaluating conflicting timestamps. "
        "Return TIMELY if the most authoritative customs-crossing record shows the shipment "
        "crossed on or before the deadline. A weaker secondary record showing a later time "
        "does not override a clear primary customs exit record. "
        "Return LATE if the most authoritative customs-crossing record shows the shipment "
        "crossed after the deadline, or if the exporter has no primary customs exit record "
        "and the available evidence unambiguously shows a late crossing. "
        "Return UNDETERMINED if: the images are unreadable; shipment references or truck "
        "plates do not match between documents; both primary records conflict and neither "
        "is clearly more authoritative; or evidence is insufficient to determine the crossing time. "
        "The importer bears the burden of proof: if the importer's evidence is missing or "
        "cannot be verified, and the exporter's customs exit record is clear and timely, "
        "return TIMELY."
    )
}

IPFS_GATEWAY = "https://ipfs.io/ipfs/"

# Verdict uint8 codes — must match TradeFxSettlement.sol resolveShipmentVerdict()
# 1=TIMELY, 2=LATE, 3=UNDETERMINED
VERDICT_TIMELY       = 1
VERDICT_LATE         = 2
VERDICT_UNDETERMINED = 3


class ShipmentDeadlineCourt(gl.Contract):
    """Single-question shipment deadline court.
    Evaluates on construction; sends result via bridge to Base Sepolia."""

    case_id:               str
    settlement_contract:   str   # TradeFxSettlement address on Base Sepolia
    guideline_version:     str
    court_sheet_a_cid:     str
    court_sheet_b_cid:     str
    bridge_sender:         str   # BridgeSender.py address on GenLayer
    target_chain_eid:      u256  # LayerZero EID for Base Sepolia (40245)
    verdict:               str
    verdict_reason:        str

    def __init__(
        self,
        case_id: str,
        settlement_contract: str,
        statement: str,
        guideline_version: str,
        court_sheet_a_cid: str,
        court_sheet_b_cid: str,
        bridge_sender: str,
        target_chain_eid: int,
    ):
        if guideline_version not in GUIDELINES:
            raise Exception(f"ShipmentCourt: unknown guideline '{guideline_version}'")

        self.case_id             = case_id
        self.settlement_contract = settlement_contract
        self.guideline_version   = guideline_version
        self.court_sheet_a_cid   = court_sheet_a_cid
        self.court_sheet_b_cid   = court_sheet_b_cid
        self.bridge_sender       = bridge_sender
        self.target_chain_eid    = u256(target_chain_eid)

        guideline = GUIDELINES[guideline_version]

        # Copy to locals for non-det block
        cid_a = court_sheet_a_cid.lstrip("ipfs://")
        cid_b = court_sheet_b_cid.lstrip("ipfs://")
        url_a = IPFS_GATEWAY + cid_a
        url_b = IPFS_GATEWAY + cid_b
        stmt  = statement

        def nondet():
            # Fetch court sheet images from IPFS
            images = []
            fetch_notes = []

            resp_a = gl.nondet.web.get(url_a)
            if resp_a and resp_a.status == 200 and resp_a.body:
                images.append(resp_a.body)
                fetch_notes.append("Court sheet A (exporter/ANB): fetched OK")
            else:
                fetch_notes.append("Court sheet A (exporter/ANB): NOT RETRIEVABLE")

            resp_b = gl.nondet.web.get(url_b)
            if resp_b and resp_b.status == 200 and resp_b.body:
                images.append(resp_b.body)
                fetch_notes.append("Court sheet B (importer/SUNAT): fetched OK")
            else:
                fetch_notes.append("Court sheet B (importer/SUNAT): NOT RETRIEVABLE")

            fetch_summary = "\n".join(fetch_notes)

            prompt = f"""You are an AI juror in the InternetCourt dispute resolution system.
You are evaluating a single disputed shipment timing fact.

STATEMENT TO EVALUATE:
{stmt}

GUIDELINE:
{guideline}

DOCUMENT FETCH STATUS:
{fetch_summary}

You have been provided the court sheet images showing:
- Court Sheet A: contract summary + exporter evidence (ANB customs exit record from Bolivia)
- Court Sheet B: contract summary + importer evidence (SUNAT border gate event record from Peru)

Examine the images carefully. Look for:
1. The stated deadline in the contract summary panel
2. The timestamp on the ANB customs exit record (exporter document)
3. The timestamp on the SUNAT border gate record (importer document)
4. Whether the truck plate and container references match between documents

Based ONLY on the evidence in the images, return exactly one of:
- TIMELY: both documents show the crossing occurred before the deadline
- LATE: both documents show the crossing occurred after the deadline
- UNDETERMINED: timestamps conflict, are unreadable, references don't match, or evidence is insufficient

Output ONLY valid JSON, no other text:
{{
  "verdict": "TIMELY" | "LATE" | "UNDETERMINED",
  "reason": "One concise sentence explaining the verdict referencing the specific timestamps or issues found."
}}"""

            if images:
                result = gl.nondet.exec_prompt(prompt, images=images)
            else:
                result = gl.nondet.exec_prompt(prompt)

            if isinstance(result, str):
                return result.strip()
            return str(result).strip()

        result_str = gl.eq_principle.prompt_non_comparative(
            nondet,
            task="Evaluate a shipment customs crossing dispute using court sheet document images",
            criteria=(
                "The verdict must be exactly one of TIMELY, LATE, or UNDETERMINED. "
                "The reason must reference specific timestamps or document issues found in the images. "
                "TIMELY requires both documents to show crossing before the deadline. "
                "LATE requires both documents to show crossing after the deadline. "
                "UNDETERMINED covers all ambiguous cases."
            ),
        )

        # Parse result
        try:
            if isinstance(result_str, str):
                clean = result_str.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(clean)
            elif isinstance(result_str, dict):
                parsed = result_str
            else:
                parsed = json.loads(str(result_str))

            v = parsed.get("verdict", "UNDETERMINED").strip().upper()
            r = parsed.get("reason", "").strip()
        except Exception as e:
            v = "UNDETERMINED"
            r = f"Failed to parse evaluation response: {str(e)}"

        if v not in ("TIMELY", "LATE", "UNDETERMINED"):
            v = "UNDETERMINED"
            r = f"Unexpected verdict value, defaulting to UNDETERMINED. Original: {r}"

        self.verdict       = v
        self.verdict_reason = r

        # Map verdict to uint8 — matches TradeFxSettlement.sol: 1=TIMELY, 2=LATE, 3=UNDETERMINED
        verdict_uint8 = {"TIMELY": 1, "LATE": 2, "UNDETERMINED": 3}.get(v, 3)

        # ABI-encode the resolution payload:
        # Inner: (address settlementContract, uint8 verdict, string reason)
        resolution_encoder = genvm_eth.MethodEncoder("", [Address, u8, str], bool)
        resolution_data = resolution_encoder.encode_call(
            [Address(settlement_contract), verdict_uint8, r]
        )[4:]  # strip selector

        # Outer: (address agreementAddress, bytes resolutionData)
        wrapper_encoder = genvm_eth.MethodEncoder("", [Address, bytes], bool)
        message_bytes = wrapper_encoder.encode_call(
            [Address(settlement_contract), resolution_data]
        )[4:]  # strip selector

        # Send via bridge → zkSync Sepolia → LayerZero → Base Sepolia
        bridge = gl.get_contract_at(Address(bridge_sender))
        bridge.emit().send_message(
            int(self.target_chain_eid),
            settlement_contract,
            message_bytes
        )

    # ─── Views ───────────────────────────────────────────────────────────────

    @gl.public.view
    def get_verdict(self) -> dict:
        return {
            "case_id":       self.case_id,
            "verdict":       self.verdict,
            "verdict_reason": self.verdict_reason,
            "guideline":     self.guideline_version,
        }

    @gl.public.view
    def get_status(self) -> str:
        return self.verdict
