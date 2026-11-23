"""
Civic Connects - Deployment & TiDB Cloud Verification Test Suite
Tests all 12 deployment safety requirements:
1. Flask app creation and start
2. TiDB Cloud connection configuration & SSL kwargs
3. Preservation of existing tables & structures
4. Non-deletion of records
5. Idempotent schema initialization
6. Citizen registration & login
7. Complaint submission
8. Complaint image upload handling (Cloudinary & local)
9. Complaint status updates and audit logs
10. Admin and department management
11. SQL query syntax compatibility
12. Strict prohibition of SQLite fallback in production
"""

import unittest
import os
import io
import sys
from unittest.mock import patch, MagicMock
from app import create_app
from config import Config
from db import (
    execute_query, init_schema, get_db_mode, verify_connection,
    get_mysql_connection_kwargs, init_connection_pool
)
from utils.image_handler import allowed_file, is_cloudinary_configured, save_complaint_image, save_avatar_image

class DeploymentSafetyTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_01_app_starts_successfully(self):
        """1. Verify that the Flask application starts and responds."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Civic Connects', response.data)

    def test_02_tidb_connection_kwargs_and_ssl(self):
        """2. Verify that TiDB Cloud connection kwargs enable TLS/SSL appropriately."""
        with patch.object(Config, 'DB_HOST', 'gateway01.us-east-1.prod.aws.tidbcloud.com'), \
             patch.object(Config, 'DB_PORT', 4000), \
             patch.object(Config, 'DB_USER', 'test_user.root'), \
             patch.object(Config, 'DB_PASSWORD', 'secret_pwd'), \
             patch.object(Config, 'DB_NAME', 'civic_connects'), \
             patch.object(Config, 'IS_PRODUCTION', True):

            kwargs = get_mysql_connection_kwargs()
            self.assertEqual(kwargs['host'], 'gateway01.us-east-1.prod.aws.tidbcloud.com')
            self.assertEqual(kwargs['port'], 4000)
            self.assertEqual(kwargs['user'], 'test_user.root')
            self.assertEqual(kwargs['password'], 'secret_pwd')
            self.assertEqual(kwargs['database'], 'civic_connects')
            self.assertFalse(kwargs.get('ssl_disabled', True))
            self.assertTrue(kwargs.get('ssl_verify_cert', False))

    def test_03_no_sqlite_fallback_in_production(self):
        """3 & 12. Verify that SQLite fallback NEVER happens in production when TiDB/MySQL fails."""
        with patch.object(Config, 'IS_PRODUCTION', True), \
             patch.object(Config, 'DB_MODE', 'auto'), \
             patch.object(Config, 'DB_HOST', 'nonexistent.tidbcloud.com'), \
             patch.object(Config, 'DB_PORT', 4000):

            # Attempting to initialize connection pool with failing remote host in production MUST raise RuntimeError
            with self.assertRaises(RuntimeError) as ctx:
                import db
                # Reset cached mode
                db._db_mode = None
                init_connection_pool()

            self.assertIn("Database connection failed", str(ctx.exception))

    def test_04_sqlite_forbidden_in_production(self):
        """Verify that explicitly configuring DB_MODE='sqlite' raises RuntimeError in production."""
        with patch.object(Config, 'IS_PRODUCTION', True), \
             patch.object(Config, 'DB_MODE', 'sqlite'):

            with self.assertRaises(RuntimeError) as ctx:
                import db
                db._db_mode = None
                init_connection_pool()

            self.assertIn("SQLite is strictly prohibited in production", str(ctx.exception))

    def test_05_idempotent_schema_initialization(self):
        """4 & 5. Verify that running init_schema multiple times preserves records and never duplicates."""
        # Clean test user if present
        execute_query("DELETE FROM users WHERE email = 'idempotent_test@example.com'", commit=True)

        from werkzeug.security import generate_password_hash
        pwd_hash = generate_password_hash('TestPass@123')
        execute_query("""
            INSERT INTO users (name, email, phone, address, password_hash, role)
            VALUES ('Persistent Citizen', 'idempotent_test@example.com', '9876543211', '123 Test St', %s, 'citizen')
        """, (pwd_hash,), commit=True)

        # Record count before
        count_before = execute_query("SELECT COUNT(*) AS c FROM users", one=True)['c']
        dept_before = execute_query("SELECT COUNT(*) AS c FROM departments", one=True)['c']

        # Run init_schema twice
        init_schema()
        init_schema()

        count_after = execute_query("SELECT COUNT(*) AS c FROM users", one=True)['c']
        dept_after = execute_query("SELECT COUNT(*) AS c FROM departments", one=True)['c']

        self.assertEqual(count_before, count_after, "User record count must not change on schema re-init")
        self.assertEqual(dept_before, dept_after, "Department count must not change on schema re-init")

        # Verify specific test user is completely intact
        user = execute_query("SELECT * FROM users WHERE email = 'idempotent_test@example.com'", one=True)
        self.assertIsNotNone(user)
        self.assertEqual(user['name'], 'Persistent Citizen')

        # Cleanup
        execute_query("DELETE FROM users WHERE email = 'idempotent_test@example.com'", commit=True)

    def test_06_admin_account_never_overwritten(self):
        """Verify that existing administrator credentials and info are NEVER overwritten by init_schema."""
        # Find or ensure admin exists
        admin = execute_query("SELECT * FROM users WHERE role = 'admin' LIMIT 1", one=True)
        if not admin:
            init_schema()
            admin = execute_query("SELECT * FROM users WHERE role = 'admin' LIMIT 1", one=True)

        original_hash = admin['password_hash']
        original_email = admin['email']

        # Run init_schema again
        init_schema()

        refreshed_admin = execute_query("SELECT * FROM users WHERE id = %s", (admin['id'],), one=True)
        self.assertEqual(refreshed_admin['password_hash'], original_hash, "Admin password hash must remain untouched")
        self.assertEqual(refreshed_admin['email'], original_email, "Admin email must remain untouched")

    def test_07_citizen_registration_and_login(self):
        """6. Test citizen registration and subsequent login."""
        test_email = 'new_cit_test@example.com'
        execute_query("DELETE FROM users WHERE email = %s", (test_email,), commit=True)

        reg_data = {
            'name': 'Ramesh Kumar',
            'email': test_email,
            'phone': '9876543210',
            'address': 'Flat 402, Lotus Towers, Ward 7',
            'password': 'Password@123',
            'confirm_password': 'Password@123'
        }
        res = self.client.post('/auth/register', data=reg_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Ramesh Kumar', res.data)

        # Logout
        self.client.get('/auth/logout')

        # Login again
        login_data = {
            'email': test_email,
            'password': 'Password@123',
            'role': 'citizen'
        }
        login_res = self.client.post('/auth/login', data=login_data, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b'Citizen Overview', login_res.data)

        # Cleanup
        execute_query("DELETE FROM users WHERE email = %s", (test_email,), commit=True)

    def test_08_complaint_submission_with_image(self):
        """7 & 8. Test complaint submission with an uploaded image."""
        # Login test citizen
        test_email = 'cit_submit_test@example.com'
        execute_query("DELETE FROM users WHERE email = %s", (test_email,), commit=True)
        from werkzeug.security import generate_password_hash
        pwd_hash = generate_password_hash('Pass@123')
        uid = execute_query("""
            INSERT INTO users (name, email, phone, address, password_hash, role)
            VALUES ('Sunita Rao', %s, '9876543212', 'Sector 5, Ward 12', %s, 'citizen')
        """, (test_email, pwd_hash), commit=True)

        with self.client.session_transaction() as sess:
            sess['user_id'] = uid
            sess['user_name'] = 'Sunita Rao'
            sess['user_email'] = test_email
            sess['role'] = 'citizen'

        # Submit complaint with image
        complaint_data = {
            'category': 'Road Damage',
            'title': 'Deep Pothole Near Gate 3',
            'description': 'A large crater has formed on the service road causing vehicular accidents.',
            'location': 'Gate 3, MG Road, Ward 12',
            'image': (io.BytesIO(b"fake-image-bytes-png"), 'test_evidence.png')
        }
        post_res = self.client.post('/citizen/report-issue', data=complaint_data, follow_redirects=True, content_type='multipart/form-data')
        self.assertEqual(post_res.status_code, 200)

        # Verify complaint exists in database
        c = execute_query("SELECT * FROM complaints WHERE user_id = %s", (uid,), one=True)
        self.assertIsNotNone(c)
        self.assertEqual(c['category'], 'Road Damage')
        self.assertIsNotNone(c['image_url'])

        # Cleanup
        execute_query("DELETE FROM complaint_logs WHERE complaint_id = %s", (c['id'],), commit=True)
        execute_query("DELETE FROM complaints WHERE id = %s", (c['id'],), commit=True)
        execute_query("DELETE FROM users WHERE id = %s", (uid,), commit=True)

    def test_09_complaint_status_update_and_audit_log(self):
        """9. Test complaint status update and audit log creation by administrator."""
        # Create test citizen & complaint
        c_user = execute_query("INSERT INTO users (name, email, phone, password_hash, role) VALUES ('Audit User', 'audit@example.com', '9876543215', 'hash', 'citizen')", commit=True)
        cid = execute_query("""
            INSERT INTO complaints (ticket_number, user_id, category, title, description, location, status)
            VALUES ('#CC-TEST-AUDIT', %s, 'Water Supply', 'Broken Pipe', 'Water leaking', 'Main St', 'pending')
        """, (c_user,), commit=True)

        admin = execute_query("SELECT * FROM users WHERE role = 'admin' LIMIT 1", one=True)

        with self.client.session_transaction() as sess:
            sess['user_id'] = admin['id']
            sess['user_name'] = admin['name']
            sess['user_email'] = admin['email']
            sess['role'] = 'admin'

        # Update status to in_progress with remark
        update_data = {
            'status': 'in_progress',
            'department_id': '1',
            'admin_remarks': 'Maintenance crew dispatched to fix pipeline.'
        }
        res = self.client.post(f'/admin/complaints/{cid}/update', data=update_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Verify complaint status updated
        comp = execute_query("SELECT * FROM complaints WHERE id = %s", (cid,), one=True)
        self.assertEqual(comp['status'], 'in_progress')
        self.assertEqual(comp['admin_remarks'], 'Maintenance crew dispatched to fix pipeline.')

        # Verify audit log exists
        logs = execute_query("SELECT * FROM complaint_logs WHERE complaint_id = %s", (cid,))
        self.assertTrue(len(logs) > 0)
        self.assertEqual(logs[0]['new_status'], 'in_progress')

        # Cleanup
        execute_query("DELETE FROM complaint_logs WHERE complaint_id = %s", (cid,), commit=True)
        execute_query("DELETE FROM complaints WHERE id = %s", (cid,), commit=True)
        execute_query("DELETE FROM users WHERE id = %s", (c_user,), commit=True)

    def test_10_admin_and_department_management(self):
        """10. Test administrator department creation and deletion."""
        admin = execute_query("SELECT * FROM users WHERE role = 'admin' LIMIT 1", one=True)

        with self.client.session_transaction() as sess:
            sess['user_id'] = admin['id']
            sess['user_name'] = admin['name']
            sess['user_email'] = admin['email']
            sess['role'] = 'admin'

        # Create department
        dept_data = {
            'name': 'Test Environment & Forestry Board',
            'contact_email': 'forestry@civicconnects.gov',
            'description': 'Parks, forestry and pollution control'
        }
        res = self.client.post('/admin/departments', data=dept_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        dept = execute_query("SELECT * FROM departments WHERE name = %s", (dept_data['name'],), one=True)
        self.assertIsNotNone(dept)

        # Delete department
        del_res = self.client.post(f'/admin/departments/{dept["id"]}/delete', follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)

        deleted_dept = execute_query("SELECT * FROM departments WHERE id = %s", (dept['id'],), one=True)
        self.assertIsNone(deleted_dept)

    def test_11_image_handler_and_cloudinary_support(self):
        """Verify image validation and Cloudinary configuration detection."""
        # Test allowed extensions
        self.assertTrue(allowed_file('photo.png'))
        self.assertTrue(allowed_file('photo.jpg'))
        self.assertTrue(allowed_file('photo.jpeg'))
        self.assertTrue(allowed_file('photo.webp'))
        self.assertFalse(allowed_file('malicious.exe'))
        self.assertFalse(allowed_file('script.sh'))
        self.assertFalse(allowed_file('code.py'))

        # When Cloudinary env vars are missing, is_cloudinary_configured() is False
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(is_cloudinary_configured())

    def test_12_media_url_template_filter(self):
        """Verify that media_url filter properly resolves both Cloudinary and local files."""
        from app import create_app
        test_app = create_app()
        with test_app.test_request_context():
            filter_fn = test_app.jinja_env.filters['media_url']
            # Cloudinary remote URL
            cloud_url = 'https://res.cloudinary.com/demo/image/upload/v12345/evidence.jpg'
            self.assertEqual(filter_fn(cloud_url), cloud_url)

            # Local filename
            local_name = 'sample_photo.jpg'
            self.assertEqual(filter_fn(local_name, 'complaints'), '/static/uploads/complaints/sample_photo.jpg')
            self.assertEqual(filter_fn(local_name, 'avatars'), '/static/uploads/avatars/sample_photo.jpg')

if __name__ == '__main__':
    unittest.main()
