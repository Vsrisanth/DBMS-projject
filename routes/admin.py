from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from utils.decorators import admin_required
from db import execute_query

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    # Key Metrics
    total = execute_query("SELECT COUNT(*) AS c FROM complaints", one=True)['c']
    pending = execute_query("SELECT COUNT(*) AS c FROM complaints WHERE status = 'pending'", one=True)['c']
    in_progress = execute_query("SELECT COUNT(*) AS c FROM complaints WHERE status = 'in_progress'", one=True)['c']
    resolved = execute_query("SELECT COUNT(*) AS c FROM complaints WHERE status = 'resolved'", one=True)['c']
    rejected = execute_query("SELECT COUNT(*) AS c FROM complaints WHERE status = 'rejected'", one=True)['c']
    total_citizens = execute_query("SELECT COUNT(*) AS c FROM users WHERE role = 'citizen'", one=True)['c']

    resolution_rate = round((resolved / total * 100), 1) if total > 0 else 0

    # Contact Form Inquiries Metrics
    try:
        total_messages = execute_query("SELECT COUNT(*) AS c FROM contact_messages", one=True)['c']
        unread_messages = execute_query("SELECT COUNT(*) AS c FROM contact_messages WHERE status = 'unread'", one=True)['c']
        recent_messages = execute_query("SELECT * FROM contact_messages ORDER BY created_at DESC LIMIT 8")
    except Exception:
        total_messages = 0
        unread_messages = 0
        recent_messages = []

    stats = {
        'total': total,
        'pending': pending,
        'in_progress': in_progress,
        'resolved': resolved,
        'rejected': rejected,
        'total_citizens': total_citizens,
        'resolution_rate': resolution_rate,
        'total_messages': total_messages,
        'unread_messages': unread_messages
    }

    # Category Breakdown
    category_counts = execute_query(
        """SELECT category, COUNT(*) as count 
           FROM complaints 
           GROUP BY category 
           ORDER BY count DESC"""
    )
    for cat in category_counts:
        cat['pct'] = round((cat['count'] / total * 100), 1) if total > 0 else 0

    # Recent complaints
    recent_complaints = execute_query(
        """SELECT c.*, u.name AS citizen_name, u.email AS citizen_email, u.phone AS citizen_phone, d.name AS department_name
           FROM complaints c
           JOIN users u ON c.user_id = u.id
           LEFT JOIN departments d ON c.department_id = d.id
           ORDER BY c.created_at DESC LIMIT 6"""
    )

    departments = execute_query("SELECT * FROM departments ORDER BY name ASC")

    return render_template('admin/dashboard.html', 
                           stats=stats, 
                           category_counts=category_counts, 
                           recent_complaints=recent_complaints,
                           departments=departments,
                           recent_messages=recent_messages)

@admin_bp.route('/complaints')
@admin_required
def complaints():
    status_filter = request.args.get('status', 'all').strip().lower()
    category_filter = request.args.get('category', 'all').strip()
    department_filter = request.args.get('department', 'all').strip()
    search_query = request.args.get('q', '').strip()

    sql = """
        SELECT c.*, u.name AS citizen_name, u.email AS citizen_email, u.phone AS citizen_phone, u.address AS citizen_address,
               d.name AS department_name
        FROM complaints c
        JOIN users u ON c.user_id = u.id
        LEFT JOIN departments d ON c.department_id = d.id
        WHERE 1=1
    """
    params = []

    if status_filter in ['pending', 'in_progress', 'resolved', 'rejected']:
        sql += " AND c.status = %s"
        params.append(status_filter)

    if category_filter and category_filter != 'all':
        sql += " AND c.category = %s"
        params.append(category_filter)

    if department_filter and department_filter != 'all':
        if department_filter == 'unassigned':
            sql += " AND c.department_id IS NULL"
        else:
            sql += " AND c.department_id = %s"
            params.append(int(department_filter))

    if search_query:
        sql += " AND (c.ticket_number LIKE %s OR c.title LIKE %s OR c.description LIKE %s OR c.location LIKE %s OR u.name LIKE %s OR u.phone LIKE %s)"
        like_term = f"%{search_query}%"
        params.extend([like_term, like_term, like_term, like_term, like_term, like_term])

    sql += " ORDER BY c.created_at DESC"

    complaint_list = execute_query(sql, tuple(params))
    departments = execute_query("SELECT * FROM departments ORDER BY name ASC")
    
    # List of all categories for dropdown
    default_categories = [
        'Road Damage',
        'Water Supply',
        'Electricity',
        'Garbage Management',
        'Drainage',
        'Streetlight Failure',
        'Public Works & Parks',
        'Other'
    ]
    categories_raw = execute_query("SELECT DISTINCT category FROM complaints ORDER BY category ASC")
    existing_cats = [r['category'] for r in categories_raw] if categories_raw else []
    categories = sorted(list(set(existing_cats + default_categories)))

    return render_template('admin/complaints.html', 
                           complaints=complaint_list, 
                           departments=departments,
                           categories=categories,
                           current_status=status_filter,
                           current_category=category_filter,
                           current_department=department_filter,
                           search_query=search_query)

