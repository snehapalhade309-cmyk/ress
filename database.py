"""
ResQAI - Database Layer (SQLite)
Provides thread-safe connection pooling, schema initialization, and transactional operations.
"""

import sqlite3
import os
import json
from contextlib import contextmanager

# Ensure data directory exists
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, 'resqai.db')


def get_connection():
    """Create a new SQLite connection with foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")  # Write-Ahead Logging for high concurrency
    return conn


@contextmanager
def get_db():
    """Context manager for database connections with automatic commit/rollback."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_db():
    """Initialize database tables and indexes."""
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Incidents Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_code TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            location_name TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            reported_severity TEXT NOT NULL,
            affected_people INTEGER DEFAULT 0,
            vulnerability_tags TEXT DEFAULT '[]',
            description TEXT,
            reporter_name TEXT,
            reporter_contact TEXT,
            calculated_risk_score REAL DEFAULT 0.0,
            risk_category TEXT DEFAULT 'Low',
            risk_factors_json TEXT DEFAULT '{}',
            status TEXT DEFAULT 'reported',
            is_demo INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        ''')

        # 2. Resources Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            capabilities TEXT DEFAULT '[]',
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            base_station TEXT NOT NULL,
            status TEXT DEFAULT 'available',
            assigned_incident_id INTEGER NULL,
            last_status_update TEXT NOT NULL,
            is_simulated INTEGER DEFAULT 1,
            FOREIGN KEY(assigned_incident_id) REFERENCES incidents(id) ON DELETE SET NULL
        )
        ''')

        # 3. Shelters Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS shelters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shelter_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            address TEXT NOT NULL,
            total_capacity INTEGER NOT NULL,
            current_occupancy INTEGER DEFAULT 0,
            amenities TEXT DEFAULT '[]',
            verification_status TEXT DEFAULT 'verified',
            contact_phone TEXT,
            updated_at TEXT NOT NULL
        )
        ''')

        # 4. Dispatches Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS dispatches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id INTEGER NOT NULL,
            resource_id INTEGER NOT NULL,
            dispatch_time TEXT NOT NULL,
            arrival_time TEXT,
            resolution_time TEXT,
            status TEXT DEFAULT 'dispatched',
            notes TEXT,
            dispatched_by TEXT DEFAULT 'ResQAI Dispatcher',
            FOREIGN KEY(incident_id) REFERENCES incidents(id) ON DELETE CASCADE,
            FOREIGN KEY(resource_id) REFERENCES resources(id) ON DELETE CASCADE
        )
        ''')

        # 5. Alerts Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            severity TEXT NOT NULL,
            incident_id INTEGER NULL,
            source TEXT NOT NULL,
            is_acknowledged INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY(incident_id) REFERENCES incidents(id) ON DELETE SET NULL
        )
        ''')

        # 6. Audit Logs Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id INTEGER,
            details TEXT,
            timestamp TEXT NOT NULL,
            actor TEXT DEFAULT 'operator'
        )
        ''')

        # Create indexes for fast filtering
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_incidents_type ON incidents(type);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_incidents_risk ON incidents(risk_category);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_resources_status ON resources(status);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_resources_type ON resources(type);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_ack ON alerts(is_acknowledged);')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_logs(timestamp);')


def row_to_dict(row):
    """Utility to convert a sqlite3.Row object to a standard Python dictionary."""
    if row is None:
        return None
    d = dict(row)
    # Parse JSON fields if present
    for json_col in ['vulnerability_tags', 'capabilities', 'amenities']:
        if json_col in d and isinstance(d[json_col], str):
            try:
                d[json_col] = json.loads(d[json_col])
            except Exception:
                d[json_col] = []
    if 'risk_factors_json' in d and isinstance(d['risk_factors_json'], str):
        try:
            d['risk_factors_json'] = json.loads(d['risk_factors_json'])
        except Exception:
            d['risk_factors_json'] = {}
    return d
