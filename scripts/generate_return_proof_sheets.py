#!/usr/bin/env python3
"""
Generate return proof court sheet PNGs for ReturnProofCourt (Phase 2).

Two sheets for case qc-coop-2026-0009-R (RETURN_PROVEN scenario):
  Sheet A: Bolivian ANB customs re-entry record showing truck returning from Peru
           Shipment ref: qc-coop-2026-0009-R, truck: BVZ-8821-Z, crossing: April 22, 2026
  Sheet B: SUNAT Peru formal rejection notice for cargo qc-coop-2026-0009
           Rejected April 21, 2026, reason: quality non-conformance

Usage:
  python3 scripts/generate_return_proof_sheets.py
"""

import os
import json
import requests
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

REPO     = Path(__file__).parent.parent
EVIDENCE = REPO / "evidence"

# ── Fonts ─────────────────────────────────────────────────────────────────────
FONT_DIR   = "/usr/share/fonts/truetype/dejavu"

def font(size, bold=False, mono=False):
    if mono:
        return ImageFont.truetype(f"{FONT_DIR}/DejaVuSansMono.ttf", size)
    if bold:
        return ImageFont.truetype(f"{FONT_DIR}/DejaVuSans-Bold.ttf", size)
    return ImageFont.truetype(f"{FONT_DIR}/DejaVuSans.ttf", size)

# ── Palette ───────────────────────────────────────────────────────────────────
BG          = (252, 251, 249)
HEADER_BG   = (18,  18,  18)
HEADER_FG   = (255, 255, 255)
LEFT_BG     = (245, 243, 240)
RIGHT_BG    = (255, 255, 255)
DIVIDER     = (200, 196, 190)
FOOTER_BG   = (30,  30,  30)
FOOTER_FG   = (180, 180, 180)
LABEL_GREY  = (75,  75,  75)
ACCENT_IC   = (99,  60, 180)

# Document org colours
ANB_GREEN   = (1,   94,  67)
ANB_YELLOW  = (252, 196,  0)
SUNAT_RED   = (185,  28,  28)
PROVEN_G    = (21,  128,  61)
REJECT_R    = (185,  28,  28)

# ── Layout ────────────────────────────────────────────────────────────────────
W, H       = 1200, 900
HEADER_H   = 110
FOOTER_H   = 36
PANEL_Y    = HEADER_H
PANEL_H    = H - HEADER_H - FOOTER_H
LEFT_W     = 390
RIGHT_X    = LEFT_W + 1
RIGHT_W    = W - RIGHT_X
MARGIN     = 20

def new_image():
    img = Image.new("RGB", (W, H), BG)
    d   = ImageDraw.Draw(img)
    return img, d

def fill_rect(d, x, y, w, h, color):
    d.rectangle([x, y, x+w, y+h], fill=color)

def hline(d, x, y, w, color=DIVIDER, th=1):
    d.rectangle([x, y, x+w, y+th], fill=color)

def vline(d, x, y, h, color=DIVIDER, th=1):
    d.rectangle([x, y, x+th, y+h], fill=color)

def text(d, x, y, s, fnt, color=(30,30,30)):
    d.text((x, y), s, font=fnt, fill=color)

def wrapped_text(d, x, y, s, fnt, color, max_w, line_h=18):
    words = s.split()
    line  = ""
    cy    = y
    for w in words:
        test = (line + " " + w).strip()
        bb   = d.textbbox((0,0), test, font=fnt)
        if bb[2] - bb[0] > max_w and line:
            d.text((x, cy), line, font=fnt, fill=color)
            cy  += line_h
            line = w
        else:
            line = test
    if line:
        d.text((x, cy), line, font=fnt, fill=color)
    return cy + line_h

# ── HEADER ────────────────────────────────────────────────────────────────────

