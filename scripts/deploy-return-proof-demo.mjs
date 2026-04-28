#!/usr/bin/env node
/**
 * deploy-return-proof-demo.mjs
 *
 * Full Phase 2 lifecycle demo for ReturnProofCourt.
 *
 * Steps:
 *  1. Deploy TradeFxSettlement (Phase 2 build) with VERY_LATE scenario settings
 *  2. requestRateLock → receiveRate → approve MockPEN → fundSettlement
 *  3. contestShipment (VERY_LATE evidence — qc-coop-2026-0009 sheets)
 *  4. resolveShipmentVerdict(5 = VERY_LATE) via relayer → RETURN_REQUIRED
 *  5. submitReturnProof(sheetA, sheetB, statement, guidelineVersion)
 *  6. Deploy ReturnProofCourt on GenLayer
 *  7. Wait for AI jury evaluation
 *  8. Read RETURN_PROVEN verdict
 *  9. resolveReturnProof(1) → importer refunded
 *
 * Uses:
 *   - artifacts/new_court_sheet_cids_v3.json   (VERY_LATE shipment sheets)
 *   - artifacts/return_proof_cids.json          (return proof sheets — Phase 2)
 *
 * Usage:
 *   node scripts/deploy-return-proof-demo.mjs
 *   node scripts/deploy-return-proof-demo.mjs --skip-to-return   (skip to step 5)
 */

import {
  createPublicClient, createWalletClient, http,
  parseUnits, parseAbi, formatUnits, decodeAbiParameters, parseAbiParameters
} from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { baseSepolia } from "viem/chains";
import { createClient, createAccount } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "fs";
import { execSync } from "child_process";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dir = dirname(fileURLToPath(import.meta.url));
const ROOT  = join(__dir, "..");
const RPC   = "https://sepolia.base.org";
const GL_RPC = "https://studio.genlayer.com/api";
const FORGE = `${process.env.HOME}/.foundry/bin/forge`;

// ── Known addresses ───────────────────────────────────────────────────────────
const MOCK_PEN        = "0x08bc87f6511913caa4e127c5e4e91618a37a9719";
const ORACLE_RELAYER  = "0x7b9797c4c2DA625b120A27AD2c07bECB7A0E30fa";
const BRIDGE_RECEIVER = "0xc3e6aE892A704c875bF74Df46eD873308db15d82";
const COURT_FACTORY   = "0xd533cB0B52E85b3F506b6f0c28b8f6bc4E449Dda";
const EXPORTER        = "0xe9630ba0e3cc2d3BFC58fbE1Bbde478f06E4CE87";
const IMPORTER        = "0x942C20d078f7417aD67E96714310DA8068850B77";
const BRIDGE_SENDER_GL = "0xC94bE65Baf99590B1523db557D157fabaD2DA729";
const LZ_DST_EID      = 40245;

// ── Keys ─────────────────────────────────────────────────────────────────────
function loadKey(p) {
  const k = readFileSync(p, "utf8").trim();
  return k.startsWith("0x") ? k : "0x" + k;
}
const EXPORTER_KEY = loadKey(`${process.env.HOME}/.internetcourt/.exporter_key`);
const IMPORTER_KEY = loadKey(`${process.env.HOME}/.internetcourt/.importer_key`);
const RELAYER_KEY  = loadKey(`${ROOT}/base-sepolia/.wallets/relayer.key`);

const transport   = http(RPC);
const pub         = createPublicClient({ chain: baseSepolia, transport });
const exporterAcct = privateKeyToAccount(EXPORTER_KEY);
const importerAcct = privateKeyToAccount(IMPORTER_KEY);
const relayerAcct  = privateKeyToAccount(RELAYER_KEY);
const exporterW   = createWalletClient({ chain: baseSepolia, transport, account: exporterAcct });
const importerW   = createWalletClient({ chain: baseSepolia, transport, account: importerAcct });
const relayerW    = createWalletClient({ chain: baseSepolia, transport, account: relayerAcct });

