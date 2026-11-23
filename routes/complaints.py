from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from db import execute_query

complaints_bp = Blueprint('complaints', __name__)

@complaints_bp.route('/track', methods=['GET', 'POST'])
def track():
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
            """SELECT c.*, d.name AS department_name
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

    return render_template('citizen/track_complaint.html', 
                           complaint=complaint, 
                           logs=logs, 
                           searched=searched, 
                           ticket_number=ticket_number)