def draw_header(d, case_id, statement, doc_type):
    fill_rect(d, 0, 0, W, HEADER_H, HEADER_BG)
    fill_rect(d, 0, 0, 6, HEADER_H, ACCENT_IC)

    text(d, 18, 14, "INTERNET", font(9, bold=True), ACCENT_IC)
    text(d, 18, 26, "COURT", font(9, bold=True), (255,255,255))

    text(d, 18, 44, f"Case {case_id}", font(11, bold=True), (210,210,210))
    text(d, 18, 62, "RETURN PROOF EVALUATION — PHASE 2", font(9), (140,140,140))

    stmt_short = statement if len(statement) < 110 else statement[:107] + "…"
    text(d, 18, 82, stmt_short, font(9), (190,190,190))

    f14 = font(12, bold=True)
    bb  = d.textbbox((0,0), doc_type, font=f14)
    tw  = bb[2]-bb[0]
    text(d, W - tw - 20, 20, doc_type, f14, (255, 220, 80))
    text(d, W - 210, 46, "Guideline: return-proof-v1", font(9), (120,120,120))

# ── LEFT PANEL: case summary ──────────────────────────────────────────────────

def draw_left(d, case_id, original_case_id, contract_no, exporter, importer, goods, return_reason):
    x0, pw = MARGIN, LEFT_W - 2*MARGIN
    cy     = PANEL_Y + MARGIN
    fill_rect(d, 0, PANEL_Y, LEFT_W, PANEL_H, LEFT_BG)
    vline(d, LEFT_W, PANEL_Y, PANEL_H, DIVIDER, 1)

    text(d, x0, cy, "RETURN PROOF SUMMARY", font(9, bold=True), LABEL_GREY)
    cy += 16
    hline(d, x0, cy, pw, DIVIDER)
    cy += 8

    def kv(label, value, vc=(40,40,40)):
        nonlocal cy
        text(d, x0, cy, label, font(9, bold=True), (110,110,110))
        cy += 13
        wrapped_text(d, x0, cy, value, font(10), vc, pw, 15)
        cy += 18

    kv("Return Proof Case No.", case_id)
    kv("Original Shipment Case", original_case_id)
    kv("Contract No.", contract_no)
    kv("Exporter (Returner)", exporter, ANB_GREEN)
    kv("Importer (Claimant)", importer, SUNAT_RED)
    kv("Goods", goods)

    cy += 4
    hline(d, x0, cy, pw, DIVIDER)
    cy += 10

    text(d, x0, cy, "RETURN CLAIM BASIS", font(9, bold=True), LABEL_GREY)
    cy += 16
    wrapped_text(d, x0, cy, return_reason, font(9), (60,60,60), pw, 14)
    cy += 48

    hline(d, x0, cy, pw, DIVIDER)
    cy += 10
    text(d, x0, cy, "EVALUATION STANDARD", font(9, bold=True), LABEL_GREY)
    cy += 14
    wrapped_text(d, x0, cy,
        "Importer bears burden of proof. Both return crossing and rejection notice required.",
        font(9), (80,80,80), pw, 14)
    cy += 36

    hline(d, x0, cy, pw, DIVIDER)
    cy += 10
    text(d, x0, cy, "CASE ID", font(9, bold=True), LABEL_GREY)
    cy += 14
    text(d, x0, cy, case_id, font(10, mono=True), (60,60,60))

# ── RIGHT PANEL: ANB customs re-entry record (Sheet A) ───────────────────────

