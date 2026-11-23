import os
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from utils.decorators import citizen_required
from utils.image_handler import save_complaint_image, save_avatar_image, delete_image_file
from utils.helpers import generate_ticket_number, validate_indian_phone
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from db import execute_query

citizen_bp = Blueprint('citizen', __name__)

CATEGORIES = [
    'Road Damage',
    'Water Supply',
    'Electricity',
    'Garbage Management',
    'Drainage',
    'Streetlight Failure',
    'Public Works & Parks',
    'Other'
]

FEEDBACK_TYPES = [
    ('bug_report', 'Bug Report / System Glitch'),
    ('feature_request', 'Feature Suggestion / Portal Enhancement'),
    ('service_feedback', 'Municipal Service Quality Feedback'),
    ('general', 'General Redressal Feedback')
]

@citizen_bp.route('/dashboard')
@citizen_required
def dashboard():
    user_id = session['user_id']
    
    # Summary stats
    stats = {
        'total': execute_query("SELECT COUNT(*) AS c FROM complaints WHERE user_id = %s", (user_id,), one=True)['c'],
        'pending': execute_query("SELECT COUNT(*) AS c FROM complaints WHERE user_id = %s AND status = 'pending'", (user_id,), one=True)['c'],
        'in_progress': execute_query("SELECT COUNT(*) AS c FROM complaints WHERE user_id = %s AND status = 'in_progress'", (user_id,), one=True)['c'],
        'resolved': execute_query("SELECT COUNT(*) AS c FROM complaints WHERE user_id = %s AND status = 'resolved'", (user_id,), one=True)['c'],
        'rejected': execute_query("SELECT COUNT(*) AS c FROM complaints WHERE user_id = %s AND status = 'rejected'", (user_id,), one=True)['c']
    }

    # Recent 5 complaints
    recent_complaints = execute_query(
        """SELECT c.*, d.name AS department_name
           FROM complaints c
           LEFT JOIN departments d ON c.department_id = d.id
           WHERE c.user_id = %s
           ORDER BY c.created_at DESC LIMIT 5""",
        (user_id,)
    )

    return render_template('citizen/dashboard.html', stats=stats, recent_complaints=recent_complaints)

@citizen_bp.route('/report-issue', methods=['GET', 'POST'])
@citizen_bp.route('/report', methods=['GET', 'POST'])
@citizen_required
def report_issue():
    if request.method == 'POST':
        category = request.form.get('category', '').strip()
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        location = request.form.get('location', '').strip()
        latitude = request.form.get('latitude') or None
        longitude = request.form.get('longitude') or None
        image_file = request.files.get('image')

        # Fallback title if user leaves title blank
        if not title:
            title = f"{category} Issue at {location[:30]}"

        if not category or not description or not location:
            flash('Category, detailed description, and location are required.', 'danger')
            return render_template('citizen/report.html', categories=CATEGORIES,
                                   category=category, title=title, description=description, location=location)

        image_filename = None
        if image_file and image_file.filename != '':
            try:
                image_filename = save_complaint_image(image_file)
            except ValueError as err:
                flash(str(err), 'danger')
                return render_template('citizen/report.html', categories=CATEGORIES,
                                       category=category, title=title, description=description, location=location)

        ticket_number = generate_ticket_number()
        user_id = session['user_id']

        # Auto-match department if category matches
        dept_match = None
        dept_map = {
            'Road Damage': 1,
            'Electricity': 2,
            'Water Supply': 3,
            'Garbage Management': 4,
            'Drainage': 5,
            'Streetlight Failure': 6,
            'Public Works & Parks': 7
        }
        dept_id = dept_map.get(category)

        complaint_id = execute_query(
            """INSERT INTO complaints 
               (ticket_number, user_id, category, title, description, location, latitude, longitude, image_url, department_id, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')""",
            (ticket_number, user_id, category, title, description, location, latitude, longitude, image_filename, dept_id),
            commit=True
        )

        # Log creation
        execute_query(
            """INSERT INTO complaint_logs (complaint_id, admin_id, previous_status, new_status, notes)
               VALUES (%s, NULL, NULL, 'pending', 'Grievance registered by citizen.')""",
            (complaint_id,),
            commit=True
        )

        flash(f'Issue submitted successfully! Your Ticket ID is {ticket_number}. Track real-time progress below.', 'success')
        return redirect(url_for('citizen.my_complaints'))

    return render_template('citizen/report.html', categories=CATEGORIES)

