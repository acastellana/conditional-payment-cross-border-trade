#!/usr/bin/env node
/**
 * tfx-relay-service.mjs
 *
 * Trade Finance settlement relay service.
 *
 * Watches 3 TradeFxSettlement contracts for ShipmentContested events.
 * When a contest is detected:
 *   1. Fetches manifest from IPFS to get court sheet CIDs
 *   2. Deploys ShipmentDeadlineCourt.py on GenLayer Studionet
 *   3. Waits for AI jury evaluation to finalize (~100-300s)
 *   4. Reads verdict from the court contract state
 *   5. Calls resolveShipmentVerdict() on TradeFxSettlement via oracleRelayer
 *
 * Note: Full LayerZero delivery (GenLayer → zkSync → Base via LZ) requires
 * CALLER_ROLE on BridgeForwarder at 0x95c4E5... — pending grant from GenLayer team.
 * Until then, step 5 uses the oracleRelayer direct path (permanent testnet fallback).
 *
 * Usage:
 *   node scripts/tfx-relay-service.mjs
 */

import { createPublicClient, createWalletClient, http, parseAbi } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { baseSepolia } from "viem/chains";
import { createClient, createAccount } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dir   = dirname(fileURLToPath(import.meta.url));
const ROOT    = join(__dir, "..");
const RPC     = "https://sepolia.base.org";
const GL_RPC  = "https://studio.genlayer.com/api";

// ── Known addresses ───────────────────────────────────────────────────────────
const BRIDGE_SENDER_GL  = "0xC94bE65Baf99590B1523db557D157fabaD2DA729";
const LZ_DST_EID        = 40245; // Base Sepolia
const ORACLE_RELAYER    = "0x7b9797c4c2DA625b120A27AD2c07bECB7A0E30fa";

// Keys
function loadKey(p) {
  const k = readFileSync(p, "utf8").trim();
  return k.startsWith("0x") ? k : "0x" + k;
}
const RELAYER_KEY  = loadKey(`${ROOT}/base-sepolia/.wallets/relayer.key`);
const GL_KEY       = loadKey(`${ROOT}/base-sepolia/.wallets/relayer.key`); // same wallet on GL

// Load scenario contracts
const SCENARIOS = JSON.parse(readFileSync(`${ROOT}/artifacts/v5-scenarios.json`, "utf8"));

// ── Viem clients ──────────────────────────────────────────────────────────────
const transport  = http(RPC);
const pub        = createPublicClient({ chain: baseSepolia, transport });
const relayerAcct = privateKeyToAccount(RELAYER_KEY);
const relayerW   = createWalletClient({ chain: baseSepolia, transport, account: relayerAcct });

// ── GenLayer client ───────────────────────────────────────────────────────────
const glAccount = createAccount(GL_KEY);
const glClient  = createClient({ chain: studionet, endpoint: GL_RPC, account: glAccount });

// ── ABIs ──────────────────────────────────────────────────────────────────────
const TFX_ABI = parseAbi([
  "event ShipmentContested(address indexed importer, string manifestCid, string statement, uint256 contestDeadline, uint256 timestamp)",
  "function resolveShipmentVerdict(uint8 verdict, string caseId, string reasonSummary)",
  "function shipmentStatus() view returns (uint8)",
  "function shipmentManifestCid() view returns (string)",
]);

// ── State ─────────────────────────────────────────────────────────────────────
const STATE_FILE   = `${ROOT}/artifacts/relay-state.json`;
const COURT_SOURCE = readFileSync(`${ROOT}/contracts/ShipmentDeadlineCourt.py`, "utf8");

function loadState() {
  try {
    if (existsSync(STATE_FILE)) return JSON.parse(readFileSync(STATE_FILE, "utf8"));
  } catch {}
  return { processed: {} };
}

function saveState(s) {
  writeFileSync(STATE_FILE, JSON.stringify(s, null, 2));
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ── IPFS fetch ────────────────────────────────────────────────────────────────
async function fetchManifest(cid) {
  const url = `https://ipfs.io/ipfs/${cid}`;
  const r   = await fetch(url, { signal: AbortSignal.timeout(15000) });
  if (!r.ok) throw new Error(`IPFS fetch failed: ${r.status} for ${cid}`);
  return r.json();
}

// ── GenLayer raw RPC ──────────────────────────────────────────────────────────
async function glRpc(method, params) {
  const r = await fetch(GL_RPC, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
    signal: AbortSignal.timeout(10000),
  });
  const d = await r.json();
  return d?.result ?? null;
}

