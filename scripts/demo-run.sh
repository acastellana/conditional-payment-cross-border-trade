#!/usr/bin/env bash
# demo-run.sh — QC-COOP-2026-DEMO · 90-second recording
# Usage: asciinema rec demo.cast -c "bash scripts/demo-run.sh"
#
# SKIP_PRIMARY_BENCHMARK=1 goes straight to market aggregate (skip 44s BCRP wait)
# The hierarchy exists in production; BCRP is the primary, market aggregate is the fallback.

TRADE=0xd0d6824eefd2Db3902125De207DCC8f3eB5Bb84C
ORACLE=0x3B8501bAcaB70dedbC6f8B8EFCB888ba66cbc73e
RPC=https://sepolia.base.org
CAST=~/.foundry/bin/cast
DEPLOYER_KEY=$(cat ~/.internetcourt/.exporter_key)

export GL_PRIVATE_KEY=$DEPLOYER_KEY
export RELAYER_KEY=$(cat ~/clawd/projects/trade-finance-genlayer/base-sepolia/.wallets/relayer.key)
export GL_ORACLE_ADDRESS=$ORACLE
export BASE_SEPOLIA_RPC=$RPC
export SKIP_PRIMARY_BENCHMARK=1

cd ~/clawd/projects/trade-finance-genlayer

# ─── Scene 1: Trade created, awaiting rate lock ────────────────────────────
clear
echo ""
node scripts/fx-settlement-relayer.mjs status $TRADE
sleep 3

# ─── Scene 2: Request rate lock ────────────────────────────────────────────
echo ""
echo "  $ cast send requestRateLock()"
echo ""
sleep 1

$CAST send $TRADE "requestRateLock()" \
  --rpc-url $RPC \
  --private-key $DEPLOYER_KEY \
  2>&1 | grep -E "status\s+|transactionHash"

sleep 2

# ─── Scene 3: Relayer delivers benchmark ───────────────────────────────────
echo ""
echo "  $ node fx-settlement-relayer.mjs lock"
echo ""
sleep 1

node scripts/fx-settlement-relayer.mjs lock $TRADE

sleep 2

# ─── Scene 4: Settlement amount locked ─────────────────────────────────────
echo ""
node scripts/fx-settlement-relayer.mjs status $TRADE
sleep 3

# ─── Scene 5: Extend due date ──────────────────────────────────────────────
echo ""
echo "  $ cast send requestRoll()  2026-04-05 → 2026-05-05"
echo ""
sleep 1

$CAST send $TRADE "requestRoll(uint256)" 1778008395 \
  --rpc-url $RPC \
  --private-key $DEPLOYER_KEY \
  2>&1 | grep -E "status\s+|transactionHash"

sleep 1

echo ""
echo "  $ node fx-settlement-relayer.mjs roll"
echo ""
sleep 1

node scripts/fx-settlement-relayer.mjs roll $TRADE 2026-05-05

sleep 2

# ─── Scene 6: Final state ──────────────────────────────────────────────────
echo ""
node scripts/fx-settlement-relayer.mjs status $TRADE
sleep 4
