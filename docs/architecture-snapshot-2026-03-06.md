# Architecture Snapshot — 2026-03-06

This document records the state of the system at the point where the product thesis was validated.
It serves as the reference for all future iterations. Do not modify this file retroactively.

---

## What the system does (one sentence)

A benchmark-based settlement engine that locks and extends cross-border invoice amounts using validator-reproducible data, while keeping official rates as an audit reference.

## What it does not do

- Not a letter of credit
- Not a bank payment rail
- Not full trade finance automation
- Not cargo or document arbitration
- Not a dispute resolution system
- Not a stablecoin or custody layer

---

## Contract Addresses

| Contract | Chain | Address |
|---|---|---|
| TradeFxSettlement | Base Sepolia (84532) | `0x5231a9B232abD0d8533D7046994235baEb01696d` |
| FxBenchmarkOracle | GenLayer Studionet | `0x3B8501bAcaB70dedbC6f8B8EFCB888ba66cbc73e` |

---

## Wallets

| Role | Address | Key Location |
|---|---|---|
| Exporter / Deployer | `0xe9630ba0e3cc2d3BFC58fbE1Bbde478f06E4CE87` | `~/.internetcourt/.exporter_key` |
| Importer | `0x942C20d078f7417aD67E96714310DA8068850B77` | `~/.internetcourt/.importer_key` |
| Oracle Relayer (dedicated) | `0x7b9797c4c2DA625b120A27AD2c07bECB7A0E30fa` | `base-sepolia/.wallets/relayer.key` |

---

## Demo Trade Parameters

| Field | Value |
|---|---|
| Invoice Ref | QC-COOP-2026-0001 |
| Exporter | Coop Quinoa Andina (Bolivia) |
| Importer | Alimentos del Pacífico SAC (Peru) |
| Invoice Amount | 150,000 BOB |
| Settlement Amount | 73,950 PEN |
| Locked Rate | 0.493 BOB/PEN |
| Original Due Date | 2026-04-05 |
| Current Due Date | 2026-05-05 (after roll #1) |
| Roll Count | 1 |
| Roll Cost | 0 (spot re-lock) |
| Final Status | ROLLED |

---

## Benchmark Hierarchy

| Tier | Source | Type | Status |
|---|---|---|---|
| Primary | BCRP series PD04638PD × BCB peg 6.96 | `BCRP_BCB_CROSS` | Audit reference (fails Studionet consensus) |
| Fallback | open.er-api.com BOB/PEN | `MARKET_AGGREGATE` | **Live benchmark** |
| Error | Both unavailable | — | No lock delivered, trade stays RATE_PENDING |

**Relayer policy:** Try primary → if MAJORITY_DISAGREE, immediately retry fallback. No manual intervention. Benchmark type is recorded on-chain per event.

---

## Validator Consensus Model

- **Protocol:** `strict_eq` (GenLayer)
- **Validators:** 5 nodes on Studionet
- **Threshold:** MAJORITY_AGREE (3/5 minimum)
- **Rounding:** `round(rate, 3)` — 10 bps deterministic bucket
- **No LLM in the numeric path** — arithmetic comparison only
- **Primary failure pattern:** BCRP API has intermittent reachability from some Studionet validators → 2–3/5 disagree consistently

---

## State Machine (TradeFxSettlement.sol)

```
DRAFT → RATE_PENDING → RATE_LOCKED → SETTLED
                              ↓
                      PARTIAL_RESIZED
                              ↓
                       ROLL_PENDING → ROLLED → SETTLED
                                         ↓
                                   (next roll...)
               + CANCELLED (any pre-settled state)
```

Exception handling: `exceptionFlagged` + `exceptionPaused` are **orthogonal bool flags**, not status branches. Lifecycle continues unless admin explicitly pauses.

---

## Validated Demo Flow (zero manual intervention)

1. `npm run deploy` → emits `artifacts/deployment.json` + `artifacts/deployment.env`
2. `cast send $TRADE "requestRateLock()"` → emits `RateLockRequested`
3. `node scripts/fx-settlement-relayer.mjs lock $TRADE` → GenLayer consensus → `receiveRate()` on Base Sepolia
4. `cast send $TRADE "requestRoll(uint256)" $NEW_DUE_UNIX` → emits `RollRequested`
5. `node scripts/fx-settlement-relayer.mjs roll $TRADE 2026-05-05` → GenLayer consensus → `receiveRolledRate()` on Base Sepolia
6. `cast call $TRADE "getSummary()(uint8,uint256,uint256,uint256,uint256,uint256,bool)"` → verifies final state

**Verified on 2026-03-06. Rate lock tx:** `0x1298bbabfe992f144db5a72c3ba1444f7d13beb868f694a215a6c77c10560b5d`  
**Roll tx:** `0x4a626e445dc1d1e036aea72833aaeccdc6e73546db4035065131b8a86c951533`

---

## Repository

- **GitHub:** https://github.com/acastellana/trade-finance-genlayer
- **Frontend:** https://acastellana.github.io/trade-finance-genlayer/
- **Commit at snapshot:** `062cfe1` (master→main push, 2026-03-06)

---

## What to build next (when resuming)

1. Record canonical 90-second demo (create → lock → roll → final state)
2. Add "what this is not" section to frontend
3. Tighten architecture page on the frontend
4. Decision: BCRP proxy infrastructure (upgrade path, not current blocker)

## What not to build next

- Do not add exception handling UI unless explicitly requested
- Do not expand into trade document handling, cargo, or dispute flows
- Do not add more benchmark sources until BCRP proxy decision is made
- Do not reintroduce InternetCourt framing
