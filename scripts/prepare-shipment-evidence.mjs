#!/usr/bin/env node
/**
 * prepare-shipment-evidence.mjs
 *
 * Reads evidence/qc-coop-2026-000X/manifest.json and outputs a
 * ready-to-use evidence pack for ShipmentDeadlineCourt.
 *
 * Usage:
 *   node scripts/prepare-shipment-evidence.mjs --case qc-coop-2026-0003
 *   node scripts/prepare-shipment-evidence.mjs --case qc-coop-2026-0003 --pin
 *
 * Flags:
 *   --case  <case-id>   Required. Directory name under evidence/
 *   --pin               Pin images to IPFS via Pinata (requires PINATA_JWT env var)
 *                       Stub: prints TODO message, does not actually pin.
 *   --out   <file>      Write output JSON to file (default: stdout)
 */

import { readFileSync, existsSync, writeFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");

// ─── Args ────────────────────────────────────────────────────────────────────

const args = process.argv.slice(2);
const caseIdIdx = args.indexOf("--case");
const pinFlag = args.includes("--pin");
const outIdx = args.indexOf("--out");

if (caseIdIdx === -1) {
  console.error("Error: --case <case-id> is required");
  console.error("Example: node scripts/prepare-shipment-evidence.mjs --case qc-coop-2026-0003");
  process.exit(1);
}

const caseId = args[caseIdIdx + 1];
const outFile = outIdx !== -1 ? args[outIdx + 1] : null;

// ─── Load manifest ───────────────────────────────────────────────────────────

const manifestPath = join(ROOT, "evidence", caseId, "manifest.json");

if (!existsSync(manifestPath)) {
  console.error(`Error: manifest not found at ${manifestPath}`);
  process.exit(1);
}

const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));

// ─── Resolve image paths ──────────────────────────────────────────────────────

function resolveImagePath(filename) {
  const full = join(ROOT, "evidence", "images", filename);
  const compact = join(ROOT, "evidence", "images_compact", filename);
  if (existsSync(compact)) return compact;
  if (existsSync(full)) return full;
  return null;
}

const exporterFile = manifest.exporter_evidence.file;
const importerFile = manifest.importer_evidence.file;

const exporterPath = resolveImagePath(exporterFile);
const importerPath = resolveImagePath(importerFile);

console.error(`Case: ${caseId}`);
console.error(`Scenario: ${manifest.scenario} — ${manifest.label}`);
console.error(`Exporter image: ${exporterPath ?? "NOT FOUND"}`);
console.error(`Importer image: ${importerPath ?? "NOT FOUND"}`);

// ─── IPFS pinning (stub) ──────────────────────────────────────────────────────

async function pinToIPFS(filePath, name) {
  // TODO: Implement actual Pinata pinning
  // const jwt = process.env.PINATA_JWT;
  // if (!jwt) throw new Error("PINATA_JWT env var not set");
  // const form = new FormData();
  // form.append("file", fs.createReadStream(filePath));
  // form.append("pinataMetadata", JSON.stringify({ name }));
  // const res = await fetch("https://api.pinata.cloud/pinning/pinFileToIPFS", {
  //   method: "POST", headers: { Authorization: `Bearer ${jwt}` }, body: form
  // });
  // const data = await res.json();
  // return data.IpfsHash;
  console.error(`  [STUB] Would pin ${filePath} to IPFS as "${name}"`);
  return manifest.exporter_evidence.ipfs_cid; // return fixture CID
}

// ─── Build evidence pack ──────────────────────────────────────────────────────

const ipfsGateway = "https://ipfs.io/ipfs";

let exporterCid = manifest.exporter_evidence.ipfs_cid;
let importerCid = manifest.importer_evidence.ipfs_cid;

if (pinFlag) {
  console.error("\nPinning evidence to IPFS...");
  if (exporterPath) {
    exporterCid = await pinToIPFS(exporterPath, `${caseId}-exporter-${exporterFile}`);
    console.error(`  Exporter CID: ${exporterCid}`);
  }
  if (importerPath) {
    importerCid = await pinToIPFS(importerPath, `${caseId}-importer-${importerFile}`);
    console.error(`  Importer CID: ${importerCid}`);
  }
}

const evidencePack = {
  case_id: manifest.case_id,
  scenario: manifest.scenario,
  label: manifest.label,
  trade_ref: manifest.trade_ref,
  contract_clause: manifest.contract_clause,
  court_question: manifest.court_question,
  exporter_evidence: {
    label: manifest.exporter_evidence.label,
    description: manifest.exporter_evidence.description,
    local_path: exporterPath,
    ipfs_cid: exporterCid,
    url: `${ipfsGateway}/${exporterCid}`,
  },
  importer_evidence: {
    label: manifest.importer_evidence.label,
    description: manifest.importer_evidence.description,
    local_path: importerPath,
    ipfs_cid: importerCid,
    url: `${ipfsGateway}/${importerCid}`,
  },
  expected_verdict: manifest.verdict,
  expected_consequence: manifest.consequence,
  prepared_at: new Date().toISOString(),
};

// ─── Output ───────────────────────────────────────────────────────────────────

const output = JSON.stringify(evidencePack, null, 2);

if (outFile) {
  writeFileSync(outFile, output, "utf8");
  console.error(`\nEvidence pack written to: ${outFile}`);
} else {
  console.log(output);
}
