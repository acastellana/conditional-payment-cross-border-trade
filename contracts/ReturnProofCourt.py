# v0.1.0
# { "Depends": "py-genlayer:latest" }
"""ReturnProofCourt — Return proof evaluation court for GenLayer.

Evaluates whether an importer has proven that a VERY_LATE shipment was
returned to the exporter or formally rejected at the Peruvian border.

Returns verdict to Base Sepolia via the InternetCourt bridge:
    RETURN_PROVEN     (1) — clear evidence of return or formal rejection; importer refunded
    RETURN_NOT_PROVEN (2) — evidence missing, insufficient, or doesn't match; highest penalty
    UNDETERMINED      (3) — evidence present but contradictory; escalate to human arbitrator

Evidence: exactly two composite court sheet images (IPFS CIDs).
    return_sheet_a: Bolivian ANB customs re-entry record (truck returning from Peru)
    return_sheet_b: SUNAT Peru formal rejection notice for the cargo

Guideline is frozen and versioned.
Current version: return-proof-v1

On construction:
    1. Fetches both return proof court sheet images from IPFS
    2. AI jury evaluates the statement against the images
    3. Encodes verdict and calls BridgeSender.send_message() → bridge → Base Sepolia
"""

from genlayer import *
import json

genvm_eth = gl.evm

# ─── Frozen guideline versions ────────────────────────────────────────────────

GUIDELINES = {
    "return-proof-v1": (
        "Evaluate the statement using only the two submitted court sheet images. "
        "Confirm that the shipment reference and truck plate match across both documents. "
        "Determine whether the evidence shows that the shipment was either "
        "(a) physically returned from Peru back to Bolivia (customs re-entry record), "
        "OR (b) formally rejected at the Peruvian border by SUNAT or the receiving warehouse. "
        "The importer bears the burden of proof: clear, readable, matching documentation is required. "
        "Check that: (1) The shipment reference on both documents refers to the same cargo. "
        "(2) The truck plate or vehicle identifier matches or is consistent across both documents. "
        "(3) The documents show an actual return crossing or formal rejection, not just a delay. "
        "If the evidence shows return or rejection clearly: RETURN_PROVEN. "
        "If the evidence is missing, illegible, or does not match the shipment reference: RETURN_NOT_PROVEN. "
        "If documents are present but contradictory (e.g. matching references but conflicting outcomes): UNDETERMINED."
    )
}

IPFS_GATEWAY = "https://ipfs.io/ipfs/"

# Verdict uint8 codes — must match TradeFxSettlement.sol resolveReturnProof()
VERDICT_RETURN_PROVEN     = 1
VERDICT_RETURN_NOT_PROVEN = 2
VERDICT_UNDETERMINED      = 3