@citizen_bp.route('/my-complaints')
@citizen_bp.route('/complaints')
@citizen_required
def my_complaints():
    user_id = session['user_id']
    status_filter = request.args.get('status', 'all').strip().lower()
    search_query = request.args.get('q', '').strip()

    sql = """
        SELECT c.*, d.name AS department_name
        FROM complaints c
        LEFT JOIN departments d ON c.department_id = d.id
        WHERE c.user_id = %s
    """
    params = [user_id]

    if status_filter in ['pending', 'in_progress', 'resolved', 'rejected']:
        sql += " AND c.status = %s"
        params.append(status_filter)

    if search_query:
        sql += " AND (c.ticket_number LIKE %s OR c.title LIKE %s OR c.description LIKE %s OR c.location LIKE %s OR c.category LIKE %s)"
        like_term = f"%{search_query}%"
        params.extend([like_term, like_term, like_term, like_term, like_term])

    sql += " ORDER BY c.created_at DESC"

    complaints = execute_query(sql, tuple(params))

    # Fetch logs for all complaints
    complaint_ids = [c['id'] for c in complaints]
    logs_by_complaint = {}
    if complaint_ids:
        # SQLite / MySQL safe in-clause
        placeholders = ','.join(['%s'] * len(complaint_ids))
        logs = execute_query(
            f"SELECT * FROM complaint_logs WHERE complaint_id IN ({placeholders}) ORDER BY created_at ASC",
            tuple(complaint_ids)
        )
        for log in logs:
            cid = log['complaint_id']
            if cid not in logs_by_complaint:
                logs_by_complaint[cid] = []
            logs_by_complaint[cid].append(log)

    for c in complaints:
        c['logs'] = logs_by_complaint.get(c['id'], [])

    return render_template('citizen/my_complaints.html', 
                           complaints=complaints, 
                           current_status=status_filter, 
                           search_query=search_query)

@citizen_bp.route('/complaint/<path:ticket_number>')
def complaint_detail(ticket_number):
    """Seamless redirect to status lookup for citizen or public tracker."""
    clean = ticket_number.strip().replace('#', '').strip()
    if 'user_id' in session and session.get('role') == 'citizen':
        return redirect(url_for('citizen.track_status', ticket=clean))
    return redirect(url_for('complaints.track', ticket=clean))

@citizen_bp.route('/track', methods=['GET', 'POST'])
@citizen_bp.route('/track-complaint', methods=['GET', 'POST'])
@citizen_bp.route('/track-status', methods=['GET', 'POST'])
def track_status():
    """
    Citizen Portal Status Lookup Interface:
    Allows citizens to search and view real-time complaint timelines via complaint/ticket ID.
    Redirects unauthenticated visitors to public tracking seamlessly.
    """
    if 'user_id' not in session:
        return redirect(url_for('complaints.track', **request.args))
    if session.get('role') != 'citizen':
        return redirect(url_for('admin.complaints', **request.args))
    ticket_number = request.args.get('ticket') or request.form.get('ticket', '')
    ticket_number = ticket_number.strip().upper()
    if ticket_number and not ticket_number.startswith('#'):
        ticket_number = f"#{ticket_number}"

    complaint = None
    logs = []
    searched = False

    if ticket_number:
        searched = True
        complaint = execute_query(
            """SELECT c.*, d.name AS department_name, d.contact_email AS department_email
               FROM complaints c
               LEFT JOIN departments d ON c.department_id = d.id
               WHERE c.ticket_number = %s""",
            (ticket_number,),
            one=True
        )
        if complaint:
            logs = execute_query(
                """SELECT l.*, u.name as admin_name 
                   FROM complaint_logs l
                   LEFT JOIN users u ON l.admin_id = u.id
                   WHERE l.complaint_id = %s
                   ORDER BY l.created_at ASC""",
                (complaint['id'],)
            )

    return render_template('citizen/track.html', 
                           complaint=complaint, 
                           logs=logs, 
                           searched=searched, 
                           ticket_number=ticket_number)

