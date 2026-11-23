"""
Civic Connects - Database Initialization & Verification Utility
Safe for repeated execution on both TiDB Cloud / MySQL and local SQLite.
Run directly via:
    python init_db.py
"""

import os
import sys
from config import Config
from db import init_schema, get_db_mode, execute_query, verify_connection

def main():
    print("=" * 70)
    print("       CIVIC CONNECTS - DATABASE SETUP & SEED VERIFIER")
    print("=" * 70)

    mode = getattr(Config, 'DB_MODE', getattr(Config, 'DB_ENGINE', 'auto')).lower()
    print(f"Configured Database Engine: {mode.upper()}")
    print(f"Target Database Name:      {Config.DB_NAME}")
    if mode != 'sqlite':
        print(f"Target Host / Port:        {Config.DB_HOST}:{Config.DB_PORT}")
        print(f"Database User:             {Config.DB_USER}")
        print(f"TLS/SSL Encryption:        {'Enabled (Required for TiDB Cloud)' if (Config.DB_SSL or Config.DB_PORT == 4000 or Config.IS_PRODUCTION or 'tidbcloud.com' in Config.DB_HOST.lower()) else 'Disabled/Local'}")

    # Step 1: Verify Connection
    print("\n[1/3] Testing database connection...")
    try:
        active_mode = get_db_mode()
        verify_connection()
        print(f"      -> Connection successful! Active engine: {active_mode.upper()}")
    except Exception as conn_err:
        print(f"\n[CRITICAL ERROR] Could not connect to database: {conn_err}")
        sys.exit(1)

    # Step 2: Initialize Schema and Seeds
    print("\n[2/3] Applying non-destructive schema & baseline seeds...")
    try:
        init_schema()
        print("      -> Schema and baseline seed checks completed successfully.")
    except Exception as schema_err:
        print(f"\n[CRITICAL ERROR] Schema initialization failed: {schema_err}")
        sys.exit(1)

    # Step 3: Verify Records and Core Tables
    print("\n[3/3] Verifying core tables & records:")
    try:
        users_count = execute_query("SELECT COUNT(*) AS c FROM users", one=True)['c']
        admin_count = execute_query("SELECT COUNT(*) AS c FROM users WHERE role = 'admin'", one=True)['c']
        dept_count = execute_query("SELECT COUNT(*) AS c FROM departments", one=True)['c']
        complaint_count = execute_query("SELECT COUNT(*) AS c FROM complaints", one=True)['c']
        log_count = execute_query("SELECT COUNT(*) AS c FROM complaint_logs", one=True)['c']
        feedback_count = execute_query("SELECT COUNT(*) AS c FROM feedbacks", one=True)['c']
        message_count = execute_query("SELECT COUNT(*) AS c FROM contact_messages", one=True)['c']

        print(f"      - Total Registered Users:  {users_count}")
        print(f"      - Municipal Administrators: {admin_count}")
        print(f"      - Service Departments:     {dept_count}")
        print(f"      - Citizen Complaints:      {complaint_count}")
        print(f"      - Audit Trail Logs:        {log_count}")
        print(f"      - Feedback Submissions:    {feedback_count}")
        print(f"      - Landing Page Inquiries:  {message_count}")
        print("\n[SUCCESS] Civic Connects database verified and ready for deployment.")
    except Exception as verify_err:
        print(f"\n[CRITICAL ERROR] Record verification query failed: {verify_err}")
        sys.exit(1)

    print("=" * 70)
    print("Application start command for Render:")
    print("    gunicorn app:app --bind 0.0.0.0:$PORT")
    print("=" * 70)

if __name__ == '__main__':
    main()