def draw_anb_reentry(d, due_no, shipment_ref, timestamp_str, exporter,
                     truck_plate, checkpoint_officer, origin_country):
    x0 = RIGHT_X + MARGIN
    pw = RIGHT_W - 2*MARGIN

    fill_rect(d, RIGHT_X, PANEL_Y, RIGHT_W, PANEL_H, RIGHT_BG)
    fill_rect(d, RIGHT_X, PANEL_Y, RIGHT_W, 52, ANB_GREEN)
    fill_rect(d, RIGHT_X, PANEL_Y + 52, RIGHT_W, 5, ANB_YELLOW)

    text(d, x0, PANEL_Y + 8,  "ADUANA NACIONAL DE BOLIVIA", font(14, bold=True), (255,255,255))
    text(d, x0, PANEL_Y + 28, "REGISTRO DE REINGRESO — IMPORTACIÓN TEMPORAL (RETORNO)", font(9), (200,240,210))

    text(d, W - 220, PANEL_Y + 10, "IMPORTER EVIDENCE", font(9, bold=True), ANB_YELLOW)
    text(d, W - 220, PANEL_Y + 27, "ANB Customs Re-entry Record", font(9), (200,240,210))

    cy = PANEL_Y + 68

    # DUR reference (Documento Único de Retorno)
    fill_rect(d, x0, cy, pw, 28, (240, 248, 242))
    d.rectangle([x0, cy, x0+pw, cy+28], outline=ANB_GREEN, width=1)
    text(d, x0+8, cy+7, "DUR No.:", font(9, bold=True), ANB_GREEN)
    text(d, x0+80, cy+7, due_no, font(11, bold=True, mono=True), (20,20,20))
    text(d, x0+pw-140, cy+7, "RETORNO OFICIAL", font(9, bold=True), ANB_GREEN)
    cy += 36

    # Timestamp — re-entry crossing date
    fill_rect(d, x0, cy, pw, 44, (248, 255, 250))
    d.rectangle([x0, cy, x0+pw, cy+44], outline=PROVEN_G, width=2)
    text(d, x0+8, cy+6, "FECHA Y HORA DE REINGRESO A BOLIVIA:", font(9, bold=True), (80,80,80))
    text(d, x0+8, cy+22, timestamp_str, font(18, bold=True, mono=True), PROVEN_G)
    text(d, x0+pw-140, cy+22, "22 APR 2026", font(12, bold=True), (100,100,100))
    cy += 52

    def field(label, value, vc=(30,30,30)):
        nonlocal cy
        text(d, x0, cy, label.upper(), font(8, bold=True), (120,120,120))
        cy += 12
        text(d, x0, cy, value, font(10), vc)
        cy += 18

    field("Declarante / Returnee", exporter)
    field("Punto de Reingreso", "Aduana Desaguadero — Código 1140")
    field("País de Procedencia", origin_country)
    field("Funcionario ANB", checkpoint_officer)
    field("Vehículo / Truck Plate", truck_plate)
    field("Ref. Envío Original", shipment_ref)

    cy += 4
    hline(d, x0, cy, pw, DIVIDER)
    cy += 8

    # Status stamp
    fill_rect(d, x0, cy, pw, 36, (240, 255, 244))
    d.rectangle([x0, cy, x0+pw, cy+36], outline=PROVEN_G, width=2)
    d.rounded_rectangle([x0+pw-160, cy+6, x0+pw-8, cy+30], radius=4, fill=PROVEN_G)
    text(d, x0+pw-154, cy+12, "REINGRESO CONFIRMADO", font(9, bold=True), (255,255,255))
    text(d, x0+8, cy+6, "Tipo:", font(9, bold=True), (80,80,80))
    text(d, x0+8, cy+20, "Retorno de mercancía rechazada en destino / temporalmente importada", font(8), (60,60,60))
    cy += 44

    # Signature block
    cy += 6
    text(d, x0, cy, "Firma del funcionario / Officer signature:", font(9), (120,120,120))
    cy += 14
    hline(d, x0, cy, 180, (80,80,80))
    cy += 6
    text(d, x0, cy, checkpoint_officer, font(9, bold=True), (40,40,40))
    # Stamp
    d.ellipse([x0+310, cy-18, x0+380, cy+20], outline=ANB_GREEN, width=2)
    d.ellipse([x0+316, cy-12, x0+374, cy+14], outline=ANB_GREEN, width=1)
    text(d, x0+322, cy-5, "ANB", font(9, bold=True), ANB_GREEN)
    text(d, x0+317, cy+4, "DUR-1140", font(7), ANB_GREEN)

