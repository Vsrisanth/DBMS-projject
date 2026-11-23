import os
import sys
import sqlite3
import re
import mysql.connector
from mysql.connector import pooling
from config import Config

_pool = None
_db_mode = None  # 'mysql' or 'sqlite'

def get_mysql_connection_kwargs():
    """
    Constructs MySQL / TiDB connection arguments.
    Enables TLS with certificate verification for TiDB Cloud or when configured.
    Never exposes passwords in logs or traces.
    """
    kwargs = {
        'host': Config.DB_HOST,
        'port': Config.DB_PORT,
        'user': Config.DB_USER,
        'password': Config.DB_PASSWORD,
        'database': Config.DB_NAME,
        'connection_timeout': Config.DB_TIMEOUT,
    }

    # Determine whether SSL/TLS is required (e.g. TiDB Cloud port 4000, remote hosts, or explicitly set)
    is_tidb = ('tidbcloud.com' in Config.DB_HOST.lower()) or (Config.DB_PORT == 4000)
    should_use_ssl = Config.DB_SSL or is_tidb or Config.IS_PRODUCTION

    if should_use_ssl:
        kwargs['ssl_disabled'] = False

        # Attempt to locate trusted CA certificate bundle for verification
        ca_path = Config.DB_SSL_CA
        if not ca_path or not os.path.isfile(ca_path):
            try:
                import certifi
                ca_path = certifi.where()
            except ImportError:
                ca_path = None

        if not ca_path or not os.path.isfile(ca_path):
            # Check standard Linux CA bundle locations (Render, Debian, Ubuntu, Alpine)
            common_ca_paths = [
                '/etc/ssl/certs/ca-certificates.crt',
                '/etc/pki/tls/certs/ca-bundle.crt',
                '/etc/ssl/ca-bundle.pem',
                '/etc/ssl/cert.pem'
            ]
            for p in common_ca_paths:
                if os.path.isfile(p):
                    ca_path = p
                    break

        if ca_path and os.path.isfile(ca_path):
            kwargs['ssl_ca'] = ca_path
            kwargs['ssl_verify_cert'] = True
        else:
            # Fall back to driver's SSL verification without explicit CA file
            kwargs['ssl_verify_cert'] = True

    return kwargs

def init_connection_pool():
    """
    Initializes database connectivity according to DB_MODE / DB_ENGINE.
    Strictly prohibits silent SQLite fallback in production environments.
    """
    global _pool, _db_mode

    # Read engine preference ('tidb', 'mysql', 'sqlite', or 'auto')
    engine_preference = getattr(Config, 'DB_MODE', getattr(Config, 'DB_ENGINE', 'auto')).lower()
    is_production = getattr(Config, 'IS_PRODUCTION', False)

    # 1. SQLite explicitly configured (Only allowed in local development)
    if engine_preference == 'sqlite':
        if is_production:
            err_msg = (
                "[CRITICAL ERROR] DB_MODE is set to 'sqlite' in a production environment.\n"
                "SQLite is strictly prohibited in production on cloud platforms (e.g., Render) because "
                "ephemeral container filesystems wipe local databases on every deploy or restart.\n"
                "Please configure TiDB Cloud or MySQL connection credentials."
            )
            print("\n" + "=" * 70, file=sys.stderr)
            print(err_msg, file=sys.stderr)
            print("=" * 70 + "\n", file=sys.stderr)
            raise RuntimeError(err_msg)

        _db_mode = 'sqlite'
        print("[Database] Explicitly running in local SQLite mode (civic_connects.db).")
        return

    # 2. TiDB Cloud / MySQL Connection Attempt
    try:
        conn_kwargs = get_mysql_connection_kwargs()

        # Connect directly to the configured database.
        # Automatic database creation on startup is removed for security & production stability.
        test_conn = mysql.connector.connect(**conn_kwargs)
        test_conn.close()

        # Initialize thread-safe connection pool
        pool_kwargs = conn_kwargs.copy()
        _pool = pooling.MySQLConnectionPool(
            pool_name="civic_pool",
            pool_size=Config.DB_POOL_SIZE,
            pool_reset_session=True,
            **pool_kwargs
        )
        _db_mode = 'mysql'
        print(f"[Database] Successfully connected to live database '{Config.DB_NAME}' on {Config.DB_HOST}:{Config.DB_PORT} (Engine: MySQL/TiDB)")
    except Exception as e:
        # IN PRODUCTION OR WHEN TiDB/MySQL IS EXPLICITLY REQUESTED:
        # Halt immediately with detailed diagnostic information. NEVER fall back to SQLite.
        if is_production or engine_preference in ('mysql', 'tidb'):
            print("\n" + "=" * 75, file=sys.stderr)
            print("[CRITICAL DATABASE CONNECTION ERROR - STARTUP HALTED]", file=sys.stderr)
            print(f"Failed to connect to TiDB Cloud / MySQL at '{Config.DB_HOST}:{Config.DB_PORT}'.", file=sys.stderr)
            print(f"Target Database: '{Config.DB_NAME}' | User: '{Config.DB_USER}'", file=sys.stderr)
            print(f"Error Details:   {e}", file=sys.stderr)
            print("\nAction Required for Production (Render / TiDB Cloud):", file=sys.stderr)
            print("  1. Verify the following environment variables in your Render Dashboard:", file=sys.stderr)
            print("     - DB_HOST      (e.g., gateway01.us-east-1.prod.aws.tidbcloud.com)", file=sys.stderr)
            print("     - DB_PORT      (e.g., 4000 for TiDB Cloud)", file=sys.stderr)
            print("     - DB_USER      (e.g., xxxxxx.root)", file=sys.stderr)
            print("     - DB_PASSWORD  (your TiDB Cloud password)", file=sys.stderr)
            print("     - DB_NAME      (e.g., civic_connects)", file=sys.stderr)
            print("  2. Ensure your TiDB Cloud cluster allows traffic from external IPs (0.0.0.0/0).", file=sys.stderr)
            print("  3. Run 'python init_db.py' to initialize tables safely if not already done.", file=sys.stderr)
            print("  4. NOTE: The system will NEVER silently fall back to SQLite in production.", file=sys.stderr)
            print("=" * 75 + "\n", file=sys.stderr)
            raise RuntimeError(f"Database connection failed: {e}")

        # Local development auto-fallback with clear explanation
        print(f"[Database] Local MySQL/TiDB notice: {e}")
        print("[Database] Development Notice: Using local SQLite database (civic_connects.db).")
        print("[Database] Reminder: When deploying to Render, set TiDB Cloud credentials in environment variables.")
        _db_mode = 'sqlite'