// ── GenLayer client ───────────────────────────────────────────────────────────
const glAccount = createAccount(RELAYER_KEY);
const glClient  = createClient({ chain: studionet, endpoint: GL_RPC, account: glAccount });

// ── CIDs ─────────────────────────────────────────────────────────────────────
const SHIPMENT_CIDS  = JSON.parse(readFileSync(`${ROOT}/artifacts/new_court_sheet_cids_v3.json`, "utf8"));
const RETURN_PROOF   = JSON.parse(readFileSync(`${ROOT}/artifacts/return_proof_cids.json`, "utf8"));

function stripIpfs(cid) { return cid.replace("ipfs://", ""); }

const VERY_LATE_SHEET_A  = stripIpfs(SHIPMENT_CIDS["qc-coop-2026-0009"].court_sheet_a);
const VERY_LATE_SHEET_B  = stripIpfs(SHIPMENT_CIDS["qc-coop-2026-0009"].court_sheet_b);
const RETURN_SHEET_A_CID = stripIpfs(RETURN_PROOF.return_sheet_a);
const RETURN_SHEET_B_CID = stripIpfs(RETURN_PROOF.return_sheet_b);

const CASE_ID        = "qc-coop-2026-0009";
const INVOICE_REF    = "QC-COOP-2026-0009";
const INVOICE_BOB    = parseUnits("150000", 18);
const RATE_18        = parseUnits("0.493", 18);
const ESCROW_PEN     = parseUnits("73950", 18);
const DUE_DATE       = Math.floor(Date.now() / 1000) + 90 * 86400;

const SHIPMENT_STATEMENT = "Shipment under Contract ISPA-2025-BOL-PER-0047 crossed Bolivian export customs at Desaguadero on or before 2026-04-05T23:59:59-04:00.";
const SHIPMENT_GUIDELINE = "shipment-deadline-v1";

const RETURN_PROOF_STATEMENT = RETURN_PROOF.statement;
const RETURN_PROOF_GUIDELINE = "return-proof-v1";

// ── ABIs ─────────────────────────────────────────────────────────────────────
const ERC20_ABI = parseAbi([
  "function approve(address spender, uint256 amount) returns (bool)",
  "function balanceOf(address) view returns (uint256)",
  "function mint(address to, uint256 amount)",
]);

const TFX_ABI = parseAbi([
  "function requestRateLock()",
  "function receiveRate(uint256 rate, bytes32 benchmarkType, bytes32 benchmarkId, uint256 asOfTimestamp)",
  "function fundSettlement()",
  "function contestShipment(string courtSheetACid, string courtSheetBCid, string statement, string guidelineVersion)",
  "function resolveShipmentVerdict(uint8 verdict, string caseId, string reasonSummary)",
  "function submitReturnProof(string returnSheetACid, string returnSheetBCid, string statement, string guidelineVersion)",
  "function resolveReturnProof(uint8 verdict, string caseId, string reasonSummary)",
  "function getReturnProofOracleArgs() view returns (bytes)",
  "function status() view returns (uint8)",
  "function shipmentStatus() view returns (uint8)",
  "function returnProofStatus() view returns (uint8)",
  "function fundedAmount() view returns (uint256)",
  "function returnProofDeadline() view returns (uint256)",
  "function returnProofVerdictReason() view returns (string)",
]);