// ── Deploy ShipmentDeadlineCourt on GenLayer ──────────────────────────────────
async function deployCourtOnGL(settlementAddr, caseId, statement, sheetACid, sheetBCid) {
  console.log(`[GL] Deploying ShipmentDeadlineCourt for ${caseId}...`);
  console.log(`[GL]   settlement: ${settlementAddr}`);
  console.log(`[GL]   court_sheet_a: ${sheetACid}`);
  console.log(`[GL]   court_sheet_b: ${sheetBCid}`);

  const txHash = await glClient.deployContract({
    code: COURT_SOURCE,
    args: [
      caseId,
      settlementAddr,
      statement,
      "shipment-deadline-v1",
      sheetACid,
      sheetBCid,
      BRIDGE_SENDER_GL,
      LZ_DST_EID,
    ],
    leaderOnly: false,
  });

  console.log(`[GL] Deploy tx: ${txHash}`);
  console.log(`[GL] Explorer: https://explorer-studio.genlayer.com/transactions/${txHash}`);
  return txHash;
}

// ── Wait for court finalization ───────────────────────────────────────────────
async function waitForFinalization(txHash, timeoutMs = 5 * 60 * 1000) {
  const start   = Date.now();
  const pollMs  = 5000;
  const maxIter = Math.ceil(timeoutMs / pollMs);

  console.log(`[GL] Waiting for consensus (up to ${timeoutMs / 1000}s)...`);

  for (let i = 0; i < maxIter; i++) {
    await sleep(pollMs);

    try {
      const tx = await glClient.getTransaction({ hash: txHash });
      const status = tx?.statusName ?? "UNKNOWN";
      const result = tx?.resultName ?? "";

      if (i % 6 === 0) console.log(`[GL]   ${Math.round((Date.now()-start)/1000)}s — status: ${status} ${result}`);

      if (status === "FINALIZED") {
        console.log(`[GL] ✅ Finalized! result: ${result}`);
        return { status, result, tx };
      }

      if (["CANCELED"].includes(status) || ["FAILURE","DISAGREE","DETERMINISTIC_VIOLATION"].includes(result)) {
        console.error(`[GL] ❌ Terminal state: ${status}/${result}`);
        return { status, result, tx };
      }
    } catch { /* tx not indexed yet */ }
  }

  console.error(`[GL] ⏰ Timed out after ${timeoutMs/1000}s`);
  return { status: "TIMEOUT", result: "", tx: null };
}

// ── Read verdict from court state ─────────────────────────────────────────────
async function readCourtVerdict(txHash) {
  // Get contract address from receipt
  let courtAddr = null;
  for (let i = 0; i < 10; i++) {
    const rec = await glRpc("gen_getTransactionReceipt", [txHash]);
    if (rec) {
      courtAddr = rec.contract_address || rec.data?.contract_address || rec.to_address;
      if (courtAddr) break;
    }
    await sleep(2000);
  }

  if (!courtAddr) throw new Error("Could not get court contract address from receipt");

  console.log(`[GL] Court contract: ${courtAddr}`);

  // Read contract state
  const state = await glRpc("gen_getContractState", [courtAddr]);
  if (!state) throw new Error("Could not read court contract state");

  console.log(`[GL] Court state:`, JSON.stringify(state, null, 2));

  const verdict       = state.verdict        ?? "UNDETERMINED";
  const verdictReason = state.verdict_reason ?? "";

  // Map verdict string to uint8 (must match TradeFxSettlement.sol)
  const verdictCode = { "TIMELY": 1, "LATE": 2, "UNDETERMINED": 3 }[verdict] ?? 3;

  return { courtAddr, verdict, verdictCode, verdictReason };
}

// ── Deliver verdict to Base Sepolia ──────────────────────────────────────────
async function deliverVerdict(settlementAddr, caseId, verdictCode, verdictReason) {
  console.log(`[Base] Delivering verdict ${verdictCode} to ${settlementAddr}...`);
  console.log(`[Base]   reason: ${verdictReason.slice(0, 100)}...`);

  const hash = await relayerW.writeContract({
    address: settlementAddr,
    abi: TFX_ABI,
    functionName: "resolveShipmentVerdict",
    args: [verdictCode, caseId, verdictReason.slice(0, 500)],
  });

  const receipt = await pub.waitForTransactionReceipt({ hash, timeout: 60_000 });
  if (receipt.status !== "success") throw new Error(`resolveShipmentVerdict reverted: ${hash}`);

  console.log(`[Base] ✅ Verdict delivered! tx: ${hash}`);
  return hash;
}

