# Data

No confidential company data. One coherent synthetic IR world (not unrelated CSVs).

## `synthetic/`

Logical model (see `docs/implementation_plan.md` §4)—**not** the proposal `bookings` draft:

- Members (`member_id`; tiers Tier 1 entry → Tier 3 = VIP)
- Outlets (`pillar` + `operating_model`; leased outlets exist for voucher redemption, not POS)
- Hotel facts (room nights, net room; `member_id` nullable)
- Self-op transactions only (`fb_self_op` / `retail_self_op` / `hotel_other` incl. IRD & breakage)
- Wallet-cash events (incl. unidentified)
- Points ledger (generator 1:1; redemption ≠ revenue ≠ wallet cash)
- Voucher issue/redeem (paid / comp / package; standalone shares same event model)
- Tenant-reported redemption **counts** only (no amount / GMV)
- Package header + components; self-op folio path
- Campaigns + contacts (observational)
- **No** tenant POS / tenant GMV tables

Physical DDL and generator: work-plan I2 (WP-201+). Generated DB files under `generated/` are gitignored.

## `documents/`

Approved unstructured knowledge for knowledge / conflict tests:

- Definitions aligned with semantic YAML
- Observational campaign brief
- Prompt-injection sample (data, not instructions)
- VIP conflict doc (VIP ≠ Tier 3) for `DEFINITION_CONFLICT`
