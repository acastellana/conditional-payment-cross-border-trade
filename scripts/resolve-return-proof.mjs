#!/usr/bin/env node
/**
 * resolve-return-proof.mjs
 * Steps 6-9: Deploy ReturnProofCourt on GenLayer → AI jury → resolveReturnProof on Base Sepolia
 */
import { createPublicClient, createWalletClient, http, parseAbi } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { baseSepolia } from "viem/chains";
import { createClient, createAccount } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import { readFileSync, writeFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dir = dirname(fileURLToPath(import.meta.url));
const ROOT  = join(__dir, "..");
const RPC   = "https://sepolia.base.org";
const GL_RPC = "https://studio.genlayer.com/api";

const CONTRACT_ADDR    = "0xf80F899994DBeDd592C5472C556d64847E0800B2";
const COURT_FACTORY    = "0xd533cB0B52E85b3F506b6f0c28b8f6bc4E449Dda";
const BRIDGE_SENDER_GL = "0xC94bE65Baf99590B1523db557D157fabaD2DA729";
const LZ_DST_EID       = 40245;

const RETURN_SHEET_A_CID = "Qmcr8yEpMn3VSNMDxZDmEE3Y2xpLyZSPs3vydR5ysiU4A5";
const RETURN_SHEET_B_CID = "Qmc1kitGkw3193Dr1BvT98aJ4vjNjafB2EawjS2nKvGfY3";
const CASE_ID            = "qc-coop-2026-0009";
const STATEMENT          = "Cargo qc-coop-2026-0009 was formally rejected by SUNAT PCF Desaguadero on 2026-04-21 and returned via ANB Desaguadero on 2026-04-22.";

function loadKey(p) {
  const k = readFileSync(p, "utf8").trim();
  return k.startsWith("0x") ? k : "0x" + k;
}
const RELAYER_KEY = loadKey(`${ROOT}/base-sepolia/.wallets/relayer.key`);

const transport  = http(RPC);
const pub        = createPublicClient({ chain: baseSepolia, transport });
const relayerAcct = privateKeyToAccount(RELAYER_KEY);
const relayerW   = createWalletClient({ chain: baseSepolia, transport, account: relayerAcct });

const glAccount = createAccount(RELAYER_KEY);
const glClient  = createClient({ chain: studionet, endpoint: GL_RPC, account: glAccount });

const TFX_ABI = parseAbi([
  "function resolveReturnProof(uint8 verdict, string caseId, string reasonSummary)",
  "function returnProofStatus() view returns (uint8)",
  "function status() view returns (uint8)",
  "function fundedAmount() view returns (uint256)",
]);

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

async function waitTx(hash, label) {
  const receipt = await pub.waitForTransactionReceipt({ hash, timeout: 60_000 });
  if (receipt.status !== "success") throw new Error(`${label} reverted: ${hash}`);
  console.log(`  ✅ ${label}: ${hash}`);
  return receipt;
}

(async () => {
  console.log("╔══════════════════════════════════════════════════════════════╗");
  console.log("║         RETURN PROOF COURT — Steps 6-9 (Resume)              ║");
  console.log("╚══════════════════════════════════════════════════════════════╝\n");
  console.log(`  Contract:     ${CONTRACT_ADDR}`);
  console.log(`  ReturnSheetA: ${RETURN_SHEET_A_CID}`);
  console.log(`  ReturnSheetB: ${RETURN_SHEET_B_CID}\n`);

  // [6] Deploy ReturnProofCourt on GenLayer
  console.log("[6] Deploying ReturnProofCourt on GenLayer...");
  const source = readFileSync(`${ROOT}/contracts/ReturnProofCourt.py`, "utf8");

  const txHash = await glClient.deployContract({
    code: source,
    args: [
      CASE_ID + "-R",
      CONTRACT_ADDR,
      STATEMENT,
      "return-proof-v1",
      RETURN_SHEET_A_CID,
      RETURN_SHEET_B_CID,
      BRIDGE_SENDER_GL,
      LZ_DST_EID,
      COURT_FACTORY,
    ],
    leaderOnly: false,
  });

  console.log(`  GL deploy tx: ${txHash}`);
  console.log(`  Explorer: https://explorer-studio.genlayer.com/transactions/${txHash}`);

  // [7] Wait for AI jury
  console.log("\n[7] Waiting for AI jury evaluation (up to 6 min)...");
  const start = Date.now();
  let finalStatus = "PENDING";
  let finalResult = "";
  for (let i = 0; i < 72; i++) {
    await sleep(5000);
    try {
      const tx = await glClient.getTransaction({ hash: txHash });
      finalStatus = tx?.statusName ?? "UNKNOWN";
      finalResult = tx?.resultName ?? "";
      const elapsed = Math.round((Date.now() - start) / 1000);
      if (i % 6 === 0) console.log(`  ${elapsed}s — ${finalStatus} ${finalResult}`);
      if (finalStatus === "FINALIZED") { console.log(`  ✅ Finalized! result: ${finalResult}`); break; }
      if (["CANCELED"].includes(finalStatus) || ["FAILURE","DISAGREE","DETERMINISTIC_VIOLATION"].includes(finalResult)) {
        console.error(`  ❌ Terminal: ${finalStatus}/${finalResult}`); break;
      }
    } catch { /* not indexed yet */ }
  }

  if (finalStatus !== "FINALIZED") throw new Error(`GenLayer did not finalize: ${finalStatus}/${finalResult}`);

  // [8] Read verdict
  console.log("\n[8] Reading verdict from ReturnProofCourt state...");
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
  console.log(`  Court contract: ${courtAddr}`);

  const state = await glRpc("gen_getContractState", [courtAddr]);
  console.log("  Court state:", JSON.stringify(state, null, 2));

  const verdict     = state?.verdict ?? "UNDETERMINED";
  const verdictCode = { "RETURN_PROVEN": 1, "RETURN_NOT_PROVEN": 2, "UNDETERMINED": 3 }[verdict] ?? 3;
  const reason      = (state?.verdict_reason ?? "").slice(0, 500);

  console.log(`\n  ══════════════════════════════════════`);
  console.log(`  Verdict: ${verdict} (code=${verdictCode})`);
  console.log(`  Reason:  ${reason.slice(0, 200)}`);
  console.log(`  ══════════════════════════════════════\n`);

  // [9] Deliver verdict to Base Sepolia
  console.log("[9] Delivering verdict to Base Sepolia...");
  const resolveTx = await relayerW.writeContract({
    address: CONTRACT_ADDR,
    abi: TFX_ABI,
    functionName: "resolveReturnProof",
    args: [verdictCode, CASE_ID + "-R", reason],
  }).then(h => waitTx(h, `resolveReturnProof(${verdict}=${verdictCode})`));

  // Final state
  const [rpStatus, status, funded] = await Promise.all([
    pub.readContract({ address: CONTRACT_ADDR, abi: TFX_ABI, functionName: "returnProofStatus" }),
    pub.readContract({ address: CONTRACT_ADDR, abi: TFX_ABI, functionName: "status" }),
    pub.readContract({ address: CONTRACT_ADDR, abi: TFX_ABI, functionName: "fundedAmount" }),
  ]);
  const RP = ["NONE","SUBMITTED","PROVEN","NOT_PROVEN","UNDETERMINED"];
  const CS = ["DRAFT","RATE_PENDING","RATE_LOCKED","FUNDED","ROLL_PENDING","ROLLED","SETTLED","CANCELLED"];

  console.log("\n╔══════════════════════════════════════════════════════════════╗");
  console.log("║                   PHASE 2 COMPLETE ✅                        ║");
  console.log("╚══════════════════════════════════════════════════════════════╝");
  console.log(`  Contract:          ${CONTRACT_ADDR}`);
  console.log(`  GL Court:          ${courtAddr}`);
  console.log(`  Verdict:           ${verdict} (${verdictCode})`);
  console.log(`  returnProofStatus: ${RP[Number(rpStatus)] ?? rpStatus}`);
  console.log(`  contractStatus:    ${CS[Number(status)] ?? status}`);
  console.log(`  fundedAmount:      ${funded} (0 = fully released)`);
  console.log(`  resolveReturnProof tx: ${resolveTx.transactionHash}`);

  const result = {
    contract: CONTRACT_ADDR,
    courtAddr,
    verdict,
    verdictCode,
    verdictReason: reason,
    glTxHash: txHash,
    resolveReturnProofTx: resolveTx.transactionHash,
    finalState: {
      returnProofStatus: RP[Number(rpStatus)] ?? String(rpStatus),
      contractStatus: CS[Number(status)] ?? String(status),
      fundedAmount: String(funded),
    },
  };
  writeFileSync(`${ROOT}/artifacts/return-proof-demo-result.json`, JSON.stringify(result, null, 2));
  console.log(`\n  Saved: artifacts/return-proof-demo-result.json`);
})().catch(e => { console.error("❌", e.message || e); process.exit(1); });
