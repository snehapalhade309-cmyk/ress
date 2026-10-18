"""
ResQAI - Command Center Application Runner
Entry point to launch the complete local-first emergency response platform.
"""

import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.database import init_db
from backend.seed_data import seed_database
from backend.app import app

def main():
    print("=" * 70)
    print("  RESQAI — EMERGENCY MANAGEMENT & RESPONSE SYSTEM")
    print("  Local-First Tactical Command Center & Decision-Support Platform")
    print("=" * 70)

    # 1. Initialize SQLite Database Schema
    print("[1/3] Initializing SQLite database schema...")
    init_db()

    # 2. Seed Realistic Scenario Dataset if Empty
    print("[2/3] Checking dataset status...")
    seed_res = seed_database(force_reset=False)
    if seed_res.get('seeded'):
        print("      -> Initial emergency dataset seeded.")
    else:
        print("      -> Existing database verified.")

    # 3. Launch Flask REST API and SPA Static Server
    port = int(os.environ.get('PORT', 5000))
    print(f"[3/3] Launching web server on http://127.0.0.1:{port}")
    print("=" * 70)
    print(f"  COMMAND CENTER READY: Open your browser at http://127.0.0.1:{port}")
    print("  Press Ctrl+C to terminate.")
    print("=" * 70)

    app.run(host='127.0.0.1', port=port, debug=False)

if __name__ == '__main__':
    main()
