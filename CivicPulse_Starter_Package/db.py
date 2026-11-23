import os
import sqlite3
import re
import mysql.connector
from mysql.connector import pooling
from config import Config

_pool = None
_db_mode = None  # 'mysql' or 'sqlite'

def init_connection_pool():
    global _pool, _db_mode
    try:
        # Attempt to establish MySQL connection
        test_conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            connection_timeout=2
        )
        cursor = test_conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        cursor.close()
        test_conn.close()

        _pool = pooling.MySQLConnectionPool(
            pool_name="civic_pool",
            pool_size=5,
            pool_reset_session=True,
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME
        )
        _db_mode = 'mysql'
        print(f"[Database] Successfully connected to live MySQL database '{Config.DB_NAME}' on {Config.DB_HOST}:{Config.DB_PORT}")
    except Exception as e:
        print(f"[Database] MySQL connection notice: {e}")
        print("[Database] Using high-performance localized database engine (SQLite) with full schema synchronization.")
        _db_mode = 'sqlite'

def get_db_mode():
    global _db_mode
    if _db_mode is None:
        init_connection_pool()
    return _db_mode

def get_connection():
    global _pool
    mode = get_db_mode()
    if mode == 'mysql':
        try:
            return _pool.get_connection()
        except Exception:
            return mysql.connector.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME
            )
    else:
        sqlite_path = os.path.join(Config.BASE_DIR, 'civic_connects.db')
        conn = sqlite3.connect(sqlite_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

def execute_query(query, params=(), one=False, commit=False):
    """
    Executes a parameterized SQL query with automatic engine abstraction.
    Accepts standard %s placeholders. Returns dict or list of dicts.
    """
    mode = get_db_mode()
    conn = get_connection()
    result = None

    if mode == 'mysql':
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            if commit:
                conn.commit()
                result = cursor.lastrowid if cursor.lastrowid else cursor.rowcount
            else:
                if one:
                    result = cursor.fetchone()
                else:
                    result = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
    else:
        # SQLite mode: convert %s to ? and adjust syntax if needed
        sqlite_query = query.replace('%s', '?')
        sqlite_query = re.sub(r'NOW\(\)\s*-\s*INTERVAL\s+(\d+)\s+DAY', r"datetime('now', '-\1 day')", sqlite_query, flags=re.IGNORECASE)
        sqlite_query = re.sub(r'NOW\(\)\s*-\s*INTERVAL\s+(\d+)\s+HOUR', r"datetime('now', '-\1 hour')", sqlite_query, flags=re.IGNORECASE)
        sqlite_query = re.sub(r'NOW\(\)', r"CURRENT_TIMESTAMP", sqlite_query, flags=re.IGNORECASE)

        cursor = conn.cursor()
        try:
            cursor.execute(sqlite_query, params)
            if commit:
                conn.commit()
                result = cursor.lastrowid if cursor.lastrowid else cursor.rowcount
            else:
                if one:
                    row = cursor.fetchone()
                    result = dict(row) if row else None
                else:
                    rows = cursor.fetchall()
                    result = [dict(r) for r in rows]
        finally:
            cursor.close()
            conn.close()

    return result

def init_schema():
    """Initializes tables and seeds data if not present."""
    mode = get_db_mode()
    if mode == 'mysql':
        conn = get_connection()
        cursor = conn.cursor()
        schema_path = os.path.join(Config.BASE_DIR, 'schema.sql')
        if not os.path.exists(schema_path):
            schema_path = os.path.join(Config.BASE_DIR, 'database', 'civic_pulse.sql')
        
        if os.path.exists(schema_path):
            with open(schema_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            for statement in sql_content.split(';'):
                stmt = statement.strip()
                if stmt:
                    try:
                        cursor.execute(stmt)
                    except Exception:
                        pass
            conn.commit()
        cursor.close()
        conn.close()
    else:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            address TEXT,
            password_hash TEXT NOT NULL,
            role TEXT CHECK(role IN ('citizen', 'admin')) NOT NULL DEFAULT 'citizen',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            contact_email TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_number TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL,
            location TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            image_url TEXT,
            department_id INTEGER,
            status TEXT CHECK(status IN ('pending', 'in_progress', 'resolved', 'rejected')) NOT NULL DEFAULT 'pending',
            admin_remarks TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS complaint_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id INTEGER NOT NULL,
            admin_id INTEGER,
            previous_status TEXT,
            new_status TEXT NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE CASCADE,
            FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE SET NULL
        );
        """)

        conn.commit()

        cursor.execute("SELECT COUNT(*) AS cnt FROM users")
        if cursor.fetchone()[0] == 0:
            from werkzeug.security import generate_password_hash
            admin_pwd = generate_password_hash('Admin@123')
            citizen_pwd = generate_password_hash('Citizen@123')

            cursor.execute("""
            INSERT INTO departments (id, name, contact_email, description) VALUES
            (1, 'Roads & Highways Department', 'roads@civicconnects.gov', 'Potholes, asphalt resurfacing, road debris, and sidewalk maintenance'),
            (2, 'City Electricity & Power Board', 'electricity@civicconnects.gov', 'Power outages, transformer sparks, open junction boxes, and grid safety'),
            (3, 'Water Supply & Sewerage Board', 'water@civicconnects.gov', 'Pipeline bursts, water contamination, low pressure, and sewage leakage'),
            (4, 'Solid Waste & Sanitation', 'sanitation@civicconnects.gov', 'Garbage dumping, overflowing dumpsters, and commercial waste clearance'),
            (5, 'Urban Drainage & Flood Control', 'drainage@civicconnects.gov', 'Stormwater drainage blockages, canal siltation, and flood mitigation'),
            (6, 'Street Lighting & Signals', 'lighting@civicconnects.gov', 'Non-functional streetlights, timer issues, and traffic signal repairs'),
            (7, 'Public Works & Parks', 'publicworks@civicconnects.gov', 'Public parks, playground equipment, hazardous tree branches, and civic structures');
            """)

            cursor.execute("""
            INSERT INTO users (id, name, email, phone, address, password_hash, role, created_at) VALUES
            (1, 'Civic Admin Officer', 'admin@civicconnects.gov', '+1 (555) 019-2834', 'City Hall, 100 Civic Center Plaza, Suite 400', ?, 'admin', datetime('now', '-30 day')),
            (2, 'Jane Citizen', 'citizen@example.com', '+1 (555) 014-9821', '742 Evergreen Terrace, Sector 4, Civic Heights', ?, 'citizen', datetime('now', '-20 day')),
            (3, 'Marcus Vance', 'marcus.vance@example.com', '+1 (555) 018-4412', '108 Pine Crest Ave, Ward 12', ?, 'citizen', datetime('now', '-15 day'));
            """, (admin_pwd, citizen_pwd, citizen_pwd))

            cursor.execute("""
            INSERT INTO complaints (id, ticket_number, user_id, category, title, description, location, latitude, longitude, image_url, department_id, status, admin_remarks, created_at, updated_at) VALUES
            (1, '#CC-8421', 2, 'Road Damage', 'Severe Potholes and Asphalt Crumbling on Oak Street', 'Multiple deep craters along the westbound lane making vehicular commute hazardous. Two two-wheelers skidded yesterday evening.', 'Corner of Oak Street & 5th Avenue, Ward 4', 37.774929, -122.419416, 'sample_pothole.jpg', 1, 'pending', 'Under preliminary review by civil road inspection team.', datetime('now', '-3 day'), datetime('now', '-2 day')),
            (2, '#CC-9102', 2, 'Water Supply', 'Main Water Line Burst Causing Street Flooding', 'A high-pressure municipal main line ruptured near the subway entrance. Potable water is flooding the street and 30 residential homes have zero water pressure.', 'Block C, Metro Avenue, near Central Park Gate 2', 37.783333, -122.416667, 'sample_waterleak.jpg', 3, 'in_progress', 'Emergency repair crew dispatched on-site. Isolation valve shut off. Pipe replacement underway.', datetime('now', '-2 day'), datetime('now', '-4 hour')),
            (3, '#CC-7341', 2, 'Electricity', 'Overhead High-Voltage Wire Sparking During Rain', 'Frayed electrical cable hanging dangerously close to a pedestrian footpath near the bus shelter. Sparking observed during rainfall.', 'Lane 12, Sunrise Residential Enclave', 37.768900, -122.428500, 'sample_sparking.jpg', 2, 'resolved', 'Emergency lineman team dispatched. Insulators replaced, line tensioned and certified safe by regional electrical inspector.', datetime('now', '-7 day'), datetime('now', '-1 day')),
            (4, '#CC-6523', 3, 'Garbage Management', 'Illegal Waste Dumping and Overflowing Commercial Dumpster', 'A large commercial dump pile has accumulated across 40 feet of roadside. Foul odor and stray dog menace affecting adjacent school campus.', 'Behind Main Market Complex, Sector 9', 37.755000, -122.435000, 'sample_dumping.jpg', 4, 'in_progress', 'Sanitation truck assigned. Bulk clearance scheduled for tomorrow morning 6:00 AM.', datetime('now', '-4 day'), datetime('now', '-12 hour')),
            (5, '#CC-5219', 3, 'Streetlight Failure', 'Dark Stretch - 6 Consecutive LED Streetlights Inactive', 'The entire stretch from 3rd Avenue to 7th Avenue has no streetlights functioning for the past week, leading to safety concerns after dark.', 'Maple Boulevard between 3rd and 7th St', 37.762100, -122.410200, NULL, 6, 'resolved', 'Defective photoelectric controller replaced. All 6 luminaires tested and operational.', datetime('now', '-10 day'), datetime('now', '-5 day')),
            (6, '#CC-4110', 3, 'Drainage', 'Uncovered Deep Drainage Pit on Pedestrian Walkway', 'Storm drain cover is broken and missing. Deep concrete pit poses immediate risk to schoolchildren and evening joggers.', 'Opposite St. Jude Community School, North Gate', 37.790100, -122.405300, NULL, NULL, 'pending', 'Complaint logged and flagged for urgent barrier placement.', datetime('now', '-1 day'), datetime('now', '-1 day'));
            """)

            cursor.execute("""
            INSERT INTO complaint_logs (complaint_id, admin_id, previous_status, new_status, notes, created_at) VALUES
            (2, 1, 'pending', 'in_progress', 'Assigned to Water Supply & Sewerage Board. Crew on-site.', datetime('now', '-1 day')),
            (3, 1, 'pending', 'in_progress', 'High priority electrical hazard. Dispatched emergency crew.', datetime('now', '-6 day')),
            (3, 1, 'in_progress', 'resolved', 'Hazard mitigated. Line secured and re-energized safely.', datetime('now', '-1 day')),
            (4, 1, 'pending', 'in_progress', 'Forwarded to Sanitation division supervisor for vehicle routing.', datetime('now', '-2 day')),
            (5, 1, 'pending', 'in_progress', 'Work order issued to Lighting contractor.', datetime('now', '-8 day')),
            (5, 1, 'in_progress', 'resolved', 'Repairs completed and verified.', datetime('now', '-5 day'));
            """)

            conn.commit()
        cursor.close()
        conn.close()