@citizen_bp.route('/profile', methods=['GET', 'POST'])
@citizen_required
def profile():
    """
    Citizen Profile Overhaul:
    - Personal info update
    - Profile photo upload with client and server validation
    - Password management
    - Sign out & Danger zone irreversible account deletion
    """
    user_id = session['user_id']
    user = execute_query("SELECT * FROM users WHERE id = %s", (user_id,), one=True)

    if request.method == 'POST':
        action = request.form.get('action')
        
        # 1. Profile Photo Upload Handler
        if action == 'upload_avatar':
            avatar_file = request.files.get('avatar')
            if not avatar_file or avatar_file.filename == '':
                flash('Please select an image file (PNG, JPG, or WEBP) under 5MB.', 'warning')
            else:
                try:
                    filename = save_avatar_image(avatar_file)
                    # Clean up old avatar image file if present
                    if user.get('avatar_url'):
                        delete_image_file(user['avatar_url'], folder='avatars')
                    execute_query(
                        "UPDATE users SET avatar_url = %s WHERE id = %s",
                        (filename, user_id),
                        commit=True
                    )
                    session['user_avatar'] = filename
                    flash('Profile photo uploaded and updated successfully!', 'success')
                except ValueError as ve:
                    flash(str(ve), 'danger')
                except Exception as ex:
                    flash(f'Error uploading avatar image: {str(ex)}', 'danger')
            return redirect(url_for('citizen.profile'))

        # Remove Avatar
        elif action == 'remove_avatar':
            if user.get('avatar_url'):
                delete_image_file(user['avatar_url'], folder='avatars')
                execute_query("UPDATE users SET avatar_url = NULL WHERE id = %s", (user_id,), commit=True)
                session['user_avatar'] = None
                flash('Profile photo removed.', 'info')
            return redirect(url_for('citizen.profile'))

        # 2. Update Personal Details
        elif action == 'update_info':
            name = request.form.get('name', '').strip()
            phone = request.form.get('phone', '').strip()
            address = request.form.get('address', '').strip()

            if not name or not phone:
                flash('Full Name and Mobile Phone Number are required.', 'danger')
            else:
                is_valid_phone, normalized_phone = validate_indian_phone(phone)
                if not is_valid_phone:
                    flash('Please enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9 (e.g. 9876543210).', 'danger')
                    return redirect(url_for('citizen.profile'))
                phone = normalized_phone

                execute_query(
                    "UPDATE users SET name = %s, phone = %s, address = %s WHERE id = %s",
                    (name, phone, address, user_id),
                    commit=True
                )
                session['user_name'] = name
                flash('Profile information successfully saved.', 'success')
            return redirect(url_for('citizen.profile'))

        # 3. Security & Password Change
        elif action == 'change_password':
            current_pwd = request.form.get('current_password', '')
            new_pwd = request.form.get('new_password', '')
            confirm_pwd = request.form.get('confirm_password', '')

            if not check_password_hash(user['password_hash'], current_pwd):
                flash('Current password entered is incorrect.', 'danger')
            elif new_pwd != confirm_pwd:
                flash('New passwords do not match. Please re-enter.', 'danger')
            elif len(new_pwd) < 6:
                flash('New password must be at least 6 characters long.', 'danger')
            else:
                new_hash = generate_password_hash(new_pwd)
                execute_query(
                    "UPDATE users SET password_hash = %s WHERE id = %s",
                    (new_hash, user_id),
                    commit=True
                )
                flash('Password changed successfully.', 'success')
            return redirect(url_for('citizen.profile'))

        # 4. Irreversible Delete Account Action (Danger Zone)
        elif action == 'delete_account':
            confirm_pwd = request.form.get('confirm_password', '')
            confirm_text = request.form.get('confirm_text', '').strip()

            if not check_password_hash(user['password_hash'], confirm_pwd) and confirm_text != 'DELETE':
                flash('Account deletion cancelled: Password verification or confirmation text failed.', 'danger')
                return redirect(url_for('citizen.profile'))

            # Clean up uploaded avatar image
            if user.get('avatar_url'):
                delete_image_file(user['avatar_url'], folder='avatars')

            # Irreversible deletion / anonymization:
            # Foreign key CASCADE removes or disassociates related complaint records
            execute_query("DELETE FROM users WHERE id = %s", (user_id,), commit=True)

            session.clear()
            flash('Your account and profile have been permanently deleted. All session data terminated.', 'info')
            return redirect(url_for('index'))

        user = execute_query("SELECT * FROM users WHERE id = %s", (user_id,), one=True)

    # User complaint statistics for profile summary card
    stats = {
        'total': execute_query("SELECT COUNT(*) AS c FROM complaints WHERE user_id = %s", (user_id,), one=True)['c'],
        'resolved': execute_query("SELECT COUNT(*) AS c FROM complaints WHERE user_id = %s AND status = 'resolved'", (user_id,), one=True)['c']
    }

    return render_template('citizen/profile.html', user=user, stats=stats)

@citizen_bp.route('/feedback', methods=['GET', 'POST'])
@citizen_bp.route('/feedback-and-report', methods=['GET', 'POST'])
@citizen_required
def feedback():
    """
    Anonymous Feedback & Bug Reporting System:
    ANONYMITY CONSTRAINT:
    Do NOT link or associate citizen user_id, name, email, or IP address with this
    submission in the database payload.
    """
    if request.method == 'POST':
        # Strictly extract content fields only
        feedback_type = request.form.get('feedback_type', 'general').strip().lower()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()
        severity = request.form.get('severity', 'medium').strip().lower()

        if not subject or not message:
            flash('Both subject and detailed message are required.', 'danger')
            return render_template('citizen/feedback.html', 
                                   feedback_types=FEEDBACK_TYPES,
                                   subject=subject,
                                   message=message,
                                   feedback_type=feedback_type,
                                   severity=severity)

        valid_types = [t[0] for t in FEEDBACK_TYPES]
        if feedback_type not in valid_types:
            feedback_type = 'general'

        if severity not in ['low', 'medium', 'high', 'critical']:
            severity = 'medium'

        # STRICT IDENTITY STRIPPING LOGIC:
        # Intentionally no session['user_id'], no user name, no email, no IP address
        # are included in the query parameters or schema table.
        execute_query(
            """INSERT INTO feedbacks (feedback_type, subject, message, severity, status)
               VALUES (%s, %s, %s, %s, 'unread')""",
            (feedback_type, subject, message, severity),
            commit=True
        )

        flash('Your report has been submitted completely anonymously. No identity or network metadata was saved.', 'success')
        return redirect(url_for('citizen.feedback'))

    return render_template('citizen/feedback.html', feedback_types=FEEDBACK_TYPES)
