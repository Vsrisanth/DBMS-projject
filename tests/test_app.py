import unittest
import os
import io
from app import create_app
from db import execute_query

class CivicConnectsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from db import init_schema
        init_schema()

        # Clean previous test-specific records only (preserves real users and complaints)
        execute_query("DELETE FROM complaint_logs WHERE complaint_id IN (SELECT id FROM complaints WHERE ticket_number = '#CC-8421' OR id = 1)", commit=True)
        execute_query("DELETE FROM complaints WHERE ticket_number = '#CC-8421' OR id = 1", commit=True)
        execute_query("DELETE FROM feedbacks WHERE subject = 'GPS location pin jitter on mobile safari' OR id = 1", commit=True)
        execute_query("DELETE FROM users WHERE email = 'citizen@example.com'", commit=True)

        from werkzeug.security import generate_password_hash
        pwd_hash = generate_password_hash('Citizen@123')

        # Insert test citizen (using email citizen@example.com)
        execute_query("""
            INSERT INTO users (name, email, phone, address, password_hash, role)
            VALUES ('Jane Citizen', 'citizen@example.com', '9876543210', '742 Evergreen Terrace', %s, 'citizen')
        """, (pwd_hash,), commit=True)
        
        citizen_user = execute_query("SELECT id FROM users WHERE email = 'citizen@example.com'", one=True)
        citizen_id = citizen_user['id'] if citizen_user else 2

        # Insert test complaint (#CC-8421) with id 1
        execute_query("""
            INSERT INTO complaints (id, ticket_number, user_id, category, title, description, location, latitude, longitude, image_url, department_id, status, admin_remarks)
            VALUES (1, '#CC-8421', %s, 'Road Damage', 'Severe Potholes and Asphalt Crumbling on Oak Street', 'Multiple deep craters along the westbound lane making vehicular commute hazardous. Two two-wheelers skidded yesterday evening.', 'Corner of Oak Street & 5th Avenue, Ward 4', 37.774929, -122.419416, 'sample_pothole.jpg', 1, 'pending', 'Under preliminary review by civil road inspection team.')
        """, (citizen_id,), commit=True)

        # Insert test feedback (id 1)
        execute_query("""
            INSERT INTO feedbacks (id, feedback_type, subject, message, severity, status)
            VALUES (1, 'bug_report', 'GPS location pin jitter on mobile safari', 'When attempting to click "Detect My Location" on an iPhone running iOS 17 Safari, the latitude field briefly populates then resets.', 'medium', 'unread')
        """, commit=True)

    @classmethod
    def tearDownClass(cls):
        # Clean up test-created data only, ensuring real user data remains intact
        execute_query("DELETE FROM complaint_logs WHERE complaint_id IN (SELECT id FROM complaints WHERE ticket_number = '#CC-8421')", commit=True)
        execute_query("DELETE FROM complaints WHERE ticket_number = '#CC-8421'", commit=True)
        execute_query("DELETE FROM feedbacks WHERE subject = 'GPS location pin jitter on mobile safari'", commit=True)
        execute_query("DELETE FROM users WHERE email LIKE '%@example.com'", commit=True)

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
            'email': 'admin@gmail.com',
            'password': 'admin@1234',
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
            'phone': '9876543211',
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
            'email': 'admin@gmail.com',
            'password': 'admin@1234',
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

    def test_11_landing_page_sections_and_explore(self):
        """Verify Requirement 1: Landing page sections (Hero, About, How It Works, Contact) and Explore CTA."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        # 1. Hero with Explore CTA
        self.assertIn(b'Explore Citizen Portal', response.data)
        self.assertIn(b'Empowering Citizens', response.data)
        # 2. About Us
        self.assertIn(b'About Civic Connects', response.data)
        self.assertIn(b'Transparent Governance', response.data)
        # 3. How It Works
        self.assertIn(b'How Civic Connects Works', response.data)
        self.assertIn(b'1. Report Issue', response.data)
        self.assertIn(b'4. Resolution Verified', response.data)
        # 4. Contact Us
        self.assertIn(b'Contact Municipal Support', response.data)
        self.assertIn(b'Central City Hall', response.data)

        # Explore CTA redirects unauthenticated user to citizen login
        explore_resp = self.client.get('/explore')
        self.assertEqual(explore_resp.status_code, 302)
        self.assertIn('/auth/login', explore_resp.headers['Location'])

    def test_12_landing_page_contact_form(self):
        """Verify Requirement 1: Functional contact form on landing page and admin dashboard delivery."""
        # 1. Verify top right corner does not have the 'Sign In' button
        home_resp = self.client.get('/')
        self.assertEqual(home_resp.status_code, 200)
        self.assertNotIn(b'Sign In', home_resp.data)
        self.assertIn(b'Explore', home_resp.data)

        # 2. Submit contact form without logging in (guest visitor)
        response = self.client.post('/contact', data={
            'name': 'Sarah Connor',
            'email': 'sarah@example.com',
            'subject': 'Ward 7 Drainage Inquiry',
            'message': 'When is the seasonal drain desilting scheduled?'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Thank you, Sarah Connor!', response.data)

        # 3. Verify message is stored in database
        saved_msg = execute_query("SELECT * FROM contact_messages WHERE email = %s", ('sarah@example.com',), one=True)
        self.assertIsNotNone(saved_msg)
        self.assertEqual(saved_msg['name'], 'Sarah Connor')
        self.assertEqual(saved_msg['subject'], 'Ward 7 Drainage Inquiry')

        # 4. Log in as admin and verify the message appears on the Admin Dashboard
        self.client.post('/auth/login', data={
            'email': 'admin@gmail.com',
            'password': 'admin@1234',
            'role': 'admin'
        }, follow_redirects=True)

        admin_dash = self.client.get('/admin/dashboard')
        self.assertEqual(admin_dash.status_code, 200)
        self.assertIn(b'Sarah Connor', admin_dash.data)
        self.assertIn(b'Ward 7 Drainage Inquiry', admin_dash.data)
        self.assertIn(b'When is the seasonal drain desilting scheduled?', admin_dash.data)

        # 5. Verify message appears on dedicated /admin/messages screen
        admin_msgs = self.client.get('/admin/messages')
        self.assertEqual(admin_msgs.status_code, 200)
        self.assertIn(b'Sarah Connor', admin_msgs.data)
        self.assertIn(b'Delete', admin_msgs.data)

        # 6. Verify Delete message action works
        del_resp = self.client.post(f"/admin/messages/{saved_msg['id']}/delete", follow_redirects=True)
        self.assertEqual(del_resp.status_code, 200)
        deleted_check = execute_query("SELECT * FROM contact_messages WHERE id = %s", (saved_msg['id'],), one=True)
        self.assertIsNone(deleted_check)

    def test_13_citizen_topbar_cleanup_and_track_status(self):
        """Verify Requirement 2: Top bar cleanup and dedicated Track Complaint sidebar navigation."""
        self.client.post('/auth/login', data={
            'email': 'citizen@example.com',
            'password': 'Citizen@123',
            'role': 'citizen'
        })

        resp = self.client.get('/citizen/dashboard')
        self.assertEqual(resp.status_code, 200)
        # Top bar cleanup: "Report New Issue" must NOT be in top bar actions
        self.assertNotIn(b'class="top-nav-actions">\n        <a href="/citizen/report-issue" class="btn btn-primary btn-sm">\n          Report New Issue', resp.data)
        # Dedicated "Track Complaint" item in sidebar navigation
        self.assertIn(b'Track Complaint', resp.data)

        # Access citizen status lookup interface
        track_resp = self.client.get('/citizen/track?ticket=CC-8421')
        self.assertEqual(track_resp.status_code, 200)
        self.assertIn(b'#CC-8421', track_resp.data)
        self.assertIn(b'Resolution Milestone Stepper', track_resp.data)

    def test_14_citizen_profile_avatar_upload(self):
        """Verify Requirement 3: Citizen profile photo upload and validation."""
        self.client.post('/auth/login', data={
            'email': 'citizen@example.com',
            'password': 'Citizen@123',
            'role': 'citizen'
        })

        fake_avatar = (io.BytesIO(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'), 'avatar_test.png')

        upload_resp = self.client.post('/citizen/profile', data={
            'action': 'upload_avatar',
            'avatar': fake_avatar
        }, follow_redirects=True, content_type='multipart/form-data')

        self.assertEqual(upload_resp.status_code, 200)
        self.assertIn(b'Profile photo uploaded and updated successfully!', upload_resp.data)

    def test_15_citizen_anonymous_feedback_submission(self):
        """Verify Requirement 4: Anonymous Feedback submission with identity stripping."""
        self.client.post('/auth/login', data={
            'email': 'citizen@example.com',
            'password': 'Citizen@123',
            'role': 'citizen'
        })

        # Submit anonymous bug report
        resp = self.client.post('/citizen/feedback', data={
            'feedback_type': 'bug_report',
            'subject': 'Map zoom slider sluggish on Firefox',
            'severity': 'medium',
            'message': 'When selecting location coordinates on Firefox 128, the zoom control jumps unexpectedly.'
        }, follow_redirects=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Your report has been submitted completely anonymously', resp.data)

        # Verify in database: Payload contains NO citizen user ID, NO citizen name, NO email, NO IP
        latest_fb = execute_query("SELECT * FROM feedbacks WHERE subject = 'Map zoom slider sluggish on Firefox'", one=True)
        self.assertIsNotNone(latest_fb)
        self.assertEqual(latest_fb['feedback_type'], 'bug_report')
        self.assertEqual(latest_fb['severity'], 'medium')
        # Check that there are no identity columns in table
        self.assertNotIn('user_id', latest_fb)
        self.assertNotIn('citizen_name', latest_fb)
        self.assertNotIn('email', latest_fb)
        self.assertNotIn('ip_address', latest_fb)

    def test_16_admin_feedback_review_screen_and_anonymity(self):
        """Verify Requirement 4: Admin feedback review screen, review/archive action, and strict anonymity."""
        self.client.post('/auth/login', data={
            'email': 'admin@gmail.com',
            'password': 'admin@1234',
            'role': 'admin'
        })

        review_screen = self.client.get('/admin/feedback')
        self.assertEqual(review_screen.status_code, 200)
        self.assertIn(b'Anonymous Feedback', review_screen.data)
        self.assertIn(b'Anonymous Citizen #', review_screen.data)
        # Ensure feedback records are strictly anonymous with no citizen account email
        self.assertNotIn(b'citizen@example.com', review_screen.data)

        # Update feedback status
        update_resp = self.client.post('/admin/feedback/1/status', data={
            'status': 'reviewed',
            'admin_notes': 'Report verified and filed with frontend QA board.'
        }, follow_redirects=True)
        self.assertEqual(update_resp.status_code, 200)
        self.assertIn(b'status updated to Reviewed', update_resp.data)

    def test_17_ai_civic_support_chatbot_api(self):
        """Verify Requirement 5: AI Civic Support Chatbot API with FAQs, 3D avatar, and ticket tracking."""
        # Verify 3D character static asset delivery
        img_resp = self.client.get('/static/images/civic_bot.png')
        self.assertEqual(img_resp.status_code, 200)
        img_resp.close()

        # Verify movable widget markup in citizen and public views
        page_resp = self.client.get('/')
        self.assertEqual(page_resp.status_code, 200)
        self.assertIn(b'civic_bot.png', page_resp.data)
        self.assertIn(b'civic-ai-launcher', page_resp.data)
        self.assertIn(b'civic-ai-header', page_resp.data)
        self.assertIn(b'civicAiLockedState', page_resp.data)

        # 1. Verify Unauthenticated guest request is rejected with 401 Unauthorized
        guest_resp = self.client.post('/api/ai-chat', json={'message': 'How do I report a pothole?'})
        self.assertEqual(guest_resp.status_code, 401)
        guest_data = guest_resp.get_json()
        self.assertEqual(guest_data['error'], 'Unauthorized')
        self.assertIn('Please Log In or Sign Up', guest_data['reply'])

        # Authenticate as citizen for protected AI chat operations
        self.client.post('/auth/login', data={
            'email': 'citizen@example.com',
            'password': 'Citizen@123',
            'role': 'citizen'
        }, follow_redirects=True)

        # 2. Ask general FAQ as authenticated citizen
        faq_resp = self.client.post('/api/ai-chat', json={'message': 'How do I report a pothole?'})
        self.assertEqual(faq_resp.status_code, 200)
        faq_data = faq_resp.get_json()
        self.assertIn('Report Issue', faq_data['reply'])
        self.assertGreater(len(faq_data['suggestions']), 0)

        # 3. Ask live ticket tracking (#CC-8421 was updated to In Progress in test_09)
        ticket_resp = self.client.post('/api/ai-chat', json={'message': 'Please check status for #CC-8421'})
        self.assertEqual(ticket_resp.status_code, 200)
        ticket_data = ticket_resp.get_json()
        self.assertIn('#CC-8421', ticket_data['reply'])
        self.assertIn('Road Damage', ticket_data['reply'])
        self.assertIn('In Progress', ticket_data['reply'])
        self.assertIn('/citizen/track?ticket=CC-8421', ticket_data['reply'])

        # 3. Verify clicking the chatbot link opens the grievance details successfully
        nav_resp = self.client.get('/citizen/track?ticket=CC-8421', follow_redirects=True)
        self.assertEqual(nav_resp.status_code, 200)
        self.assertIn(b'#CC-8421', nav_resp.data)
        self.assertIn(b'Road Damage', nav_resp.data)

        # 4. Verify /complaint/ shortcut and hash redirector
        complaint_url_resp = self.client.get('/complaint/CC-8421', follow_redirects=True)
        self.assertEqual(complaint_url_resp.status_code, 200)
        self.assertIn(b'#CC-8421', complaint_url_resp.data)

        hash_page = self.client.get('/complaint/')
        self.assertEqual(hash_page.status_code, 200)
        self.assertIn(b'Redirecting to Ticket Tracking', hash_page.data)

    def test_18_citizen_profile_delete_account(self):
        """Verify Requirement 3: Irreversible Delete Account inside Danger Zone."""
        import random
        rand_num = random.randint(10000, 99999)
        temp_email = f"delete_me_{rand_num}@example.com"

        # Register a temporary citizen
        self.client.post('/auth/register', data={
            'role': 'citizen',
            'name': 'Temp Citizen',
            'email': temp_email,
            'phone': '9876543212',
            'address': '12 Test St',
            'password': 'Password@123',
            'confirm_password': 'Password@123'
        })

        # Submit delete account form with confirmation
        del_resp = self.client.post('/citizen/profile', data={
            'action': 'delete_account',
            'confirm_password': 'Password@123',
            'confirm_text': 'DELETE'
        }, follow_redirects=True)

        self.assertEqual(del_resp.status_code, 200)
        self.assertIn(b'permanently deleted', del_resp.data)

        # Confirm user is completely gone from users table
        user_in_db = execute_query("SELECT id FROM users WHERE email = %s", (temp_email,), one=True)
        self.assertIsNone(user_in_db)

    def test_19_chatbot_excluded_on_auth_pages(self):
        """Verify Change 1: AI Chatbot does NOT appear on Login or Register pages for either Citizen or Admin."""
        # 1. Login page as Citizen
        login_cit_resp = self.client.get('/auth/login?role=citizen')
        self.assertEqual(login_cit_resp.status_code, 200)
        self.assertNotIn(b'civic-ai-launcher', login_cit_resp.data)
        self.assertNotIn(b'civic_bot.png', login_cit_resp.data)

        # 2. Login page as Admin
        login_adm_resp = self.client.get('/auth/login?role=admin')
        self.assertEqual(login_adm_resp.status_code, 200)
        self.assertNotIn(b'civic-ai-launcher', login_adm_resp.data)
        self.assertNotIn(b'civic_bot.png', login_adm_resp.data)

        # 3. Register / Sign Up page as Citizen
        reg_cit_resp = self.client.get('/auth/register?role=citizen')
        self.assertEqual(reg_cit_resp.status_code, 200)
        self.assertNotIn(b'civic-ai-launcher', reg_cit_resp.data)

        # 4. Register / Sign Up page as Admin
        reg_adm_resp = self.client.get('/auth/register?role=admin')
        self.assertEqual(reg_adm_resp.status_code, 200)
        self.assertNotIn(b'civic-ai-launcher', reg_adm_resp.data)

    def test_20_notification_bell_in_citizen_and_admin_dashboards(self):
        """Verify Change 2: Notification Bell is present on top right corner in both Citizen and Admin dashboards."""
        # 1. Verify in Citizen Dashboard
        self.client.post('/auth/login', data={
            'email': 'citizen@example.com',
            'password': 'Citizen@123',
            'role': 'citizen'
        })
        cit_resp = self.client.get('/citizen/dashboard')
        self.assertEqual(cit_resp.status_code, 200)
        self.assertIn(b'civic-notif-bell-btn', cit_resp.data)
        self.assertIn(b'civic-notif-dropdown', cit_resp.data)

        # Clear session before logging in as admin
        self.client.get('/auth/logout')

        # 2. Verify in Admin Dashboard
        self.client.post('/auth/login', data={
            'email': 'admin@gmail.com',
            'password': 'admin@1234',
            'role': 'admin'
        })
        adm_resp = self.client.get('/admin/dashboard')
        self.assertEqual(adm_resp.status_code, 200)
        self.assertIn(b'civic-notif-bell-btn', adm_resp.data)
        self.assertIn(b'civic-notif-dropdown', adm_resp.data)

    def test_21_delete_department_in_admin_portal(self):
        """Verify Admin can delete a department and associated complaints become unassigned."""
        # 1. Login as Admin
        self.client.post('/auth/login', data={
            'email': 'admin@gmail.com',
            'password': 'admin@1234',
            'role': 'admin'
        })

        # 2. Add a new department for testing deletion
        import random
        rand_suffix = random.randint(10000, 99999)
        dept_name = f"Test Division {rand_suffix}"
        dept_id = execute_query(
            "INSERT INTO departments (name, contact_email, description) VALUES (%s, %s, %s)",
            (dept_name, 'test_div@civicconnects.gov', 'Division designated for deletion testing.'),
            commit=True
        )
        self.assertIsNotNone(dept_id)

        # 3. Assign an existing complaint to this department
        complaint = execute_query("SELECT id FROM complaints LIMIT 1", one=True)
        if complaint:
            execute_query(
                "UPDATE complaints SET department_id = %s WHERE id = %s",
                (dept_id, complaint['id']),
                commit=True
            )

        # 4. View /admin/departments and verify the delete button is rendered
        view_resp = self.client.get('/admin/departments')
        self.assertEqual(view_resp.status_code, 200)
        self.assertIn(dept_name.encode('utf-8'), view_resp.data)
        self.assertIn(f"/admin/departments/{dept_id}/delete".encode('utf-8'), view_resp.data)

        # 5. Delete the department via POST
        del_resp = self.client.post(f"/admin/departments/{dept_id}/delete", follow_redirects=True)
        self.assertEqual(del_resp.status_code, 200)
        self.assertIn(b'has been deleted', del_resp.data)

        # 6. Verify department was removed from database
        dept_in_db = execute_query("SELECT * FROM departments WHERE id = %s", (dept_id,), one=True)
        self.assertIsNone(dept_in_db)

        # 7. Verify associated complaint was set to unassigned (department_id = NULL)
        if complaint:
            updated_c = execute_query("SELECT department_id FROM complaints WHERE id = %s", (complaint['id'],), one=True)
            self.assertIsNone(updated_c['department_id'])

    def test_22_citizen_report_with_geolocation_coordinates(self):
        """Verify Citizen Report Issue screen contains geolocation elements and captures coordinates."""
        # 1. Login as Citizen
        self.client.get('/auth/logout')
        self.client.post('/auth/login', data={
            'email': 'citizen@example.com',
            'password': 'Citizen@123',
            'role': 'citizen'
        })

        # 2. Check report form elements
        report_get = self.client.get('/citizen/report-issue')
        self.assertEqual(report_get.status_code, 200)
        self.assertIn(b'id="detectLocationBtn"', report_get.data)
        self.assertIn(b'id="locationInput"', report_get.data)
        self.assertIn(b'id="latInput"', report_get.data)
        self.assertIn(b'id="lngInput"', report_get.data)
        self.assertIn(b'id="geoStatus"', report_get.data)

        # 3. Submit complaint with detected GPS coordinates
        import random
        test_loc = f"Park Avenue Sector {random.randint(100, 999)}, Landmark Square"
        submit_resp = self.client.post('/citizen/report-issue', data={
            'category': 'Road Damage',
            'title': 'Deep pothole filled with rainwater',
            'description': 'Severe pothole causing hazards near intersection.',
            'location': test_loc,
            'latitude': '17.385044',
            'longitude': '78.486671'
        }, follow_redirects=True)
        self.assertEqual(submit_resp.status_code, 200)
        self.assertIn(b'Issue submitted successfully', submit_resp.data)

        # 4. Verify saved complaint in DB has coordinates
        saved_c = execute_query(
            "SELECT * FROM complaints WHERE location = %s ORDER BY id DESC LIMIT 1",
            (test_loc,),
            one=True
        )
        self.assertIsNotNone(saved_c)
        self.assertAlmostEqual(float(saved_c['latitude']), 17.385044, places=4)
        self.assertAlmostEqual(float(saved_c['longitude']), 78.486671, places=4)

    def test_23_indian_mobile_number_validation(self):
        """Verify Indian mobile number validation (exactly 10 digits starting with [6-9])."""
        # 1. Reject invalid numbers (starts with 1-5, US style, or wrong length)
        invalid_numbers = ['+1 (555) 019-9999', '5987654321', '98765', '987654321012', 'abcdefghij']
        for bad_phone in invalid_numbers:
            resp = self.client.post('/auth/register', data={
                'role': 'citizen',
                'name': 'Invalid Phone User',
                'email': 'bad_phone@example.com',
                'phone': bad_phone,
                'password': 'Password@123',
                'confirm_password': 'Password@123'
            }, follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn(b'valid 10-digit Indian mobile number', resp.data)

        # 2. Accept valid 10-digit Indian mobile numbers (e.g., 9876543219, +91 98765 43219)
        valid_resp = self.client.post('/auth/register', data={
            'role': 'citizen',
            'name': 'Valid Indian Citizen',
            'email': 'indian_citizen@example.com',
            'phone': '+91 98765 43219',
            'password': 'Password@123',
            'confirm_password': 'Password@123'
        }, follow_redirects=True)
        self.assertEqual(valid_resp.status_code, 200)
        self.assertIn(b'Registration successful', valid_resp.data)

        # 3. Verify clean 10-digit mobile number stored in DB
        user_row = execute_query("SELECT phone FROM users WHERE email = %s", ('indian_citizen@example.com',), one=True)
        self.assertIsNotNone(user_row)
        self.assertEqual(user_row['phone'], '9876543219')

    def test_24_admin_registration_disabled(self):
        """Verify that Admin self-registration is completely removed and blocked."""
        # 1. Registration page contains no Admin toggle and no Admin clearance key
        reg_resp = self.client.get('/auth/register')
        self.assertEqual(reg_resp.status_code, 200)
        self.assertIn(b'Create Citizen Account', reg_resp.data)
        self.assertNotIn(b'roleToggleAdmin', reg_resp.data)
        self.assertNotIn(b'adminPasskey', reg_resp.data)
        self.assertNotIn(b'Municipal Authority Clearance Key', reg_resp.data)

        # 2. Direct POST attempt to register an admin is rejected and redirected
        admin_reg_post = self.client.post('/auth/register', data={
            'role': 'admin',
            'name': 'Hacker Admin',
            'email': 'hacker@example.com',
            'phone': '9876543210',
            'password': 'Password@123',
            'confirm_password': 'Password@123'
        }, follow_redirects=True)
        self.assertEqual(admin_reg_post.status_code, 200)
        self.assertIn(b'Administrative accounts cannot be self-registered', admin_reg_post.data)

        # 3. Verify hacker account was never created in DB
        hacker_user = execute_query("SELECT id FROM users WHERE email = %s", ('hacker@example.com',), one=True)
        self.assertIsNone(hacker_user)

    def test_25_admin_manage_complaints_modal_and_citizen_notification(self):
        """Verify Manage Complaints modal renders scrollable form controls and delivers updates to citizen."""
        # 1. Verify CSS flex-chain rule prevents modal form overflow
        css_resp = self.client.get('/static/css/style.css')
        self.assertEqual(css_resp.status_code, 200)
        self.assertIn(b'.modal-dialog > form', css_resp.data)
        self.assertIn(b'min-height: 0', css_resp.data)
        css_resp.close()

        # 2. Admin visits Manage Complaints & Dashboard and both include shared modal controls
        self.client.post('/auth/login', data={
            'email': 'admin@gmail.com',
            'password': 'admin@1234',
            'role': 'admin'
        })
        for route in ['/admin/complaints', '/admin/dashboard']:
            page = self.client.get(route)
            self.assertEqual(page.status_code, 200)
            self.assertIn(b'id="complaintActionModal"', page.data)
            self.assertIn(b'id="modalAdminRemarks"', page.data)
            self.assertIn(b'Commit Changes &amp; Notify Citizen', page.data)
            self.assertIn(b'class="modal-form-grid"', page.data)

        # 3. Admin sends an issue update & remarks to citizen
        remark_msg = 'Road crew dispatched with asphalt patching unit for #CC-8421.'
        upd_resp = self.client.post('/admin/complaints/1/update', data={
            'status': 'in_progress',
            'department_id': '1',
            'admin_remarks': remark_msg
        }, follow_redirects=True)
        self.assertEqual(upd_resp.status_code, 200)
        self.assertIn(b'updated successfully to In Progress', upd_resp.data)

        # 4. Citizen sees the update in notifications, My Complaints, and Track Status
        self.client.get('/auth/logout')
        self.client.post('/auth/login', data={
            'email': 'citizen@example.com',
            'password': 'Citizen@123',
            'role': 'citizen'
        })

        cit_dash = self.client.get('/citizen/dashboard')
        self.assertEqual(cit_dash.status_code, 200)
        self.assertIn(remark_msg.encode('utf-8'), cit_dash.data)

        my_comp = self.client.get('/citizen/my-complaints')
        self.assertEqual(my_comp.status_code, 200)
        self.assertIn(remark_msg.encode('utf-8'), my_comp.data)

        track_resp = self.client.get('/citizen/track?ticket=CC-8421')
        self.assertEqual(track_resp.status_code, 200)
        self.assertIn(remark_msg.encode('utf-8'), track_resp.data)

    def test_26_signout_redirects_to_landing_page(self):
        """Verify that signing out redirects to the public landing page (index) instead of login."""
        # Log in first
        self.client.post('/auth/login', data={
            'email': 'citizen@example.com',
            'password': 'Citizen@123',
            'role': 'citizen'
        })
        # Hit logout
        logout_resp = self.client.get('/auth/logout')
        self.assertEqual(logout_resp.status_code, 302)
        self.assertEqual(logout_resp.headers.get('Location'), '/')

        # Following redirect leads to landing page
        follow_resp = self.client.get('/auth/logout', follow_redirects=True)
        self.assertEqual(follow_resp.status_code, 200)
        self.assertIn(b'Empowering Citizens', follow_resp.data)
        self.assertIn(b'Restoring Communities', follow_resp.data)
        self.assertIn(b'You have been securely logged out', follow_resp.data)

if __name__ == '__main__':
    unittest.main()
