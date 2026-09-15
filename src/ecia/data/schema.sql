-- Synthetic IR analytical schema (SSOT / implementation_plan §4).
-- No tenant POS / tenant GMV tables.

CREATE TABLE members (
  member_id VARCHAR PRIMARY KEY,
  join_date DATE NOT NULL,
  tier VARCHAR NOT NULL CHECK (tier IN ('Tier 1', 'Tier 2', 'Tier 3')),
  external_loyalty_key VARCHAR  -- reserved; always NULL this version
);

CREATE TABLE outlets (
  outlet_id VARCHAR PRIMARY KEY,
  outlet_name VARCHAR NOT NULL,
  pillar VARCHAR NOT NULL CHECK (pillar IN ('fb', 'retail', 'hotel')),
  operating_model VARCHAR NOT NULL CHECK (operating_model IN ('self_op', 'leased'))
);

CREATE TABLE stays (
  stay_id VARCHAR PRIMARY KEY,
  property_id VARCHAR NOT NULL,
  member_id VARCHAR,           -- NULL = unidentified member link
  guest_token VARCHAR NOT NULL, -- distinct hotel-guest identity for counting
  check_in DATE NOT NULL,
  check_out DATE NOT NULL,
  nights INTEGER NOT NULL,
  net_room_revenue DOUBLE NOT NULL,
  cancelled BOOLEAN NOT NULL,
  package_id VARCHAR
);

CREATE TABLE self_op_transactions (
  txn_id VARCHAR PRIMARY KEY,
  outlet_id VARCHAR NOT NULL,
  member_id VARCHAR,
  guest_token VARCHAR,
  txn_date DATE NOT NULL,
  revenue_bucket VARCHAR NOT NULL
    CHECK (revenue_bucket IN ('fb_self_op', 'retail_self_op', 'hotel_other')),
  amount DOUBLE NOT NULL,
  payment_path VARCHAR NOT NULL
    CHECK (payment_path IN (
      'pos', 'folio', 'voucher_redeem_self_op', 'breakage', 'package_component'
    )),
  stay_id VARCHAR,
  voucher_id VARCHAR,
  package_id VARCHAR
);

CREATE TABLE wallet_cash_events (
  event_id VARCHAR PRIMARY KEY,
  member_id VARCHAR,  -- NULL = unidentified IR cash
  event_date DATE NOT NULL,
  amount DOUBLE NOT NULL,
  source_type VARCHAR NOT NULL
    CHECK (source_type IN (
      'stay_settlement', 'pos', 'package_purchase', 'voucher_purchase', 'folio_settlement'
    )),
  source_id VARCHAR NOT NULL
);

CREATE TABLE points_ledger (
  entry_id VARCHAR PRIMARY KEY,
  member_id VARCHAR NOT NULL,
  event_date DATE NOT NULL,
  points DOUBLE NOT NULL,
  kind VARCHAR NOT NULL CHECK (kind IN ('earn', 'redeem')),
  related_wallet_event_id VARCHAR
);

CREATE TABLE vouchers (
  voucher_id VARCHAR PRIMARY KEY,
  funding_source VARCHAR NOT NULL
    CHECK (funding_source IN ('paid_standalone', 'paid_package', 'comp')),
  face_value DOUBLE NOT NULL,
  issued_date DATE NOT NULL,
  member_id VARCHAR,
  package_id VARCHAR,
  wallet_cash_event_id VARCHAR,
  status VARCHAR NOT NULL CHECK (status IN ('open', 'redeemed', 'expired'))
);

CREATE TABLE voucher_redemptions (
  redemption_id VARCHAR PRIMARY KEY,
  voucher_id VARCHAR NOT NULL,
  outlet_id VARCHAR NOT NULL,
  redeemed_date DATE NOT NULL,
  face_amount DOUBLE NOT NULL,
  member_id VARCHAR
);

-- Count only — never an amount / GMV column (D35 / I18)
CREATE TABLE tenant_reported_redemption_counts (
  report_id VARCHAR PRIMARY KEY,
  outlet_id VARCHAR NOT NULL,
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  redemption_count INTEGER NOT NULL
);

CREATE TABLE packages (
  package_id VARCHAR PRIMARY KEY,
  sold_date DATE NOT NULL,
  member_id VARCHAR,
  cash_received DOUBLE NOT NULL,
  wallet_cash_event_id VARCHAR NOT NULL,
  label VARCHAR NOT NULL
);

CREATE TABLE package_components (
  component_id VARCHAR PRIMARY KEY,
  package_id VARCHAR NOT NULL,
  component_type VARCHAR NOT NULL
    CHECK (component_type IN (
      'room', 'ird', 'fb_self_op', 'retail_self_op', 'tenant_meal', 'shopping_voucher'
    )),
  outlet_id VARCHAR,
  face_or_ssp DOUBLE NOT NULL,
  recognition VARCHAR NOT NULL
    CHECK (recognition IN ('ir_revenue', 'liability', 'hotel_other')),
  recognized_amount DOUBLE NOT NULL,
  status VARCHAR NOT NULL
    CHECK (status IN ('pending', 'recognized', 'broken', 'settled_liability'))
);

CREATE TABLE campaigns (
  campaign_id VARCHAR PRIMARY KEY,
  campaign_name VARCHAR NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  co_brand_outlet_id VARCHAR,
  is_randomized BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE campaign_contacts (
  contact_id VARCHAR PRIMARY KEY,
  campaign_id VARCHAR NOT NULL,
  member_id VARCHAR NOT NULL,
  contacted_date DATE NOT NULL
);

CREATE TABLE meta (
  key VARCHAR PRIMARY KEY,
  value VARCHAR NOT NULL
);
