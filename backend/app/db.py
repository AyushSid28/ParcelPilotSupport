from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from app.clock import IST
from app.paths import DB_PATH, SOURCE_DIR

XLSX = SOURCE_DIR / "ParcelPilot_Assessment_Data.xlsx"

SCHEMA = """
CREATE TABLE accounts (
  account_id TEXT PRIMARY KEY,
  account_name TEXT NOT NULL,
  plan TEXT NOT NULL,
  status TEXT NOT NULL,
  csm TEXT NOT NULL,
  contract_file TEXT,
  premium_support INTEGER NOT NULL,
  notes TEXT NOT NULL
);

CREATE TABLE orders (
  order_id TEXT PRIMARY KEY,
  account_id TEXT NOT NULL REFERENCES accounts(account_id),
  carrier TEXT NOT NULL,
  status TEXT NOT NULL,
  booked_at TEXT NOT NULL,
  pickup_window_start TEXT NOT NULL,
  pickup_window_end TEXT NOT NULL,
  pickup_actual_at TEXT,
  shipment_fee_inr REAL NOT NULL,
  carrier_fault INTEGER,
  customer_fault INTEGER,
  cancellation_requested_at TEXT,
  notes TEXT NOT NULL
);

CREATE TABLE tickets (
  ticket_id TEXT PRIMARY KEY,
  account_id TEXT NOT NULL REFERENCES accounts(account_id),
  created_at TEXT NOT NULL,
  status TEXT NOT NULL,
  subject TEXT NOT NULL,
  description TEXT NOT NULL,
  channel TEXT NOT NULL,
  assigned_to TEXT NOT NULL,
  last_customer_message_at TEXT,
  historical_resolution TEXT
);

CREATE TABLE doc_chunks (
  id INTEGER PRIMARY KEY,
  doc_id TEXT NOT NULL,
  filename TEXT NOT NULL,
  title TEXT NOT NULL,
  doc_type TEXT NOT NULL,
  status TEXT NOT NULL,
  authority INTEGER NOT NULL,
  account_id TEXT,
  heading TEXT,
  body TEXT NOT NULL
);

CREATE TABLE proposals (
  id TEXT PRIMARY KEY,
  actor_kind TEXT NOT NULL,
  account_id TEXT,
  staff_id TEXT,
  action_type TEXT NOT NULL,
  payload TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE escalations (
  id TEXT PRIMARY KEY,
  ticket_id TEXT,
  account_id TEXT,
  reason TEXT NOT NULL,
  priority TEXT NOT NULL,
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE ticket_updates (
  id TEXT PRIMARY KEY,
  ticket_id TEXT NOT NULL,
  note TEXT NOT NULL,
  new_status TEXT,
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE tasks (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  account_id TEXT,
  related_id TEXT,
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE audit_log (
  id INTEGER PRIMARY KEY,
  at TEXT NOT NULL,
  actor TEXT NOT NULL,
  event TEXT NOT NULL,
  detail TEXT NOT NULL
);
"""


def connect(path: Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ts(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=IST)
        return dt.isoformat()
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    dt = datetime.strptime(text, "%Y-%m-%d %H:%M").replace(tzinfo=IST)
    return dt.isoformat()


def _flag(value) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return 1 if bool(value) else 0


def _str(value) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None


def rebuild(path: Path | None = None) -> sqlite3.Connection:
    db_path = path or DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    conn = connect(db_path)
    conn.executescript(SCHEMA)

    accounts = pd.read_excel(XLSX, sheet_name="accounts")
    for _, row in accounts.iterrows():
        conn.execute(
            """INSERT INTO accounts VALUES (?,?,?,?,?,?,?,?)""",
            (
                row["account_id"],
                row["account_name"],
                row["plan"],
                row["status"],
                row["csm"],
                _str(row.get("contract_file")),
                1 if bool(row["premium_support"]) else 0,
                row["notes"],
            ),
        )

    orders = pd.read_excel(XLSX, sheet_name="orders")
    for _, row in orders.iterrows():
        conn.execute(
            """INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                row["order_id"],
                row["account_id"],
                row["carrier"],
                row["status"],
                _ts(row["booked_at"]),
                _ts(row["pickup_window_start"]),
                _ts(row["pickup_window_end"]),
                _ts(row["pickup_actual_at"]),
                float(row["shipment_fee_inr"]),
                _flag(row["carrier_fault"]),
                _flag(row["customer_fault"]),
                _ts(row["cancellation_requested_at"]),
                row["notes"],
            ),
        )

    tickets = pd.read_excel(XLSX, sheet_name="tickets")
    for _, row in tickets.iterrows():
        conn.execute(
            """INSERT INTO tickets VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                row["ticket_id"],
                row["account_id"],
                _ts(row["created_at"]),
                row["status"],
                row["subject"],
                row["description"],
                row["channel"],
                row["assigned_to"],
                _ts(row["last_customer_message_at"]),
                _str(row.get("historical_resolution")),
            ),
        )

    conn.commit()
    return conn
