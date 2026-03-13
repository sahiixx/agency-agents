-- schema.sql — The Agency D1 database
-- Run: wrangler d1 execute agency-traces --file=schema.sql

CREATE TABLE IF NOT EXISTS mission_traces (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  mission_id   TEXT    NOT NULL,
  goal         TEXT    NOT NULL,
  preset       TEXT    NOT NULL DEFAULT 'full',
  verdict      TEXT    NOT NULL,
  agents       TEXT    NOT NULL,
  tokens_in    INTEGER NOT NULL DEFAULT 0,
  tokens_out   INTEGER NOT NULL DEFAULT 0,
  cost_usd     REAL    NOT NULL DEFAULT 0,
  surprise     REAL    NOT NULL DEFAULT 0.5,
  created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_traces_created ON mission_traces(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_traces_verdict  ON mission_traces(verdict);
