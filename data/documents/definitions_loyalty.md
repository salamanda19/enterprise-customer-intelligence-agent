# Loyalty and revenue definitions (aligned with config/semantic.yaml / SSOT)

## Customer
In this property, **customer** means a **loyalty member** with a stable `member_id`.
It does not mean all visitors or all hotel guests.

## VIP
**VIP** means **Tier 3**, the highest loyalty tier (Tier 1 is entry; Tier 2 is mid).
VIP is not the same as a high-value member, and not the same as a hotel-list VIP.

## High-value member
A high-value member is a member whose IR wallet cash over the past 12 months exceeds the
threshold stored in the semantic layer. This is independent of tier / VIP.

## Active member
A member is active if they have at least one **wallet cash to IR** event in the past 90 days.
Tenant voucher redemptions, points redemptions, and comp vouchers do **not** qualify.

## Revenue buckets
- Hotel pillar total = net room revenue + hotel other (includes in-room dining and breakage).
- F&B revenue = self-operated F&B only (excludes IRD and tenant restaurant GMV).
- Retail revenue = self-operated retail only (excludes tenant GMV and voucher face as GMV).

## Vouchers
Voucher redemption face value is not tenant GMV and is not automatically IR retail/F&B revenue
when redeemed at a leased outlet.