@admin_bp.route('/complaints/<int:complaint_id>')
@admin_required
def complaint_detail_json(complaint_id):
    complaint = execute_query(
        """SELECT c.*, u.name AS citizen_name, u.email AS citizen_email, u.phone AS citizen_phone, u.address AS citizen_address,
                  d.name AS department_name
           FROM complaints c
           JOIN users u ON c.user_id = u.id
           LEFT JOIN departments d ON c.department_id = d.id
           WHERE c.id = %s""",
        (complaint_id,),
        one=True
    )
    if not complaint:
        return jsonify({'error': 'Not found'}), 404

    logs = execute_query(
        """SELECT l.*, u.name as admin_name 
           FROM complaint_logs l
           LEFT JOIN users u ON l.admin_id = u.id
           WHERE l.complaint_id = %s
           ORDER BY l.created_at ASC""",
        (complaint_id,)
    )

    return jsonify({
        'complaint': complaint,
        'logs': logs
    })

@admin_bp.route('/complaints/<int:complaint_id>/update', methods=['POST'])
@admin_required
def update_complaint(complaint_id):
    complaint = execute_query("SELECT * FROM complaints WHERE id = %s", (complaint_id,), one=True)
    if not complaint:
        flash('Complaint not found.', 'danger')
        return redirect(url_for('admin.complaints'))

    new_status = request.form.get('status', complaint['status']).strip().lower()
    department_id = request.form.get('department_id')
    admin_remarks = request.form.get('admin_remarks', '').strip()

    if department_id and department_id.strip() != '':
        try:
            department_id = int(department_id)
        except ValueError:
            department_id = None
    else:
        department_id = None

    if new_status not in ['pending', 'in_progress', 'resolved', 'rejected']:
        new_status = complaint['status']

    # Update database
    execute_query(
        """UPDATE complaints 
           SET status = %s, department_id = %s, admin_remarks = %s, updated_at = CURRENT_TIMESTAMP
           WHERE id = %s""",
        (new_status, department_id, admin_remarks, complaint_id),
        commit=True
    )

    # Log action in audit trail
    log_note = admin_remarks if admin_remarks else f"Status updated to {new_status.replace('_', ' ').capitalize()}."
    execute_query(
        """INSERT INTO complaint_logs (complaint_id, admin_id, previous_status, new_status, notes)
           VALUES (%s, %s, %s, %s, %s)""",
        (complaint_id, session['user_id'], complaint['status'], new_status, log_note),
        commit=True
    )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': f"Ticket {complaint['ticket_number']} updated successfully."})

    flash(f"Ticket {complaint['ticket_number']} updated successfully to {new_status.replace('_', ' ').title()}.", 'success')
    return redirect(request.referrer or url_for('admin.complaints'))