// ── Process one contested settlement ─────────────────────────────────────────
async function processContest(scen, manifestCid, statement) {
  const settlementAddr = scen.contract;
  const caseId         = scen.caseId;

  // 1. Fetch manifest to get court sheet CIDs
  console.log(`\n[Relay] Fetching manifest ${manifestCid}...`);
  const manifest = await fetchManifest(manifestCid);
  const sheetACid = manifest.court_inputs.court_sheet_a.cid.replace("ipfs://", "");
  const sheetBCid = manifest.court_inputs.court_sheet_b.cid.replace("ipfs://", "");
  console.log(`[Relay] court_sheet_a: ${sheetACid}`);
  console.log(`[Relay] court_sheet_b: ${sheetBCid}`);

  // 2. Deploy court contract on GenLayer
  const txHash = await deployCourtOnGL(settlementAddr, caseId, statement, sheetACid, sheetBCid);

  // 3. Wait for finalization
  const { status, result } = await waitForFinalization(txHash);

  if (status === "TIMEOUT" || status === "CANCELED") {
    throw new Error(`Court evaluation failed: ${status}/${result}`);
  }

  // 4. Read verdict
  const { courtAddr, verdict, verdictCode, verdictReason } = await readCourtVerdict(txHash);

  console.log(`\n[Relay] ═══════════════════════════════`);
  console.log(`[Relay] Case: ${caseId}`);
  console.log(`[Relay] Verdict: ${verdict} (code=${verdictCode})`);
  console.log(`[Relay] Court: ${courtAddr}`);
  console.log(`[Relay] GL tx: ${txHash}`);
  console.log(`[Relay] ═══════════════════════════════\n`);

  // 5. Deliver verdict to Base Sepolia
  const deliveryTx = await deliverVerdict(settlementAddr, caseId, verdictCode, verdictReason);

  return {
    caseId,
    settlementAddr,
    glTxHash: txHash,
    courtAddr,
    verdict,
    verdictCode,
    verdictReason,
    deliveryTx,
    processedAt: new Date().toISOString(),
  };
}

// ── Main polling loop ─────────────────────────────────────────────────────────
async function main() {
  console.log("🚀 TFX Relay Service starting...\n");
  console.log(`Watching ${SCENARIOS.length} scenario contracts:`);
  SCENARIOS.forEach(s => console.log(`  ${s.label}: ${s.contract}`));
  console.log();

  const state = loadState();
  const results = [];

  for (const scen of SCENARIOS) {
    const key = `${scen.caseId}:${scen.contract}`;

    if (state.processed[key]) {
      console.log(`[Relay] ${scen.label} already processed — skipping`);
      results.push(state.processed[key]);
      continue;
    }

    // Check current shipmentStatus on-chain
    const shipStatus = await pub.readContract({
      address: scen.contract,
      abi: TFX_ABI,
      functionName: "shipmentStatus",
    });

    if (shipStatus !== 2) {
      console.log(`[Relay] ${scen.label}: shipmentStatus=${shipStatus} (not CONTESTED) — skipping`);
      continue;
    }

    // Get manifest CID from contract
    const manifestCid = await pub.readContract({
      address: scen.contract,
      abi: TFX_ABI,
      functionName: "shipmentManifestCid",
    });

    const statement = "Shipment under Contract ISPA-2025-BOL-PER-0047 crossed Bolivian export customs at Desaguadero on or before 2026-04-05T23:59:59-04:00.";

    console.log(`\n${"═".repeat(60)}`);
    console.log(`Processing: ${scen.label} — ${scen.caseId}`);
    console.log(`${"═".repeat(60)}`);

    try {
      const result = await processContest(scen, manifestCid, statement);
      state.processed[key] = result;
      saveState(state);
      results.push(result);
      console.log(`\n✅ ${scen.label} complete!\n`);
    } catch (err) {
      console.error(`❌ ${scen.label} failed:`, err.message);
    }

    // Small pause between scenarios
    await sleep(5000);
  }

  // Write final results
  writeFileSync(`${ROOT}/artifacts/relay-results.json`, JSON.stringify(results, null, 2));

  console.log("\n" + "═".repeat(60));
  console.log("RELAY SERVICE COMPLETE");
  console.log("═".repeat(60));
  results.forEach(r => {
    if (!r) return;
    console.log(`\n  ${r.caseId}: ${r.verdict} (${r.verdictCode})`);
    console.log(`    GL court: ${r.courtAddr}`);
    console.log(`    GL tx:    ${r.glTxHash}`);
    console.log(`    Base tx:  ${r.deliveryTx}`);
  });
  console.log(`\nSaved: artifacts/relay-results.json`);
}

main().catch(e => { console.error("Fatal:", e); process.exit(1); });
