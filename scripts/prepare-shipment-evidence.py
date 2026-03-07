#!/usr/bin/env python3
"""
prepare-shipment-evidence.py

Reads evidence/<case-id>/ source files and produces:
  - Normalized PNGs from any PDFs
  - Cropped regions highlighting key fields
  - court_sheet_a.png  (contract summary + exporter evidence)
  - court_sheet_b.png  (contract summary + importer evidence)
  - manifest.json      (spec-compliant, with all CIDs and extracted fields)

Usage:
  python3 scripts/prepare-shipment-evidence.py --case qc-coop-2026-0003
  python3 scripts/prepare-shipment-evidence.py --case qc-coop-2026-0003 --pin

Requirements:
  pip install pillow pdf2image
  apt install poppler-utils  (for pdftoppm)
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("ERROR: Install Pillow: pip install pillow")

try:
    from pdf2image import convert_from_path
except ImportError:
    sys.exit("ERROR: Install pdf2image: pip install pdf2image")

# ─── Config ──────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent
EVIDENCE_DIR = REPO_ROOT / "evidence"
IPFS_GATEWAY = "https://ipfs.io/ipfs/"

# Frozen guideline — must match ShipmentDeadlineCourt.py
GUIDELINE_VERSION = "shipment-deadline-v1"

# Court sheet dimensions
SHEET_W = 1200
SHEET_H = 900
LABEL_BG = (30, 30, 30)
LABEL_FG = (255, 255, 255)
HEADER_BG = (20, 20, 20)
DIVIDER = (80, 80, 80)
GREEN = (21, 128, 61)
AMBER = (180, 83, 9)

# ─── CLI ─────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="Prepare shipment evidence for ShipmentDeadlineCourt")
parser.add_argument("--case", required=True, help="Case ID (directory name under evidence/)")
parser.add_argument("--pin", action="store_true", help="Pin to IPFS via Pinata (requires PINATA_JWT)")
args = parser.parse_args()

case_dir = EVIDENCE_DIR / args.case
if not case_dir.exists():
    sys.exit(f"ERROR: Case directory not found: {case_dir}")

manifest_path = case_dir / "manifest.json"
if not manifest_path.exists():
    sys.exit(f"ERROR: manifest.json not found in {case_dir}")

manifest = json.loads(manifest_path.read_text())
case_id = manifest["case_id"]
statement = manifest["statement"]

print(f"[prepare] Case: {case_id}")
print(f"[prepare] Scenario: {manifest['scenario']} — {manifest['label']}")
print(f"[prepare] Statement: {statement[:80]}...")

# ─── Helpers ─────────────────────────────────────────────────────────────────

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def pdf_to_png(pdf_path: Path, out_prefix: str, dpi: int = 150) -> list[Path]:
    """Convert PDF pages to PNG. Returns list of output paths."""
    pages = convert_from_path(str(pdf_path), dpi=dpi)
    paths = []
    for i, page in enumerate(pages):
        out = case_dir / f"{out_prefix}_page_{i+1}.png"
        page.save(str(out), "PNG")
        print(f"[prepare]   PDF page {i+1} → {out.name}")
        paths.append(out)
    return paths


def open_or_convert(filename: str, prefix: str) -> list[Path]:
    """Open source file (PDF/PNG/JPG) and return list of PNG paths."""
    candidates = [
        case_dir / filename,
        EVIDENCE_DIR / "images" / filename,
        EVIDENCE_DIR / "images_compact" / filename,
    ]
    src = next((p for p in candidates if p.exists()), None)
    if src is None:
        print(f"[prepare]   WARNING: source file not found: {filename}")
        return []
    if src.suffix.lower() == ".pdf":
        return pdf_to_png(src, prefix)
    else:
        # Copy as-is to case dir under normalized name
        out = case_dir / f"{prefix}_page_1.png"
        img = Image.open(src).convert("RGB")
        img.save(str(out), "PNG")
        return [out]


def crop_top(img_path: Path, out_name: str, height_fraction: float = 0.45) -> Path:
    """Crop top N% of image as the 'relevant region'."""
    img = Image.open(img_path).convert("RGB")
    w, h = img.size
    crop = img.crop((0, 0, w, int(h * height_fraction)))
    out = case_dir / out_name
    crop.save(str(out), "PNG")
    print(f"[prepare]   Cropped → {out.name}")
    return out


def try_load_font(size: int):
    """Load a font with graceful fallback."""
    for name in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]:
        if Path(name).exists():
            try:
                return ImageFont.truetype(name, size)
            except Exception:
                pass
    return ImageFont.load_default()


def build_court_sheet(
    sheet_path: Path,
    title: str,
    title_color: tuple,
    contract_crop: Path | None,
    evidence_crop: Path | None,
    labels: dict,
) -> Path:
    """Compose a labeled court sheet from contract crop + evidence crop."""
    sheet = Image.new("RGB", (SHEET_W, SHEET_H), (245, 245, 243))
    draw = ImageDraw.Draw(sheet)

    font_sm = try_load_font(14)
    font_md = try_load_font(18)
    font_lg = try_load_font(22)
    font_xl = try_load_font(26)

    # Header bar
    draw.rectangle([(0, 0), (SHEET_W, 56)], fill=HEADER_BG)
    draw.text((16, 15), f"InternetCourt — Shipment Deadline Evaluation", font=font_lg, fill=(200, 200, 200))
    draw.text((SHEET_W - 240, 20), f"Case: {case_id}", font=font_sm, fill=(100, 100, 100))

    # Title bar
    draw.rectangle([(0, 56), (SHEET_W, 96)], fill=title_color)
    draw.text((16, 68), title, font=font_md, fill=LABEL_FG)

    # Statement strip
    y = 104
    draw.rectangle([(0, y), (SHEET_W, y + 38)], fill=(240, 240, 238))
    draw.line([(0, y), (SHEET_W, y)], fill=DIVIDER, width=1)
    stmt_short = statement if len(statement) <= 110 else statement[:107] + "…"
    draw.text((16, y + 10), f"Statement: {stmt_short}", font=font_sm, fill=(80, 80, 80))
    y += 38

    # Deadline pill
    draw.rectangle([(0, y), (SHEET_W, y + 30)], fill=(255, 255, 255))
    draw.line([(0, y), (SHEET_W, y)], fill=DIVIDER, width=1)
    deadline = labels.get("deadline", "2026-04-05T23:59:59-04:00")
    location = labels.get("location", "Desaguadero, Bolivian export customs")
    reference = labels.get("reference", case_id)
    draw.text((16, y + 8), f"Deadline: {deadline}  |  Location: {location}  |  Ref: {reference}", font=font_sm, fill=(60, 60, 60))
    y += 30

    # Split: left = contract snippet, right = evidence
    col_split = 460
    left_x, right_x = 0, col_split + 8
    left_w, right_w = col_split, SHEET_W - col_split - 8
    content_top = y + 8
    content_h = SHEET_H - content_top - 8

    # Left panel label
    draw.rectangle([(left_x, content_top), (left_x + left_w, content_top + 24)], fill=(230, 230, 230))
    draw.text((left_x + 8, content_top + 5), "CONTRACT SUMMARY", font=font_sm, fill=(80, 80, 80))

    # Contract image
    if contract_crop and contract_crop.exists():
        try:
            cimg = Image.open(contract_crop).convert("RGB")
            cimg.thumbnail((left_w - 4, content_h - 28))
            sheet.paste(cimg, (left_x + 2, content_top + 26))
        except Exception as e:
            draw.text((left_x + 8, content_top + 40), f"[contract image error: {e}]", font=font_sm, fill=(180, 0, 0))
    else:
        draw.rectangle([(left_x + 2, content_top + 26), (left_x + left_w - 2, content_top + content_h - 2)], fill=(220, 220, 220))
        draw.text((left_x + 16, content_top + 60), "CONTRACT SNIPPET\n(source not found)", font=font_md, fill=(140, 140, 140))

    # Divider
    draw.line([(col_split + 4, content_top), (col_split + 4, SHEET_H - 8)], fill=DIVIDER, width=2)

    # Right panel label
    evidence_label = labels.get("evidence_label", "EVIDENCE")
    doc_type = labels.get("doc_type", "")
    claimed_ts = labels.get("claimed_timestamp", "")
    draw.rectangle([(right_x, content_top), (right_x + right_w, content_top + 24)], fill=(*title_color,))
    draw.text((right_x + 8, content_top + 5), evidence_label, font=font_sm, fill=LABEL_FG)

    if doc_type:
        draw.text((right_x + 200, content_top + 5), f"Doc type: {doc_type}", font=font_sm, fill=(200, 200, 200))

    # Claimed timestamp strip
    if claimed_ts:
        draw.rectangle([(right_x, content_top + 24), (right_x + right_w, content_top + 44)], fill=(250, 250, 248))
        ts_color = GREEN if labels.get("timely") else AMBER
        draw.text((right_x + 8, content_top + 29), f"Reported timestamp: {claimed_ts}", font=font_sm, fill=ts_color)
        ev_top = content_top + 44
    else:
        ev_top = content_top + 24

    # Evidence image
    if evidence_crop and evidence_crop.exists():
        try:
            eimg = Image.open(evidence_crop).convert("RGB")
            eimg.thumbnail((right_w - 4, SHEET_H - ev_top - 8))
            sheet.paste(eimg, (right_x + 2, ev_top + 2))
        except Exception as e:
            draw.text((right_x + 8, ev_top + 20), f"[evidence image error: {e}]", font=font_sm, fill=(180, 0, 0))
    else:
        draw.rectangle([(right_x + 2, ev_top + 2), (right_x + right_w - 2, SHEET_H - 10)], fill=(220, 220, 220))
        draw.text((right_x + 16, ev_top + 40), "EVIDENCE IMAGE\n(source not found)", font=font_md, fill=(140, 140, 140))

    # Footer
    draw.rectangle([(0, SHEET_H - 20), (SHEET_W, SHEET_H)], fill=HEADER_BG)
    draw.text((16, SHEET_H - 16), f"Guideline: {GUIDELINE_VERSION}  |  Generated: {datetime.utcnow().isoformat()}Z  |  {sheet_path.name}", font=font_sm, fill=(80, 80, 80))

    sheet.save(str(sheet_path), "PNG")
    print(f"[prepare] Court sheet → {sheet_path.name}")
    return sheet_path


def stub_pin(file_path: Path, name: str) -> str:
    """Stub IPFS pin — returns placeholder CID. TODO: implement real Pinata upload."""
    # TODO: implement actual Pinata pinning
    # import httpx, base64
    # jwt = os.environ["PINATA_JWT"]
    # with open(file_path, "rb") as f:
    #     resp = httpx.post("https://api.pinata.cloud/pinning/pinFileToIPFS",
    #         headers={"Authorization": f"Bearer {jwt}"},
    #         files={"file": (name, f)})
    #     return resp.json()["IpfsHash"]
    print(f"[prepare]   [STUB] Would pin {file_path.name} to IPFS")
    return f"Qm{hashlib.sha256(name.encode()).hexdigest()[:44]}"


# ─── Main pipeline ────────────────────────────────────────────────────────────

print("\n[prepare] === Step 1: Normalize source files ===")

# Source filenames — use existing JPGs from images/ if no case-specific files
# For a full implementation, drop contract_summary.pdf, exporter_record.pdf/jpg, importer_record.pdf/jpg
# into the case directory.

CONTRACT_SOURCES = ["contract_summary.pdf", "contract_summary.png", "contract_summary.jpg"]
EXPORTER_SOURCES = ["exporter_record.pdf", "exporter_record.png", "exporter_record.jpg"]
IMPORTER_SOURCES = ["importer_record.pdf", "importer_record.png", "importer_record.jpg"]

# Fallback to existing repo images for demo
DEMO_FALLBACKS = {
    "contract": "07_Purchase_Contract_Excerpt.jpg",
    "exporter": "03_COSCO_Bill_of_Lading.jpg",
    "importer": "03_COSCO_Bill_of_Lading.jpg",
}

def find_source(candidates, fallback_key):
    for name in candidates:
        p = case_dir / name
        if p.exists():
            return p, name
    fb = DEMO_FALLBACKS[fallback_key]
    for base in [EVIDENCE_DIR / "images", EVIDENCE_DIR / "images_compact"]:
        p = base / fb
        if p.exists():
            return p, fb
    return None, None

contract_src, contract_name = find_source(CONTRACT_SOURCES, "contract")
exporter_src, exporter_name = find_source(EXPORTER_SOURCES, "exporter")
importer_src, importer_name = find_source(IMPORTER_SOURCES, "importer")

print(f"  contract: {contract_name or 'NOT FOUND'}")
print(f"  exporter: {exporter_name or 'NOT FOUND'}")
print(f"  importer: {importer_name or 'NOT FOUND'}")

print("\n[prepare] === Step 2: Convert PDFs to PNG ===")

def normalize_to_png(src: Path | None, prefix: str) -> Path | None:
    if src is None:
        return None
    if src.suffix.lower() == ".pdf":
        pages = pdf_to_png(src, prefix)
        return pages[0] if pages else None
    else:
        out = case_dir / f"{prefix}_page_1.png"
        img = Image.open(src).convert("RGB")
        img.save(str(out), "PNG")
        return out

contract_png = normalize_to_png(contract_src, "contract")
exporter_png = normalize_to_png(exporter_src, "exporter")
importer_png = normalize_to_png(importer_src, "importer")

print("\n[prepare] === Step 3: Crop relevant regions ===")

contract_crop = crop_top(contract_png, "contract_crop.png", 0.50) if contract_png else None
exporter_crop = crop_top(exporter_png, "exporter_crop.png", 0.50) if exporter_png else None
importer_crop = crop_top(importer_png, "importer_crop.png", 0.50) if importer_png else None

print("\n[prepare] === Step 4: Build court sheets ===")

extracted = manifest.get("extracted_fields", {})

sheet_a = case_dir / "court_sheet_a.png"
build_court_sheet(
    sheet_path=sheet_a,
    title="COURT SHEET A — Contract Summary + Exporter Evidence",
    title_color=GREEN,
    contract_crop=contract_crop,
    evidence_crop=exporter_crop,
    labels={
        "deadline": manifest["contract"]["deadline_iso"],
        "location": manifest["contract"]["location"],
        "reference": manifest["contract"]["shipment_reference"],
        "evidence_label": "EXPORTER EVIDENCE",
        "doc_type": extracted.get("exporter_doc_type", ""),
        "claimed_timestamp": extracted.get("exporter_claimed_timestamp") or "",
        "timely": True,
    }
)

sheet_b = case_dir / "court_sheet_b.png"
build_court_sheet(
    sheet_path=sheet_b,
    title="COURT SHEET B — Contract Summary + Importer Evidence",
    title_color=AMBER,
    contract_crop=contract_crop,
    evidence_crop=importer_crop,
    labels={
        "deadline": manifest["contract"]["deadline_iso"],
        "location": manifest["contract"]["location"],
        "reference": manifest["contract"]["shipment_reference"],
        "evidence_label": "IMPORTER EVIDENCE",
        "doc_type": extracted.get("importer_doc_type", ""),
        "claimed_timestamp": extracted.get("importer_claimed_timestamp") or "",
        "timely": False,
    }
)

print("\n[prepare] === Step 5: Hash all artifacts ===")

def sha256_or_none(p: Path | None) -> str:
    if p and p.exists():
        return sha256_file(p)
    return "NOT_FOUND"

hashes = {
    "contract_summary": sha256_or_none(contract_src),
    "exporter_record":  sha256_or_none(exporter_src),
    "importer_record":  sha256_or_none(importer_src),
    "court_sheet_a":    sha256_file(sheet_a),
    "court_sheet_b":    sha256_file(sheet_b),
}

print("\n[prepare] === Step 6: Pin to IPFS ===")

if args.pin:
    contract_cid = stub_pin(contract_src, f"{case_id}-contract") if contract_src else "NOT_FOUND"
    exporter_cid = stub_pin(exporter_src, f"{case_id}-exporter") if exporter_src else "NOT_FOUND"
    importer_cid = stub_pin(importer_src, f"{case_id}-importer") if importer_src else "NOT_FOUND"
    sheet_a_cid  = stub_pin(sheet_a, f"{case_id}-court-sheet-a")
    sheet_b_cid  = stub_pin(sheet_b, f"{case_id}-court-sheet-b")
else:
    # Use existing manifest stubs
    contract_cid = manifest.get("audit_originals", {}).get("contract_summary", {}).get("cid", "ipfs://STUB")
    exporter_cid = manifest.get("audit_originals", {}).get("exporter_record", {}).get("cid", "ipfs://STUB")
    importer_cid = manifest.get("audit_originals", {}).get("importer_record", {}).get("cid", "ipfs://STUB")
    sheet_a_cid  = manifest.get("court_inputs", {}).get("court_sheet_a", {}).get("cid", "ipfs://STUB")
    sheet_b_cid  = manifest.get("court_inputs", {}).get("court_sheet_b", {}).get("cid", "ipfs://STUB")
    print("  Skipping IPFS pin (use --pin to upload)")

print("\n[prepare] === Step 7: Write manifest.json ===")

out_manifest = {
    "case_id": case_id,
    "statement": statement,
    "guideline_version": GUIDELINE_VERSION,
    "contract": manifest["contract"],
    "audit_originals": {
        "contract_summary": {"cid": contract_cid, "sha256": hashes["contract_summary"]},
        "exporter_record":  {"cid": exporter_cid, "sha256": hashes["exporter_record"]},
        "importer_record":  {"cid": importer_cid, "sha256": hashes["importer_record"]},
    },
    "court_inputs": {
        "court_sheet_a": {"cid": sheet_a_cid, "sha256": hashes["court_sheet_a"]},
        "court_sheet_b": {"cid": sheet_b_cid, "sha256": hashes["court_sheet_b"]},
    },
    "extracted_fields": manifest.get("extracted_fields", {}),
    "expected_verdict": manifest.get("expected_verdict"),
    "expected_consequence": manifest.get("expected_consequence"),
    "prepared_at": datetime.utcnow().isoformat() + "Z",
}

manifest_path.write_text(json.dumps(out_manifest, indent=2))
print(f"  Manifest written: {manifest_path}")

print("\n[prepare] === Done ===")
print(f"  court_sheet_a.png  {hashes['court_sheet_a'][:16]}…")
print(f"  court_sheet_b.png  {hashes['court_sheet_b'][:16]}…")
print(f"  manifest.json updated")
print(f"\nTo create the court case:")
print(f"  node scripts/fx-settlement-relayer.mjs create-shipment-case <TRADE_ADDR> --case {case_id}")