@admin_bp.route('/departments', methods=['GET', 'POST'])
@admin_required
def departments():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('contact_email', '').strip()
        desc = request.form.get('description', '').strip()

        if not name:
            flash('Department name is required.', 'danger')
        else:
            execute_query(
                "INSERT INTO departments (name, contact_email, description) VALUES (%s, %s, %s)",
                (name, email, desc),
                commit=True
            )
            flash(f"Department '{name}' added successfully.", 'success')
            return redirect(url_for('admin.departments'))

    departments_list = execute_query(
        """SELECT d.*, COUNT(c.id) AS total_complaints,
                  SUM(CASE WHEN c.status = 'pending' THEN 1 ELSE 0 END) AS pending_count,
                  SUM(CASE WHEN c.status = 'in_progress' THEN 1 ELSE 0 END) AS in_progress_count,
                  SUM(CASE WHEN c.status = 'resolved' THEN 1 ELSE 0 END) AS resolved_count
           FROM departments d
           LEFT JOIN complaints c ON d.id = c.department_id
           GROUP BY d.id
           ORDER BY d.name ASC"""
    )

    return render_template('admin/manage_departments.html', departments=departments_list)

@admin_bp.route('/departments/<int:dept_id>/delete', methods=['POST'])
@admin_required
def delete_department(dept_id):
    dept = execute_query("SELECT * FROM departments WHERE id = %s", (dept_id,), one=True)
    if not dept:
        flash('Department not found.', 'danger')
        return redirect(url_for('admin.departments'))

    # Dissociate any complaints currently assigned to this department
    execute_query("UPDATE complaints SET department_id = NULL WHERE department_id = %s", (dept_id,), commit=True)

    # Delete the department record
    execute_query("DELETE FROM departments WHERE id = %s", (dept_id,), commit=True)

    flash(f"Department '{dept['name']}' has been deleted. Any assigned complaints have been marked as unassigned.", 'success')
    return redirect(url_for('admin.departments'))

@admin_bp.route('/users')
@admin_required
def users():
    users_list = execute_query(
        """SELECT u.*, COUNT(c.id) AS total_complaints
           FROM users u
           LEFT JOIN complaints c ON u.id = c.user_id
           GROUP BY u.id
           ORDER BY u.created_at DESC"""
    )
    return render_template('admin/manage_users.html', users=users_list)

@admin_bp.route('/feedback')
@admin_bp.route('/reports')
@admin_required
def feedback():
    """
    Dedicated screen for reviewing anonymous citizen feedback and bug reports.
    STRICT REQUIREMENT: Submissions must remain completely anonymous.
    No user identity or account information is retrieved, queried, or displayed.
    """
    status_filter = request.args.get('status', 'all').strip().lower()
    type_filter = request.args.get('type', 'all').strip().lower()
    severity_filter = request.args.get('severity', 'all').strip().lower()
    search_query = request.args.get('q', '').strip()

    sql = "SELECT * FROM feedbacks WHERE 1=1"
    params = []

    if status_filter in ['unread', 'reviewed', 'archived']:
        sql += " AND status = %s"
        params.append(status_filter)

    if type_filter in ['bug_report', 'feature_request', 'service_feedback', 'general']:
        sql += " AND feedback_type = %s"
        params.append(type_filter)

    if severity_filter in ['low', 'medium', 'high', 'critical']:
        sql += " AND severity = %s"
        params.append(severity_filter)

    if search_query:
        sql += " AND (subject LIKE %s OR message LIKE %s)"
        like_term = f"%{search_query}%"
        params.extend([like_term, like_term])

    sql += " ORDER BY created_at DESC"

    feedbacks_list = execute_query(sql, tuple(params))

    # Metric summary for admin
    counts = {
        'total': execute_query("SELECT COUNT(*) AS c FROM feedbacks", one=True)['c'],
        'unread': execute_query("SELECT COUNT(*) AS c FROM feedbacks WHERE status = 'unread'", one=True)['c'],
        'reviewed': execute_query("SELECT COUNT(*) AS c FROM feedbacks WHERE status = 'reviewed'", one=True)['c'],
        'archived': execute_query("SELECT COUNT(*) AS c FROM feedbacks WHERE status = 'archived'", one=True)['c']
    }

    return render_template('admin/feedback.html',
                           feedbacks=feedbacks_list,
                           counts=counts,
                           current_status=status_filter,
                           current_type=type_filter,
                           current_severity=severity_filter,
                           search_query=search_query)