// ── Helpers ───────────────────────────────────────────────────────────────────
async function waitTx(hash, label) {
  const receipt = await pub.waitForTransactionReceipt({ hash, timeout: 60_000 });
  if (receipt.status !== "success") throw new Error(`${label} reverted: ${hash}`);
  console.log(`    ✅ ${label}: ${hash}`);
  return receipt;
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

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

// ── Deploy TradeFxSettlement ──────────────────────────────────────────────────
function deployContract() {
  console.log("\n  [1] Deploying TradeFxSettlement (Phase 2)...");
  const env = {
    ...process.env,
    DEPLOYER_KEY:        EXPORTER_KEY,
    EXPORTER_ADDR:       EXPORTER,
    IMPORTER_ADDR:       IMPORTER,
    ORACLE_RELAYER_ADDR: ORACLE_RELAYER,
    ADMIN_ADDR:          "0x0000000000000000000000000000000000000000",
    SETTLEMENT_TOKEN:    MOCK_PEN,
    INVOICE_BOB:         INVOICE_BOB.toString(),
    INVOICE_REF:         INVOICE_REF,
    DUE_DATE_UNIX:       DUE_DATE.toString(),
    SOURCE_CURRENCY:     "BOB",
    SETTLEMENT_CURRENCY: "PEN",
    BRIDGE_RECEIVER:     BRIDGE_RECEIVER,
    COURT_FACTORY:       "0x0000000000000000000000000000000000000000", // IC disabled — use direct relayer for demo
  };

  mkdirSync(`${ROOT}/base-sepolia/artifacts`, { recursive: true });
  execSync(
    `${FORGE} script script/DeployTradeFx.s.sol --rpc-url ${RPC} --broadcast --sig "run()" -vv`,
    { cwd: `${ROOT}/base-sepolia`, env, encoding: "utf8", timeout: 120_000 }
  );

  const manifest = JSON.parse(readFileSync(`${ROOT}/base-sepolia/artifacts/trade-fx-base-deployment.json`, "utf8"));
  console.log(`    ✅ Deployed: ${manifest.contract}`);
  return manifest.contract;
}

// ── Deploy ReturnProofCourt on GenLayer ───────────────────────────────────────
async function deployReturnProofCourt(settlementAddr, caseId, statement, sheetACid, sheetBCid) {
  const source = readFileSync(`${ROOT}/contracts/ReturnProofCourt.py`, "utf8");

  console.log(`\n  [6] Deploying ReturnProofCourt on GenLayer...`);
  console.log(`      settlement:     ${settlementAddr}`);
  console.log(`      return_sheet_a: ${sheetACid}`);
  console.log(`      return_sheet_b: ${sheetBCid}`);

  const txHash = await glClient.deployContract({
    code: source,
    args: [
      caseId + "-R",
      settlementAddr,
      statement,
      "return-proof-v1",
      sheetACid,
      sheetBCid,
      BRIDGE_SENDER_GL,
      LZ_DST_EID,
      COURT_FACTORY,
    ],
    leaderOnly: false,
  });

  console.log(`      GL tx: ${txHash}`);
  console.log(`      Explorer: https://explorer-studio.genlayer.com/transactions/${txHash}`);
  return txHash;
}

// ── Wait for GenLayer finalization ────────────────────────────────────────────
async function waitForFinalization(txHash, timeoutMs = 5 * 60 * 1000) {
  const start  = Date.now();
  const pollMs = 5000;
  const maxIter = Math.ceil(timeoutMs / pollMs);

  console.log(`      Waiting for consensus (up to ${timeoutMs/1000}s)...`);

  for (let i = 0; i < maxIter; i++) {
    await sleep(pollMs);
    try {
      const tx = await glClient.getTransaction({ hash: txHash });
      const status = tx?.statusName ?? "UNKNOWN";
      const result = tx?.resultName ?? "";
      if (i % 6 === 0) console.log(`      ${Math.round((Date.now()-start)/1000)}s — ${status} ${result}`);
      if (status === "FINALIZED") { console.log(`      ✅ Finalized! result: ${result}`); return { status, result }; }
      if (["CANCELED"].includes(status) || ["FAILURE","DISAGREE","DETERMINISTIC_VIOLATION"].includes(result)) {
        console.error(`      ❌ Terminal: ${status}/${result}`); return { status, result };
      }
    } catch { /* not indexed yet */ }
  }
  console.error(`      ⏰ Timeout`);
  return { status: "TIMEOUT", result: "" };
}

// ── Read ReturnProofCourt verdict from state ──────────────────────────────────
async function readReturnProofVerdict(txHash) {
  let courtAddr = null;
  for (let i = 0; i < 10; i++) {
    const rec = await glRpc("gen_getTransactionReceipt", [txHash]);
    if (rec) {
      courtAddr = rec.contract_address || rec.data?.contract_address || rec.to_address;
      if (courtAddr) break;
    }
    await sleep(2000);
  }
  if (!courtAddr) throw new Error("Could not get court contract address");

  console.log(`      Court contract: ${courtAddr}`);
  const state = await glRpc("gen_getContractState", [courtAddr]);
  if (!state) throw new Error("Could not read court state");

  console.log(`      Court state:`, JSON.stringify(state, null, 2));

  const verdict       = state.verdict        ?? "UNDETERMINED";
  const verdictReason = state.verdict_reason ?? "";
  const verdictCode   = { "RETURN_PROVEN": 1, "RETURN_NOT_PROVEN": 2, "UNDETERMINED": 3 }[verdict] ?? 3;

  return { courtAddr, verdict, verdictCode, verdictReason };
}

// ── Main lifecycle ────────────────────────────────────────────────────────────
const SKIP_TO_RETURN = process.argv.includes("--skip-to-return");
let CONTRACT_ADDR    = null;

// Check for existing deployment to skip to
if (SKIP_TO_RETURN && existsSync(`${ROOT}/artifacts/return-proof-demo-state.json`)) {
  const saved = JSON.parse(readFileSync(`${ROOT}/artifacts/return-proof-demo-state.json`, "utf8"));
  CONTRACT_ADDR = saved.contract;
  console.log(`  ♻️  Resuming from saved state. Contract: ${CONTRACT_ADDR}`);
}

(async () => {
  console.log("╔══════════════════════════════════════════════════════════════╗");
  console.log("║         RETURN PROOF COURT — Phase 2 Lifecycle Demo          ║");
  console.log("╚══════════════════════════════════════════════════════════════╝\n");
  console.log(`  Case:          ${CASE_ID}`);
  console.log(`  Shipment A:    ${VERY_LATE_SHEET_A.slice(0, 20)}...`);
  console.log(`  Shipment B:    ${VERY_LATE_SHEET_B.slice(0, 20)}...`);
  console.log(`  Return A:      ${RETURN_SHEET_A_CID.slice(0, 20)}...`);
  console.log(`  Return B:      ${RETURN_SHEET_B_CID.slice(0, 20)}...`);
  console.log();

  const result = { caseId: CASE_ID, txs: {} };

  if (!SKIP_TO_RETURN) {
    // ── Phase 1: Deploy + VERY_LATE contest ────────────────────────────────
    const contractAddr = deployContract();
    result.contract = contractAddr;
    CONTRACT_ADDR   = contractAddr;

    await sleep(5000);

    console.log("\n  [2] requestRateLock (exporter)...");
    result.txs.requestRateLock = await exporterW.writeContract({
      address: contractAddr, abi: TFX_ABI, functionName: "requestRateLock"
    }).then(h => waitTx(h, "requestRateLock")).then(r => r.transactionHash);

    await sleep(3000);

    console.log("\n  [3] receiveRate (relayer)...");
    result.txs.receiveRate = await relayerW.writeContract({
      address: contractAddr, abi: TFX_ABI, functionName: "receiveRate",
      args: [
        RATE_18,
        "0x4243525042434243524f5345524154450000000000000000000000000000000",
        "0x514332303236303030390000000000000000000000000000000000000000000",
        BigInt(Math.floor(Date.now() / 1000))
      ]
    }).then(h => waitTx(h, "receiveRate")).then(r => r.transactionHash);

    await sleep(3000);

    // Mint + approve + fund
    const penBal = await pub.readContract({ address: MOCK_PEN, abi: ERC20_ABI, functionName: "balanceOf", args: [IMPORTER] });
    if (penBal < ESCROW_PEN) {
      console.log("\n  [4a] Minting MockPEN...");
      await importerW.writeContract({ address: MOCK_PEN, abi: ERC20_ABI, functionName: "mint", args: [IMPORTER, ESCROW_PEN * 2n] }).then(h => waitTx(h, "mint"));
    }

    console.log("\n  [4] Approve MockPEN + fundSettlement (importer)...");
    result.txs.approve = await importerW.writeContract({
      address: MOCK_PEN, abi: ERC20_ABI, functionName: "approve", args: [contractAddr, ESCROW_PEN]
    }).then(h => waitTx(h, "approve")).then(r => r.transactionHash);

    await sleep(3000);

    result.txs.fundSettlement = await importerW.writeContract({
      address: contractAddr, abi: TFX_ABI, functionName: "fundSettlement"
    }).then(h => waitTx(h, "fundSettlement")).then(r => r.transactionHash);

    await sleep(3000);

    console.log("\n  [5] contestShipment (VERY_LATE scenario)...");
    result.txs.contestShipment = await importerW.writeContract({
      address: contractAddr, abi: TFX_ABI, functionName: "contestShipment",
      args: [VERY_LATE_SHEET_A, VERY_LATE_SHEET_B, SHIPMENT_STATEMENT, SHIPMENT_GUIDELINE]
    }).then(h => waitTx(h, "contestShipment")).then(r => r.transactionHash);

    await sleep(3000);

    // Simulate VERY_LATE verdict from relayer (direct path for demo speed)
    console.log("\n  [5b] Delivering VERY_LATE verdict (via relayer — direct testnet path)...");
    result.txs.resolveShipment = await relayerW.writeContract({
      address: contractAddr, abi: TFX_ABI, functionName: "resolveShipmentVerdict",
      args: [5, CASE_ID, "Shipment crossed 12 days after deadline — VERY_LATE verdict confirmed by AI jury."]
    }).then(h => waitTx(h, "resolveShipmentVerdict(VERY_LATE=5)")).then(r => r.transactionHash);

    const shipStatus = await pub.readContract({ address: contractAddr, abi: TFX_ABI, functionName: "shipmentStatus" });
    console.log(`    shipmentStatus: ${shipStatus} (expected 6=RETURN_REQUIRED) ${shipStatus === 6n ? "✅" : "❌"}`);

    const rpDeadline = await pub.readContract({ address: contractAddr, abi: TFX_ABI, functionName: "returnProofDeadline" });
    console.log(`    returnProofDeadline: ${new Date(Number(rpDeadline) * 1000).toISOString()}`);

    // Save state for resume
    writeFileSync(`${ROOT}/artifacts/return-proof-demo-state.json`, JSON.stringify({ ...result, contract: contractAddr }, null, 2));

    await sleep(5000);
  } else {
    result.contract = CONTRACT_ADDR;
    console.log(`  Skipping to return proof submission. Contract: ${CONTRACT_ADDR}`);
  }

  const contractAddr = result.contract ?? CONTRACT_ADDR;

  // ── Phase 2: Submit return proof + GenLayer evaluation ────────────────────
  console.log("\n  [5] submitReturnProof (importer)...");
  result.txs.submitReturnProof = await importerW.writeContract({
    address: contractAddr, abi: TFX_ABI, functionName: "submitReturnProof",
    args: [RETURN_SHEET_A_CID, RETURN_SHEET_B_CID, RETURN_PROOF_STATEMENT, RETURN_PROOF_GUIDELINE]
  }).then(h => waitTx(h, "submitReturnProof")).then(r => r.transactionHash);

  await sleep(3000);

  const rpStatus = await pub.readContract({ address: contractAddr, abi: TFX_ABI, functionName: "returnProofStatus" });
  console.log(`    returnProofStatus: ${rpStatus} (expected 1=SUBMITTED) ${rpStatus === 1n ? "✅" : "❌"}`);

  // ── Deploy ReturnProofCourt on GenLayer ───────────────────────────────────
  const txHash = await deployReturnProofCourt(contractAddr, CASE_ID, RETURN_PROOF_STATEMENT, RETURN_SHEET_A_CID, RETURN_SHEET_B_CID);
  result.glTxHash = txHash;

  // ── Wait for AI jury finalization ─────────────────────────────────────────
  console.log("\n  [7] Waiting for AI jury evaluation...");
  const { status: glStatus, result: glResult } = await waitForFinalization(txHash, 6 * 60 * 1000);

  if (glStatus === "TIMEOUT" || glStatus === "CANCELED") {
    throw new Error(`ReturnProofCourt evaluation failed: ${glStatus}/${glResult}`);
  }

  // ── Read verdict ──────────────────────────────────────────────────────────
  console.log("\n  [8] Reading verdict from GenLayer court state...");
  const { courtAddr, verdict, verdictCode, verdictReason } = await readReturnProofVerdict(txHash);
  result.courtAddr     = courtAddr;
  result.verdict       = verdict;
  result.verdictCode   = verdictCode;
  result.verdictReason = verdictReason;

  console.log(`\n  ═══════════════════════════════════════`);
  console.log(`  Return Proof Verdict: ${verdict} (code=${verdictCode})`);
  console.log(`  Reason: ${verdictReason.slice(0, 150)}`);
  console.log(`  ═══════════════════════════════════════\n`);

  // ── Deliver verdict to Base Sepolia ───────────────────────────────────────
  console.log("  [9] Delivering return proof verdict to Base Sepolia...");
  result.txs.resolveReturnProof = await relayerW.writeContract({
    address: contractAddr, abi: TFX_ABI, functionName: "resolveReturnProof",
    args: [verdictCode, CASE_ID + "-R", verdictReason.slice(0, 500)]
  }).then(h => waitTx(h, `resolveReturnProof(${verdict}=${verdictCode})`)).then(r => r.transactionHash);

  // ── Final state check ─────────────────────────────────────────────────────
  const finalRpStatus  = await pub.readContract({ address: contractAddr, abi: TFX_ABI, functionName: "returnProofStatus" });
  const finalFunded    = await pub.readContract({ address: contractAddr, abi: TFX_ABI, functionName: "fundedAmount" });
  const finalStatus    = await pub.readContract({ address: contractAddr, abi: TFX_ABI, functionName: "status" });

  const RP_STATUS_NAMES = ["NONE","SUBMITTED","PROVEN","NOT_PROVEN","UNDETERMINED"];
  const STATUS_NAMES    = ["DRAFT","RATE_PENDING","RATE_LOCKED","FUNDED","ROLL_PENDING","ROLLED","SETTLED","CANCELLED"];

  result.finalState = {
    returnProofStatus: RP_STATUS_NAMES[Number(finalRpStatus)] ?? String(finalRpStatus),
    fundedAmount: formatUnits(finalFunded, 18),
    contractStatus: STATUS_NAMES[Number(finalStatus)] ?? String(finalStatus),
  };

  console.log("\n╔══════════════════════════════════════════════════════════════╗");
  console.log("║                   PHASE 2 DEMO COMPLETE                      ║");
  console.log("╚══════════════════════════════════════════════════════════════╝");
  console.log(`\n  Contract:           ${contractAddr}`);
  console.log(`  GL Court:           ${courtAddr}`);
  console.log(`  Verdict:            ${verdict} (${verdictCode})`);
  console.log(`  returnProofStatus:  ${result.finalState.returnProofStatus}`);
  console.log(`  contractStatus:     ${result.finalState.contractStatus}`);
  console.log(`  fundedAmount:       ${result.finalState.fundedAmount} PEN (should be 0 if PROVEN)`);
  console.log(`\n  Transactions:`);
  Object.entries(result.txs).forEach(([k, v]) => console.log(`    ${k}: ${v}`));

  // Save final result
  writeFileSync(`${ROOT}/artifacts/return-proof-demo-result.json`, JSON.stringify(result, null, 2));
  console.log(`\n  Saved: artifacts/return-proof-demo-result.json`);
})().catch(e => { console.error("❌", e); process.exit(1); });
