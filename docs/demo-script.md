# Demo Script — 90 Seconds

**Demo trade:** QC-COOP-2026-0002  
**Contract:** `0x212644D91A68fdCBa8AA103944f6A5535D96AdF4` (Base Sepolia)  
**Oracle:** `0x3B8501bAcaB70dedbC6f8B8EFCB888ba66cbc73e` (GenLayer Studionet)

---

## Scene 1 — Create Trade (0:00–0:15)

Open the settlement console (or run `status`).

```bash
GL_ORACLE_ADDRESS=0x3B8501bAcaB70dedbC6f8B8EFCB888ba66cbc73e \
RELAYER_KEY=$(cat base-sepolia/.wallets/relayer.key) \
GL_PRIVATE_KEY=$(cat ~/.internetcourt/.exporter_key) \
node scripts/fx-settlement-relayer.mjs status 0x212644D91A68fdCBa8AA103944f6A5535D96AdF4
```

Show on screen:
- status: RATE_PENDING
- invoice: 150,000 BOB
- ref: QC-COOP-2026-0002
- due: 2026-04-05

---

## Scene 2 — Request Rate Lock (0:15–0:30)

```bash
~/.foundry/bin/cast send 0x212644D91A68fdCBa8AA103944f6A5535D96AdF4 \
  "requestRateLock()" \
  --rpc-url https://sepolia.base.org \
  --private-key $(cat ~/.internetcourt/.exporter_key)
```

Show: `status 1 (success)` · `RateLockRequested` event emitted.

---

## Scene 3 — Benchmark Lock (0:30–1:00)

```bash
GL_ORACLE_ADDRESS=0x3B8501bAcaB70dedbC6f8B8EFCB888ba66cbc73e \
RELAYER_KEY=$(cat base-sepolia/.wallets/relayer.key) \
GL_PRIVATE_KEY=$(cat ~/.internetcourt/.exporter_key) \
BASE_SEPOLIA_RPC=https://sepolia.base.org \
node scripts/fx-settlement-relayer.mjs lock 0x212644D91A68fdCBa8AA103944f6A5535D96AdF4
```

Show in output:
- `request_rate_lock_primary` → MAJORITY_DISAGREE → fallback
- `request_rate_lock_fallback` → MAJORITY_AGREE
- benchmark: MARKET_AGGREGATE · MARKET-20260306
- rate_18: 493000000000000000
- `receiveRate()` delivered ✅

---

## Scene 4 — Final State After Lock (1:00–1:15)

```bash
~/.foundry/bin/cast call 0x212644D91A68fdCBa8AA103944f6A5535D96AdF4 \
  "getSummary()(uint8,uint256,uint256,uint256,uint256,uint256,bool)" \
  --rpc-url https://sepolia.base.org
```

Show:
- status: 2 (RATE_LOCKED)
- invoice: 150000000000000000000000
- settlement: 73950000000000000000000 → **73,950 PEN**

---

## Scene 5 — Extend Hedge / Roll (1:15–1:40)

```bash
~/.foundry/bin/cast send 0x212644D91A68fdCBa8AA103944f6A5535D96AdF4 \
  "requestRoll(uint256)" 1778008395 \
  --rpc-url https://sepolia.base.org \
  --private-key $(cat ~/.internetcourt/.exporter_key)
```

Then:
```bash
GL_ORACLE_ADDRESS=0x3B8501bAcaB70dedbC6f8B8EFCB888ba66cbc73e \
RELAYER_KEY=$(cat base-sepolia/.wallets/relayer.key) \
GL_PRIVATE_KEY=$(cat ~/.internetcourt/.exporter_key) \
BASE_SEPOLIA_RPC=https://sepolia.base.org \
node scripts/fx-settlement-relayer.mjs roll \
  0x212644D91A68fdCBa8AA103944f6A5535D96AdF4 2026-05-05
```

Show: `receiveRolledRate()` delivered ✅ · new_due=2026-05-05 · roll_cost=0

---

## Scene 6 — Final State (1:40–1:50)

```bash
~/.foundry/bin/cast call 0x212644D91A68fdCBa8AA103944f6A5535D96AdF4 \
  "getSummary()(uint8,uint256,uint256,uint256,uint256,uint256,bool)" \
  --rpc-url https://sepolia.base.org
```

Show:
- **status: 5 (ROLLED)**
- invoice: 150,000 BOB
- settlement: 73,950 PEN
- due: 2026-05-05
- roll_count: 1
- exception: false

Stop recording.

---

## Recording checklist

- [ ] Terminal font ≥ 16px, dark background
- [ ] No browser tabs, notifications, or toolbars visible
- [ ] No narration — commands and output speak for themselves
- [ ] Target: 90 seconds total
- [ ] Export as MP4 (H.264) at 1920×1080 or 1280×720