@admin_bp.route('/feedback/<int:feedback_id>/status', methods=['POST'])
@admin_required
def update_feedback_status(feedback_id):
    """Update review or archive state for an anonymous report."""
    new_status = request.form.get('status', '').strip().lower()
    admin_notes = request.form.get('admin_notes', '').strip()

    if new_status not in ['unread', 'reviewed', 'archived']:
        flash('Invalid status specified.', 'danger')
        return redirect(url_for('admin.feedback'))

    if admin_notes:
        execute_query(
            "UPDATE feedbacks SET status = %s, admin_notes = %s WHERE id = %s",
            (new_status, admin_notes, feedback_id),
            commit=True
        )
    else:
        execute_query(
            "UPDATE feedbacks SET status = %s WHERE id = %s",
            (new_status, feedback_id),
            commit=True
        )

    flash(f'Anonymous report #{feedback_id} status updated to {new_status.title()}.', 'success')
    return redirect(request.referrer or url_for('admin.feedback'))

@admin_bp.route('/messages')
@admin_required
def messages():
    """List and filter public inquiry messages sent from landing page contact form."""
    status_filter = request.args.get('status', 'all').strip().lower()
    search_query = request.args.get('q', '').strip()

    sql = "SELECT * FROM contact_messages WHERE 1=1"
    params = []

    if status_filter in ['unread', 'read', 'replied', 'archived']:
        sql += " AND status = %s"
        params.append(status_filter)

    if search_query:
        sql += " AND (name LIKE %s OR email LIKE %s OR subject LIKE %s OR message LIKE %s)"
        like_term = f"%{search_query}%"
        params.extend([like_term, like_term, like_term, like_term])

    sql += " ORDER BY created_at DESC"

    messages_list = execute_query(sql, tuple(params))
    counts = {
        'total': execute_query("SELECT COUNT(*) AS c FROM contact_messages", one=True)['c'],
        'unread': execute_query("SELECT COUNT(*) AS c FROM contact_messages WHERE status = 'unread'", one=True)['c'],
        'read': execute_query("SELECT COUNT(*) AS c FROM contact_messages WHERE status = 'read'", one=True)['c'],
        'archived': execute_query("SELECT COUNT(*) AS c FROM contact_messages WHERE status = 'archived'", one=True)['c']
    }

    return render_template('admin/messages.html',
                           messages=messages_list,
                           counts=counts,
                           current_status=status_filter,
                           search_query=search_query)

@admin_bp.route('/messages/<int:msg_id>/status', methods=['POST'])
@admin_required
def mark_message_status(msg_id):
    """Mark an inquiry message as read, replied, or archived."""
    new_status = request.form.get('status', 'read').strip().lower()
    if new_status in ['unread', 'read', 'replied', 'archived']:
        execute_query(
            "UPDATE contact_messages SET status = %s WHERE id = %s",
            (new_status, msg_id),
            commit=True
        )
        flash(f'Inquiry message #{msg_id} marked as {new_status.title()}.', 'success')
    return redirect(request.referrer or url_for('admin.dashboard'))

@admin_bp.route('/messages/<int:msg_id>/delete', methods=['POST'])
@admin_required
def delete_message(msg_id):
    """Permanently delete an inquiry message."""
    execute_query("DELETE FROM contact_messages WHERE id = %s", (msg_id,), commit=True)
    flash(f'Inquiry message #{msg_id} has been permanently deleted.', 'success')
    return redirect(request.referrer or url_for('admin.messages'))
