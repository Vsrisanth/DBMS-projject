import unittest
import os
import io
from app import create_app
from db import execute_query

class CivicConnectsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

    def test_01_public_landing_and_about(self):
        """Verify public landing page and about page."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Civic Connects', response.data)
        self.assertIn(b'Empowering Citizens', response.data)

        about_resp = self.client.get('/about')
        self.assertEqual(about_resp.status_code, 200)
        self.assertIn(b'About Civic Connects', about_resp.data)

    def test_02_auth_login_get(self):
        """Verify login page GET renders properly with role toggles."""
        response = self.client.get('/auth/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Sign In as Citizen', response.data)
        self.assertIn(b'roleToggleCitizen', response.data)
        self.assertIn(b'roleToggleAdmin', response.data)

    def test_03_citizen_login_success(self):
        """Verify citizen login with default seeded credentials."""
        response = self.client.post('/auth/login', data={
            'email': 'citizen@example.com',
            'password': 'Citizen@123',
            'role': 'citizen'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Citizen Overview', response.data)
        self.assertIn(b'Jane Citizen', response.data)

    def test_04_admin_login_success(self):
        """Verify municipal authority login."""
        response = self.client.post('/auth/login', data={
            'email': 'admin@civicconnects.gov',
            'password': 'Admin@123',
            'role': 'admin'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Command Center', response.data)
        self.assertIn(b'Executive Dashboard', response.data)

    def test_05_invalid_password_rejected(self):
        """Verify invalid password does not authenticate."""
        response = self.client.post('/auth/login', data={
            'email': 'citizen@example.com',
            'password': 'WrongPassword!',
            'role': 'citizen'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid email address or password', response.data)

    def test_06_citizen_registration(self):
        """Verify new citizen registration flow."""
        import random
        rand_num = random.randint(1000, 9999)
        test_email = f"resident_{rand_num}@example.com"

        response = self.client.post('/auth/register', data={
            'role': 'citizen',
            'name': 'Alex Resident',
            'email': test_email,
            'phone': '+1 (555) 019-9999',
            'address': '55 Elm Street, Ward 2',
            'password': 'Resident@123',
            'confirm_password': 'Resident@123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Registration successful', response.data)
        self.assertIn(b'Alex Resident', response.data)

    def test_07_access_control_protection(self):
        """Verify protected portals require authentication."""
        # Unauthenticated access to citizen dashboard redirects to login
        resp = self.client.get('/citizen/dashboard')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/auth/login', resp.headers['Location'])

        # Unauthenticated access to admin dashboard redirects to login
        admin_resp = self.client.get('/admin/dashboard')
        self.assertEqual(admin_resp.status_code, 302)
        self.assertIn('/auth/login', admin_resp.headers['Location'])

    def test_08_citizen_report_issue_and_track(self):
        """Verify citizen can report an issue with an image file."""
        self.client.post('/auth/login', data={
            'email': 'citizen@example.com',
            'password': 'Citizen@123',
            'role': 'citizen'
        })

        fake_image = (io.BytesIO(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'), 'hazard.png')

        response = self.client.post('/citizen/report-issue', data={
            'category': 'Road Damage',
            'title': 'Dangerous Sinkhole Near Crossing',
            'description': 'A 3-foot wide deep sinkhole formed on the main pedestrian crossing.',
            'location': 'Intersection of 4th Street & Market Lane',
            'latitude': '37.775000',
            'longitude': '-122.418000',
            'image': fake_image
        }, follow_redirects=True, content_type='multipart/form-data')

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Issue submitted successfully', response.data)
        self.assertIn(b'Dangerous Sinkhole Near Crossing', response.data)

    def test_09_admin_status_update_and_remarks(self):
        """Verify admin can update complaint status, assign department, and add remarks."""
        self.client.post('/auth/login', data={
            'email': 'admin@civicconnects.gov',
            'password': 'Admin@123',
            'role': 'admin'
        })

        update_resp = self.client.post('/admin/complaints/1/update', data={
            'status': 'in_progress',
            'department_id': '1',
            'admin_remarks': 'Patching machine and cold mix asphalt crew scheduled for 10:00 AM.'
        }, follow_redirects=True)

        self.assertEqual(update_resp.status_code, 200)
        self.assertIn(b'updated successfully to In Progress', update_resp.data)

        detail_resp = self.client.get('/admin/complaints/1')
        self.assertEqual(detail_resp.status_code, 200)
        data = detail_resp.get_json()
        self.assertEqual(data['complaint']['status'], 'in_progress')
        self.assertIn('Patching machine', data['complaint']['admin_remarks'])

    def test_10_public_ticket_tracking(self):
        """Verify public ticket tracking page without login."""
        response = self.client.get('/track?ticket=CC-8421')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'#CC-8421', response.data)
        self.assertIn(b'Potholes', response.data)

if __name__ == '__main__':
    unittest.main()
