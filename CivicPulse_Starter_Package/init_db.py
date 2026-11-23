"""
Civic Connects - Database Initialization & Verification Utility
Can be executed directly via: python init_db.py
"""

import os
import sys
from config import Config
from db import init_schema, get_db_mode, execute_query

def main():
    print("="*65)
    print("   CIVIC CONNECTS - DATABASE SETUP & SEED VERIFIER")
    print("="*65)

    print(f"Target Database: {Config.DB_NAME}")
    print(f"MySQL Host: {Config.DB_HOST}:{Config.DB_PORT} (User: {Config.DB_USER})")

    # Run Schema initialization
    print("\n[1/3] Initializing schema and seed records...")
    init_schema()

    active_mode = get_db_mode()
    print(f"[2/3] Active Database Mode: {active_mode.upper()}")
    if active_mode == 'mysql':
        print("      -> Connected to live MySQL database server!")
    else:
        print("      -> Using local zero-dependency database engine (SQLite).")
        print("      -> To switch to live MySQL: start XAMPP MySQL / MariaDB service.")

    # Verify data counts
    print("\n[3/3] Verifying database records:")
    try:
        user_count = execute_query("SELECT COUNT(*) AS c FROM users", one=True)['c']
        dept_count = execute_query("SELECT COUNT(*) AS c FROM departments", one=True)['c']
        complaint_count = execute_query("SELECT COUNT(*) AS c FROM complaints", one=True)['c']
        log_count = execute_query("SELECT COUNT(*) AS c FROM complaint_logs", one=True)['c']

        print(f"      - Users seeded:       {user_count}")
        print(f"      - Departments seeded: {dept_count}")
        print(f"      - Complaints seeded:  {complaint_count}")
        print(f"      - Audit logs seeded:  {log_count}")
        print("\n[SUCCESS] Civic Connects database initialized and ready for production use.")
    except Exception as e:
        print(f"\n[ERROR] Database verification failed: {e}")
        sys.exit(1)

    print("="*65)
    print("Run the web application with:")
    print("   python app.py")
    print("="*65)

if __name__ == '__main__':
    main()