class ReturnProofCourt(gl.Contract):
    """Return proof evaluation court.
    Evaluates on construction; sends result via bridge to Base Sepolia."""

    case_id:                str
    settlement_contract:    str   # TradeFxSettlement address on Base Sepolia
    guideline_version:      str
    return_sheet_a_cid:     str   # IPFS CID — Bolivian re-entry record
    return_sheet_b_cid:     str   # IPFS CID — SUNAT rejection notice
    bridge_sender:          str   # BridgeSender.py address on GenLayer
    target_chain_eid:       u256  # LayerZero EID for Base Sepolia (40245)
    verdict:                str
    verdict_reason:         str
    return_proof_case_id:   str   # resolved case identifier

    def __init__(
        self,
        case_id: str,
        settlement_contract: str,
        statement: str,
        guideline_version: str,
        return_sheet_a_cid: str,
        return_sheet_b_cid: str,
        bridge_sender: str,
        target_chain_eid: int,
        target_contract: str,  # InternetCourtFactory on Base Sepolia
    ):
        if guideline_version not in GUIDELINES:
            raise Exception(f"ReturnProofCourt: unknown guideline '{guideline_version}'")

        self.case_id              = case_id
        self.settlement_contract  = settlement_contract
        self.guideline_version    = guideline_version
        self.return_sheet_a_cid   = return_sheet_a_cid
        self.return_sheet_b_cid   = return_sheet_b_cid
        self.bridge_sender        = bridge_sender
        self.target_chain_eid     = u256(target_chain_eid)
        self.return_proof_case_id = case_id

        guideline = GUIDELINES[guideline_version]

        # Copy to locals for non-det block
        cid_a = return_sheet_a_cid.lstrip("ipfs://")
        cid_b = return_sheet_b_cid.lstrip("ipfs://")
        url_a = IPFS_GATEWAY + cid_a
        url_b = IPFS_GATEWAY + cid_b
        stmt  = statement

        def nondet():
            # Fetch return proof court sheet images from IPFS
            images = []
            fetch_notes = []

            resp_a = gl.nondet.web.get(url_a)
            if resp_a and resp_a.status == 200 and resp_a.body:
                images.append(resp_a.body)
                fetch_notes.append("Return Sheet A (Bolivian ANB re-entry): fetched OK")
            else:
                fetch_notes.append("Return Sheet A (Bolivian ANB re-entry): NOT RETRIEVABLE")

            resp_b = gl.nondet.web.get(url_b)
            if resp_b and resp_b.status == 200 and resp_b.body:
                images.append(resp_b.body)
                fetch_notes.append("Return Sheet B (SUNAT rejection notice): fetched OK")
            else:
                fetch_notes.append("Return Sheet B (SUNAT rejection notice): NOT RETRIEVABLE")

            fetch_summary = "\n".join(fetch_notes)

            prompt = f"""You are an AI juror in the InternetCourt dispute resolution system.
You are evaluating a return proof claim for a VERY_LATE cross-border shipment.

STATEMENT TO EVALUATE:
{stmt}

GUIDELINE:
{guideline}

DOCUMENT FETCH STATUS:
{fetch_summary}

You have been provided the return proof court sheet images showing:
- Return Sheet A: Bolivian ANB (Aduana Nacional de Bolivia) customs re-entry record
  showing the shipment vehicle returning from Peru back into Bolivia
- Return Sheet B: SUNAT (Peru Customs) formal rejection notice for the cargo

Examine the images carefully. Look for:
1. The shipment reference number / cargo ID in both documents
2. The truck plate / vehicle identifier in both documents
3. Whether Sheet A shows an actual re-entry crossing into Bolivia from Peru
4. Whether Sheet B shows an official SUNAT rejection or non-conformance notice
5. Whether the references and truck plate match across both documents

Your task is to determine:
- RETURN_PROVEN: Both documents are present, readable, and consistently show
  that the shipment was either returned to Bolivia or formally rejected by SUNAT.
  The shipment reference and truck plate must match across documents.
- RETURN_NOT_PROVEN: One or both documents are missing, illegible, or the
  shipment reference / truck plate does not match between documents, or the
  documents do not actually show a return or rejection.
- UNDETERMINED: Both documents appear present and reference the same shipment,
  but their content is contradictory (e.g., one shows return, other shows delivery).

Output ONLY valid JSON, no other text:
{{
  "verdict": "RETURN_PROVEN" | "RETURN_NOT_PROVEN" | "UNDETERMINED",
  "reason": "One concise sentence explaining the verdict, referencing the specific documents, dates, and references found."
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
            task="Evaluate return proof documentation for a cross-border shipment dispute",
            criteria=(
                "The verdict must be exactly one of: RETURN_PROVEN, RETURN_NOT_PROVEN, UNDETERMINED. "
                "RETURN_PROVEN requires both documents to be present, readable, and consistently prove "
                "return or formal rejection with matching shipment references and truck plate. "
                "RETURN_NOT_PROVEN applies when evidence is missing, illegible, or references don't match. "
                "UNDETERMINED is for contradictory but present documentation. "
                "The reason must reference specific document details found in the images."
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

        valid_verdicts = ("RETURN_PROVEN", "RETURN_NOT_PROVEN", "UNDETERMINED")
        if v not in valid_verdicts:
            v = "UNDETERMINED"
            r = f"Unexpected verdict value, defaulting to UNDETERMINED. Original reason: {r}"

        self.verdict       = v
        self.verdict_reason = r

        # Map verdict to uint8
        verdict_map = {
            "RETURN_PROVEN":     VERDICT_RETURN_PROVEN,
            "RETURN_NOT_PROVEN": VERDICT_RETURN_NOT_PROVEN,
            "UNDETERMINED":      VERDICT_UNDETERMINED,
        }
        verdict_uint8 = verdict_map.get(v, VERDICT_UNDETERMINED)

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
            target_contract,   # ← targets InternetCourtFactory, which dispatches to settlement
            message_bytes
        )

    # ─── Views ───────────────────────────────────────────────────────────────

    @gl.public.view
    def get_verdict(self) -> dict:
        return {
            "case_id":              self.case_id,
            "return_proof_case_id": self.return_proof_case_id,
            "verdict":              self.verdict,
            "verdict_reason":       self.verdict_reason,
            "guideline":            self.guideline_version,
        }

    @gl.public.view
    def get_status(self) -> str:
        return self.verdict