# ── RIGHT PANEL: SUNAT formal rejection notice (Sheet B) ─────────────────────

def draw_sunat_rejection(d, notice_id, cargo_ref, rejection_date, rejection_reason,
                         importer, truck_plate, officer, warehouse):
    x0 = RIGHT_X + MARGIN
    pw = RIGHT_W - 2*MARGIN

    fill_rect(d, RIGHT_X, PANEL_Y, RIGHT_W, PANEL_H, RIGHT_BG)
    fill_rect(d, RIGHT_X, PANEL_Y, RIGHT_W, 52, SUNAT_RED)
    fill_rect(d, RIGHT_X, PANEL_Y + 52, RIGHT_W, 4, (220, 160, 0))

    text(d, x0, PANEL_Y + 6,  "SUNAT — SUPERINTENDENCIA NACIONAL DE ADUANAS Y DE", font(11, bold=True), (255,255,255))
    text(d, x0, PANEL_Y + 22, "ADMINISTRACIÓN TRIBUTARIA — CONTROL FRONTERIZO", font(10, bold=True), (255,255,255))
    text(d, x0, PANEL_Y + 38, "ACTA DE RECHAZO / FORMAL REJECTION NOTICE", font(9), (255,200,200))

    text(d, W - 240, PANEL_Y + 10, "IMPORTER EVIDENCE", font(9, bold=True), (255,220,80))
    text(d, W - 240, PANEL_Y + 27, "SUNAT Formal Rejection Notice", font(9), (255,200,200))

    cy = PANEL_Y + 68

    # Notice reference
    fill_rect(d, x0, cy, pw, 28, (255, 245, 245))
    d.rectangle([x0, cy, x0+pw, cy+28], outline=SUNAT_RED, width=1)
    text(d, x0+8, cy+7, "Acta No.:", font(9, bold=True), SUNAT_RED)
    text(d, x0+90, cy+7, notice_id, font(11, bold=True, mono=True), (20,20,20))
    text(d, x0+pw-140, cy+7, "DOCUMENTO OFICIAL", font(9, bold=True), SUNAT_RED)
    cy += 36

    # Rejection date — key fact
    fill_rect(d, x0, cy, pw, 44, (255, 245, 245))
    d.rectangle([x0, cy, x0+pw, cy+44], outline=REJECT_R, width=2)
    text(d, x0+8, cy+6, "FECHA DE RECHAZO FORMAL:", font(9, bold=True), (80,80,80))
    text(d, x0+8, cy+22, rejection_date, font(18, bold=True, mono=True), REJECT_R)
    text(d, x0+pw-140, cy+22, "21 APR 2026", font(12, bold=True), (100,100,100))
    cy += 52

    # Rejection reason box
    fill_rect(d, x0, cy, pw, 44, (255, 240, 240))
    d.rectangle([x0, cy, x0+pw, cy+44], outline=REJECT_R, width=2)
    text(d, x0+8, cy+6, "MOTIVO DE RECHAZO / REJECTION REASON:", font(9, bold=True), (80,80,80))
    text(d, x0+8, cy+22, rejection_reason, font(12, bold=True), REJECT_R)
    text(d, x0+8, cy+35, "Art. 87° LGAA — Mercancía no conforme a normas de calidad.", font(8), (100,100,100))
    cy += 52

    def field(label, value, vc=(30,30,30)):
        nonlocal cy
        text(d, x0, cy, label.upper(), font(8, bold=True), (120,120,120))
        cy += 12
        text(d, x0, cy, value, font(10), vc)
        cy += 18

    field("Importador / Consignee",  importer)
    field("Ref. Carga / Cargo Ref.", cargo_ref)
    field("Vehículo / Truck Plate",  truck_plate)
    field("Almacén de Control",      warehouse)
    field("Funcionario SUNAT",       officer)

    cy += 4
    hline(d, x0, cy, pw, DIVIDER)
    cy += 8

    # Legal notice
    fill_rect(d, x0, cy, pw, 44, (255, 245, 245))
    d.rectangle([x0, cy, x0+pw, cy+44], outline=SUNAT_RED, width=1)
    text(d, x0+8, cy+6, "La mercancía queda bajo custodia SUNAT para retorno inmediato al país de origen.", font(9), (80,80,80))
    text(d, x0+8, cy+20, "Plazo de retorno: 15 días hábiles desde fecha de rechazo.", font(9), (80,80,80))
    text(d, x0+8, cy+34, "Verificable en: sunat.gob.pe/consulta-actas-rechazo", font(8), (120,120,120))
    cy += 52

    # Signature block
    cy += 2
    text(d, x0, cy, "Firma del funcionario / Officer signature:", font(9), (120,120,120))
    cy += 14
    hline(d, x0, cy, 180, (80,80,80))
    cy += 6
    text(d, x0, cy, officer, font(9, bold=True), (40,40,40))
    # Stamp
    d.ellipse([x0+220, cy-18, x0+295, cy+20], outline=SUNAT_RED, width=2)
    d.ellipse([x0+226, cy-12, x0+289, cy+14], outline=SUNAT_RED, width=1)
    text(d, x0+233, cy-5, "SUNAT", font(8, bold=True), SUNAT_RED)
    text(d, x0+230, cy+4, "RECHAZO", font(7), SUNAT_RED)