def get_db_mode():
    """Returns active database mode ('mysql' or 'sqlite')."""
    global _db_mode
    if _db_mode is None:
        init_connection_pool()
    return _db_mode

def verify_connection():
    """
    Verifies that the database connection is alive and working.
    Does NOT modify schema or records.
    """
    mode = get_db_mode()
    conn = get_connection()
    try:
        if mode == 'mysql':
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
        return True
    finally:
        conn.close()

def get_connection():
    """
    Returns a database connection from the pool or creates a fresh connection.
    """
    global _pool
    mode = get_db_mode()
    if mode == 'mysql':
        try:
            return _pool.get_connection()
        except Exception:
            # Fallback reconnect using full connection parameters
            kwargs = get_mysql_connection_kwargs()
            return mysql.connector.connect(**kwargs)
    else:
        sqlite_path = os.path.join(Config.BASE_DIR, 'civic_connects.db')
        conn = sqlite3.connect(sqlite_path)
        conn.row_factory = sqlite3.Row
        # Enable foreign keys in SQLite
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
        # Replace NOW() with CURRENT_TIMESTAMP if needed
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
    """
    Initializes tables and seeds baseline data if not present.
    Strictly non-destructive:
      - Uses CREATE TABLE IF NOT EXISTS
      - Never drops or recreates existing tables
      - Preserves all existing records
      - Never overwrites existing administrator accounts or passwords
      - Safe to execute repeatedly (idempotent)
    """
    mode = get_db_mode()
    if mode == 'mysql':
        conn = get_connection()
        cursor = conn.cursor()
        try:
            # 1. Execute safe schema DDL from schema.sql
            schema_path = os.path.join(Config.BASE_DIR, 'schema.sql')
            if not os.path.exists(schema_path):
                schema_path = os.path.join(Config.BASE_DIR, 'database', 'civic_pulse.sql')

            if os.path.exists(schema_path):
                with open(schema_path, 'r', encoding='utf-8') as f:
                    sql_content = f.read()

                # Execute statement-by-statement safely
                for statement in sql_content.split(';'):
                    stmt = statement.strip()
                    if not stmt:
                        continue
                    # Skip CREATE DATABASE or USE statements if present
                    upper_stmt = stmt.upper()
                    if upper_stmt.startswith('CREATE DATABASE') or upper_stmt.startswith('USE '):
                        continue
                    # Reject any destructive DROP TABLE statements
                    if 'DROP TABLE' in upper_stmt:
                        print(f"[Database Security Notice] Skipping destructive statement: {stmt[:40]}...")
                        continue

                    try:
                        cursor.execute(stmt)
                    except Exception as stmt_err:
                        # Log but do not fail on duplicate notices
                        pass
                conn.commit()

            # 2. Safe ALTER TABLE migrations for existing tables (ensure avatar_url & image_url accommodate Cloudinary URLs)
            try:
                cursor.execute("ALTER TABLE `users` MODIFY COLUMN `avatar_url` VARCHAR(500) NULL;")
                conn.commit()
            except Exception:
                pass

            try:
                cursor.execute("ALTER TABLE `complaints` MODIFY COLUMN `image_url` VARCHAR(500) NULL;")
                conn.commit()
            except Exception:
                pass

            # 3. Seed baseline municipal departments if none exist
            cursor.execute("SELECT COUNT(*) FROM `departments`")
            dept_count = cursor.fetchone()[0]
            if dept_count == 0:
                cursor.execute("""
                INSERT IGNORE INTO `departments` (`id`, `name`, `contact_email`, `description`) VALUES
                (1, 'Roads & Highways Department', 'roads@civicconnects.gov', 'Potholes, asphalt resurfacing, road debris, and sidewalk maintenance'),
                (2, 'City Electricity & Power Board', 'electricity@civicconnects.gov', 'Power outages, transformer sparks, open junction boxes, and grid safety'),
                (3, 'Water Supply & Sewerage Board', 'water@civicconnects.gov', 'Pipeline bursts, water contamination, low pressure, and sewage leakage'),
                (4, 'Solid Waste & Sanitation', 'sanitation@civicconnects.gov', 'Garbage dumping, overflowing dumpsters, and commercial waste clearance'),
                (5, 'Urban Drainage & Flood Control', 'drainage@civicconnects.gov', 'Stormwater drainage blockages, canal siltation, and flood mitigation'),
                (6, 'Street Lighting & Signals', 'lighting@civicconnects.gov', 'Non-functional streetlights, timer issues, and traffic signal repairs'),
                (7, 'Public Works & Parks', 'publicworks@civicconnects.gov', 'Public parks, playground equipment, hazardous tree branches, and civic structures');
                """)
                conn.commit()
                print("[Database] Seeded 7 municipal departments.")

            # 4. Seed default administrator ONLY if no admin account exists
            # Never overwrite existing administrator passwords, accounts, or details
            cursor.execute("SELECT id FROM `users` WHERE `role` = 'admin' OR `email` = 'admin@gmail.com' LIMIT 1")
            existing_admin = cursor.fetchone()
            if not existing_admin:
                from werkzeug.security import generate_password_hash
                admin_pwd = generate_password_hash('admin@1234')
                cursor.execute("""
                INSERT INTO `users` (`name`, `email`, `phone`, `address`, `password_hash`, `role`, `created_at`)
                VALUES ('Civic Admin Officer', 'admin@gmail.com', '9876543210', 'City Hall, 100 Civic Center Plaza, Suite 400', %s, 'admin', NOW());
                """, (admin_pwd,))
                conn.commit()
                print("[Database] Seeded default administrator account (admin@gmail.com).")
            else:
                # Administrator already exists; preserve exact existing record
                pass

        except Exception as e:
            print(f"[Database] Notice during schema initialization: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    else:
        # SQLite Mode for local development
        conn = get_connection()
        cursor = conn.cursor()

        # Users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            address TEXT,
            avatar_url TEXT,
            password_hash TEXT NOT NULL,
            role TEXT CHECK(role IN ('citizen', 'admin')) NOT NULL DEFAULT 'citizen',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Migration check: Ensure avatar_url column exists in users
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'avatar_url' not in columns:
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT;")
            except Exception as e:
                pass

        # Departments table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            contact_email TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Complaints table
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

        # Complaint logs table
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

        # Anonymous Feedback table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feedback_type TEXT NOT NULL,
            subject TEXT NOT NULL,
            message TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'medium',
            status TEXT CHECK(status IN ('unread', 'reviewed', 'archived')) NOT NULL DEFAULT 'unread',
            admin_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Contact Messages table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS contact_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            subject TEXT NOT NULL DEFAULT 'General Inquiry',
            message TEXT NOT NULL,
            status TEXT CHECK(status IN ('unread', 'read', 'replied', 'archived')) NOT NULL DEFAULT 'unread',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        conn.commit()

        # Seed municipal departments if table is empty
        cursor.execute("SELECT COUNT(*) AS cnt FROM departments")
        if cursor.fetchone()[0] == 0:
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
            conn.commit()

        # Seed default municipal admin account only if no admin exists
        cursor.execute("SELECT COUNT(*) AS cnt FROM users WHERE role = 'admin' OR email = 'admin@gmail.com'")
        if cursor.fetchone()[0] == 0:
            from werkzeug.security import generate_password_hash
            admin_pwd = generate_password_hash('admin@1234')
            cursor.execute("""
            INSERT INTO users (name, email, phone, address, password_hash, role, created_at) VALUES
            ('Civic Admin Officer', 'admin@gmail.com', '9876543210', 'City Hall, 100 Civic Center Plaza, Suite 400', ?, 'admin', CURRENT_TIMESTAMP);
            """, (admin_pwd,))
            conn.commit()

        cursor.close()
        conn.close()
