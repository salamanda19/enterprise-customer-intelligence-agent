# Conflicting VIP definition (for DEFINITION_CONFLICT tests)

## VIP
For hotel operations reporting, **VIP** means any guest on the front-desk courtesy list,
regardless of loyalty tier. High spenders in the last 30 days may also be labeled VIP.

This definition intentionally conflicts with the semantic layer (VIP = Tier 3).
When both this document and the semantic layer are retrieved, the system must **refuse to
pick a side** and emit `DEFINITION_CONFLICT`.