# ── FOOTER ────────────────────────────────────────────────────────────────────

def draw_footer(d, doc_type, filename):
    fy  = H - FOOTER_H
    fill_rect(d, 0, fy, W, FOOTER_H, FOOTER_BG)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    text(d, 12, fy + 10, f"Generated: {now} | InternetCourt Return Proof Exhibit | {doc_type}", font(8), FOOTER_FG)
    text(d, W - 200, fy + 10, filename, font(8, mono=True), FOOTER_FG)

# ── MAIN ──────────────────────────────────────────────────────────────────────

CASE_ID          = "qc-coop-2026-0009-R"
ORIGINAL_CASE_ID = "qc-coop-2026-0009"
CONTRACT_NO      = "ISPA-2025-BOL-PER-0047"
EXPORTER         = "Minera Andina SRL — Potosí, Bolivia"
IMPORTER         = "Electroquímica del Perú S.A. — Lima, Peru"
GOODS            = "50 MT battery-grade lithium carbonate (Li₂CO₃), ISO 6206"

STATEMENT = (
    "Importer claims that shipment qc-coop-2026-0009 under Contract ISPA-2025-BOL-PER-0047 "
    "was formally rejected by SUNAT at the Peruvian border on April 21, 2026 due to quality "
    "non-conformance, and that the shipment vehicle BVZ-8821-Z returned to Bolivia on April 22, 2026."
)

RETURN_REASON = (
    "Shipment was rejected by SUNAT Desaguadero PCF on April 21, 2026 for quality non-conformance "
    "(ISO 6206 certificate mismatch). Vehicle BVZ-8821-Z returned to Bolivia on April 22, 2026."
)


