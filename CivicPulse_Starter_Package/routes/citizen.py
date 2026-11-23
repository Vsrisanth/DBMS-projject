from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from utils.decorators import citizen_required
from utils.image_handler import save_complaint_image
from utils.helpers import generate_ticket_number
from werkzeug.security import generate_password_hash, check_password_hash
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

@citizen_bp.route('/dashboard')
@citizen_required
def dashboard():
    user_id = session['user_id']
    
    stats = {
        'total': execute_query("SELECT COUNT(*) AS c FROM complaints WHERE user_id = %s", (user_id,), one=True)['c'],
        'pending': execute_query("SELECT COUNT(*) AS c FROM complaints WHERE user_id = %s AND status = 'pending'", (user_id,), one=True)['c'],
        'in_progress': execute_query("SELECT COUNT(*) AS c FROM complaints WHERE user_id = %s AND status = 'in_progress'", (user_id,), one=True)['c'],
        'resolved': execute_query("SELECT COUNT(*) AS c FROM complaints WHERE user_id = %s AND status = 'resolved'", (user_id,), one=True)['c'],
        'rejected': execute_query("SELECT COUNT(*) AS c FROM complaints WHERE user_id = %s AND status = 'rejected'", (user_id,), one=True)['c']
    }

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

    complaint_ids = [c['id'] for c in complaints]
    logs_by_complaint = {}
    if complaint_ids:
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

@citizen_bp.route('/complaint/<ticket_number>')
@citizen_required
def complaint_detail(ticket_number):
    user_id = session['user_id']
    complaint = execute_query(
        """SELECT c.*, d.name AS department_name, d.contact_email AS department_email
           FROM complaints c
           LEFT JOIN departments d ON c.department_id = d.id
           WHERE c.ticket_number = %s AND c.user_id = %s""",
        (ticket_number, user_id),
        one=True
    )
    if not complaint:
        flash('Complaint ticket not found or unauthorized access.', 'danger')
        return redirect(url_for('citizen.my_complaints'))

    logs = execute_query(
        """SELECT l.*, u.name as admin_name 
           FROM complaint_logs l
           LEFT JOIN users u ON l.admin_id = u.id
           WHERE l.complaint_id = %s
           ORDER BY l.created_at ASC""",
        (complaint['id'],)
    )
    complaint['logs'] = logs

    return render_template('citizen/track_complaint.html', complaint=complaint)

@citizen_bp.route('/profile', methods=['GET', 'POST'])
@citizen_required
def profile():
    user_id = session['user_id']
    user = execute_query("SELECT * FROM users WHERE id = %s", (user_id,), one=True)

    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_info':
            name = request.form.get('name', '').strip()
            phone = request.form.get('phone', '').strip()
            address = request.form.get('address', '').strip()

            if not name or not phone:
                flash('Name and phone number are required.', 'danger')
            else:
                execute_query(
                    "UPDATE users SET name = %s, phone = %s, address = %s WHERE id = %s",
                    (name, phone, address, user_id),
                    commit=True
                )
                session['user_name'] = name
                flash('Profile information successfully updated.', 'success')
                return redirect(url_for('citizen.profile'))

        elif action == 'change_password':
            current_pwd = request.form.get('current_password', '')
            new_pwd = request.form.get('new_password', '')
            confirm_pwd = request.form.get('confirm_password', '')

            if not check_password_hash(user['password_hash'], current_pwd):
                flash('Current password entered is incorrect.', 'danger')
            elif new_pwd != confirm_pwd:
                flash('New passwords do not match.', 'danger')
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

        user = execute_query("SELECT * FROM users WHERE id = %s", (user_id,), one=True)

    return render_template('citizen/profile.html', user=user)
