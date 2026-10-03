-- Yamlr Licensing Gateway: Database Schema
-- Goal: Minimal, anonymized telemetry and license state persistence.

CREATE TABLE IF NOT EXISTS pulses (
  id             TEXT    PRIMARY KEY,
  cli_version    TEXT    NOT NULL,
  event_type     TEXT    NOT NULL,
  dna_score_delta REAL,
  ts             INTEGER NOT NULL
);

-- Performance Indexes for large-scale telemetry analysis
CREATE INDEX IF NOT EXISTS idx_pulses_ts ON pulses(ts);
CREATE INDEX IF NOT EXISTS idx_pulses_event ON pulses(event_type);

CREATE TABLE IF NOT EXISTS organizations (
  id             TEXT    PRIMARY KEY,
  name           TEXT    NOT NULL,
  stripe_customer_id TEXT,
  seat_count     INTEGER DEFAULT 1,
  created_at     INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS licenses (
  clerk_user_id  TEXT    PRIMARY KEY,
  email          TEXT    NOT NULL,
  plan           TEXT    NOT NULL DEFAULT 'free',
  machine_id     TEXT,   -- Bound to Machine Fingerprint
  organization_id TEXT,  -- For Team/Enterprise licensing
  activated_at   INTEGER,
  updated_at     INTEGER NOT NULL
);

-- Canonical tier grants are independent of workstation identity. Team records
-- represent one named developer seat; Enterprise records represent an org grant.
CREATE TABLE IF NOT EXISTS license_grants (
  subject_id      TEXT    PRIMARY KEY,
  subject_kind    TEXT    NOT NULL CHECK (subject_kind IN ('developer', 'organization')),
  organization_id TEXT    NOT NULL,
  plan            TEXT    NOT NULL CHECK (plan IN ('team', 'enterprise')),
  seat_count      INTEGER,
  node_count      INTEGER,
  status          TEXT    NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'revoked')),
  expires_at      INTEGER NOT NULL,
  updated_at      INTEGER NOT NULL,
  CHECK (seat_count IS NULL OR seat_count > 0),
  CHECK (node_count IS NULL OR node_count > 0),
  CHECK (plan != 'enterprise' OR seat_count IS NOT NULL OR node_count IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_license_grants_org ON license_grants(organization_id);
CREATE INDEX IF NOT EXISTS idx_license_grants_status_expiry ON license_grants(status, expires_at);

-- Yamlr owns account and organization membership; OIDC supplies verified identity.
CREATE TABLE IF NOT EXISTS identities (
  issuer         TEXT NOT NULL,
  subject        TEXT NOT NULL,
  email          TEXT NOT NULL,
  email_verified INTEGER NOT NULL CHECK (email_verified IN (0, 1)),
  updated_at     INTEGER NOT NULL,
  PRIMARY KEY (issuer, subject)
);

CREATE INDEX IF NOT EXISTS idx_identities_email ON identities(email);

CREATE TABLE IF NOT EXISTS oidc_login_requests (
  state_hash TEXT PRIMARY KEY,
  nonce      TEXT NOT NULL,
  verifier   TEXT NOT NULL,
  expires_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_oidc_login_expiry ON oidc_login_requests(expires_at);

CREATE TABLE IF NOT EXISTS web_sessions (
  token_hash TEXT PRIMARY KEY,
  issuer     TEXT NOT NULL,
  subject    TEXT NOT NULL,
  expires_at INTEGER NOT NULL,
  created_at INTEGER NOT NULL,
  FOREIGN KEY (issuer, subject) REFERENCES identities(issuer, subject)
);

CREATE INDEX IF NOT EXISTS idx_web_sessions_expiry ON web_sessions(expires_at);

CREATE TABLE IF NOT EXISTS team_memberships (
  organization_id TEXT NOT NULL,
  issuer          TEXT NOT NULL,
  subject         TEXT NOT NULL,
  email           TEXT NOT NULL,
  role            TEXT NOT NULL CHECK (role IN ('admin', 'member')),
  has_seat        INTEGER NOT NULL DEFAULT 0 CHECK (has_seat IN (0, 1)),
  revoked_at      INTEGER,
  created_at      INTEGER NOT NULL,
  PRIMARY KEY (organization_id, issuer, subject),
  FOREIGN KEY (organization_id) REFERENCES organizations(id),
  FOREIGN KEY (issuer, subject) REFERENCES identities(issuer, subject)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_team_memberships_active_email ON team_memberships(organization_id, email) WHERE revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_team_memberships_identity ON team_memberships(issuer, subject);

CREATE TABLE IF NOT EXISTS team_invitations (
  token_hash      TEXT PRIMARY KEY,
  organization_id TEXT NOT NULL,
  email           TEXT NOT NULL,
  invited_by      TEXT NOT NULL,
  expires_at      INTEGER NOT NULL,
  accepted_at     INTEGER,
  accepted_issuer TEXT,
  accepted_sub    TEXT,
  revoked_at      INTEGER,
  created_at      INTEGER NOT NULL,
  FOREIGN KEY (organization_id) REFERENCES organizations(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_team_invitations_pending_email ON team_invitations(organization_id, email) WHERE accepted_at IS NULL AND revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_team_invitations_org ON team_invitations(organization_id, expires_at);

CREATE TABLE IF NOT EXISTS team_billing (
  organization_id       TEXT PRIMARY KEY,
  stripe_subscription_id TEXT UNIQUE NOT NULL,
  status                TEXT NOT NULL CHECK (status IN ('active', 'past_due', 'canceled', 'suspended')),
  current_period_end    INTEGER NOT NULL,
  grace_until           INTEGER,
  updated_at            INTEGER NOT NULL,
  FOREIGN KEY (organization_id) REFERENCES organizations(id)
);

CREATE TABLE IF NOT EXISTS team_billing_events (
  event_id       TEXT PRIMARY KEY,
  organization_id TEXT NOT NULL,
  event_type     TEXT NOT NULL,
  created_at     INTEGER NOT NULL,
  status         TEXT NOT NULL CHECK (status IN ('processing', 'processed')),
  FOREIGN KEY (organization_id) REFERENCES organizations(id)
);

CREATE INDEX IF NOT EXISTS idx_team_billing_events_order
  ON team_billing_events(organization_id, created_at, event_id);

-- Immutable audit log for license events
CREATE TABLE IF NOT EXISTS license_events (
  event_id       TEXT    PRIMARY KEY,
  user_id        TEXT    NOT NULL,
  machine_id     TEXT,
  event_type     TEXT    NOT NULL, -- LOGIN, SYNC, UPGRADE, REVOKE
  metadata       TEXT,    -- JSON event metadata
  ts             INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_license_events_user ON license_events(user_id);
CREATE INDEX IF NOT EXISTS idx_license_events_ts ON license_events(ts);