def generate():
    out_dir = EVIDENCE / CASE_ID
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Sheet A: ANB customs re-entry record ─────────────────────────────────
    img_a, d_a = new_image()
    draw_header(d_a, CASE_ID, STATEMENT, "RETURN SHEET A — Re-entry Record")
    draw_left(d_a, CASE_ID, ORIGINAL_CASE_ID, CONTRACT_NO, EXPORTER, IMPORTER, GOODS, RETURN_REASON)
    draw_anb_reentry(
        d_a,
        due_no             = "DUR-2026-DES-0012204",
        shipment_ref       = "qc-coop-2026-0009-R",
        timestamp_str      = "2026-04-22  09:47:00  -04:00",
        exporter           = "Minera Andina SRL — Tax ID: 1029384756",
        truck_plate        = "Placa: BVZ-8821-Z | Tractocamión DAF XF (retorno)",
        checkpoint_officer = "Lic. Ramiro Chávez Apaza — Funcionario ANB 4420",
        origin_country     = "República del Perú (vía Desaguadero)",
    )
    draw_footer(d_a, "Return Sheet A — Bolivian ANB Re-entry Record", "return_sheet_a.png")
    path_a = out_dir / "return_sheet_a.png"
    img_a.save(str(path_a), "PNG", dpi=(150, 150))
    print(f"  ✅ {path_a}")

    # ── Sheet B: SUNAT formal rejection notice ────────────────────────────────
    img_b, d_b = new_image()
    draw_header(d_b, CASE_ID, STATEMENT, "RETURN SHEET B — SUNAT Rejection Notice")
    draw_left(d_b, CASE_ID, ORIGINAL_CASE_ID, CONTRACT_NO, EXPORTER, IMPORTER, GOODS, RETURN_REASON)
    draw_sunat_rejection(
        d_b,
        notice_id        = "SUNAT-PCF-DES-2026-04-21-0079",
        cargo_ref        = "qc-coop-2026-0009 / DUE-2026-DES-0050011",
        rejection_date   = "2026-04-21  14:33:00  -05:00",
        rejection_reason = "CALIDAD NO CONFORME — ISO 6206 / QUALITY NON-CONFORMANCE",
        importer         = "Electroquímica del Perú S.A. — RUC: 20512345678",
        truck_plate      = "Placa: BVZ-8821-Z | Tractocamión DAF XF",
        officer          = "Insp. Rosa Mamani Condori — SUNAT PCF-001",
        warehouse        = "Almacén Fiscal Desaguadero — AFD-PUN-003",
    )
    draw_footer(d_b, "Return Sheet B — SUNAT Formal Rejection Notice", "return_sheet_b.png")
    path_b = out_dir / "return_sheet_b.png"
    img_b.save(str(path_b), "PNG", dpi=(150, 150))
    print(f"  ✅ {path_b}")

    return str(path_a), str(path_b)


def upload_to_pinata(path):
    jwt_path = Path.home() / ".internetcourt" / ".pinata_jwt"
    jwt      = jwt_path.read_text().strip()

    filename = Path(path).name
    with open(path, "rb") as f:
        resp = requests.post(
            "https://api.pinata.cloud/pinning/pinFileToIPFS",
            headers={"Authorization": f"Bearer {jwt}"},
            files={"file": (filename, f, "image/png")},
            data={"pinataMetadata": json.dumps({"name": filename})},
            timeout=60,
        )
    resp.raise_for_status()
    ipfs_hash = resp.json()["IpfsHash"]
    print(f"  📌 Pinned {filename} → ipfs://{ipfs_hash}")
    return f"ipfs://{ipfs_hash}"


if __name__ == "__main__":
    print(f"Generating return proof court sheets for case {CASE_ID}...")
    path_a, path_b = generate()

    print("\nUploading to Pinata...")
    cid_a = upload_to_pinata(path_a)
    cid_b = upload_to_pinata(path_b)

    result = {
        "case_id":        CASE_ID,
        "original_case":  ORIGINAL_CASE_ID,
        "return_sheet_a": cid_a,
        "return_sheet_b": cid_b,
        "statement":      STATEMENT,
        "guideline":      "return-proof-v1",
        "generated_at":   datetime.now(timezone.utc).isoformat(),
    }

    out_path = Path(__file__).parent.parent / "artifacts" / "return_proof_cids.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2))
    print(f"\n✅ Saved CIDs to {out_path}")
    print(json.dumps(result, indent=2))
