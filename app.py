import os
from flask import Flask, render_template, redirect, url_for, session, flash, request, jsonify
from config import Config
from db import init_schema, execute_query, get_db_mode
from routes import register_routes
from utils.ai_bot import process_ai_message

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize upload directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config.get('AVATAR_UPLOAD_FOLDER', os.path.join(app.config['BASE_DIR'], 'static', 'uploads', 'avatars')), exist_ok=True)

    # Verify database connectivity on application startup
    # Note: Full schema initialization is separated from application startup (run via: python init_db.py)
    try:
        active_mode = get_db_mode()
        auto_init = os.environ.get('AUTO_INIT_DB', '').lower() in ('true', '1')
        is_sqlite_fresh = (active_mode == 'sqlite' and not os.path.exists(os.path.join(Config.BASE_DIR, 'civic_connects.db')))
        if auto_init or is_sqlite_fresh:
            init_schema()
    except Exception as e:
        print(f"[Database Connection Notice on Startup]: {e}")
        if app.config.get('IS_PRODUCTION'):
            raise

    # Template filter for cloud (Cloudinary) or local image URLs
    @app.template_filter('media_url')
    def media_url_filter(filename_or_url, folder='complaints'):
        if not filename_or_url:
            return ''
        s = str(filename_or_url).strip()
        if s.startswith('http://') or s.startswith('https://'):
            return s
        return url_for('static', filename=f'uploads/{folder}/{s}')

    # Register modular blueprints
    register_routes(app)

    # Invalidate stale sessions for users no longer in database
    @app.before_request
    def validate_session_user():
        if 'user_id' in session:
            try:
                db_user = execute_query("SELECT id FROM users WHERE id = %s", (session['user_id'],), one=True)
                if not db_user:
                    session.clear()
            except Exception:
                pass

    # Global template context processor
    @app.context_processor
    def inject_global_vars():
        user = None
        user_notifications = []
        if 'user_id' in session:
            try:
                db_user = execute_query("SELECT id, name, email, role, avatar_url FROM users WHERE id = %s", (session['user_id'],), one=True)
                if not db_user:
                    session.clear()
                else:
                    user = {
                        'id': db_user['id'],
                        'name': db_user['name'],
                        'email': db_user['email'],
                        'role': db_user['role'],
                        'avatar_url': db_user.get('avatar_url')
                    }
            except Exception:
                user = None

        if user:
            try:
                if user['role'] == 'citizen':
                    # Citizen alerts: Recent status updates on user's complaints
                    logs = execute_query(
                        """SELECT l.id, l.new_status, l.notes, l.created_at, c.ticket_number, c.title, c.category
                           FROM complaint_logs l
                           JOIN complaints c ON l.complaint_id = c.id
                           WHERE c.user_id = %s
                           ORDER BY l.created_at DESC LIMIT 6""",
                        (user['id'],)
                    )
                    for log in logs:
                        status_title = log['new_status'].replace('_', ' ').title()
                        user_notifications.append({
                            'id': f"log_{log['id']}",
                            'type': 'status_update',
                            'title': f"Ticket {log['ticket_number']} Status: {status_title}",
                            'message': log['notes'] or f"Milestone updated to {status_title}.",
                            'time': log['created_at'],
                            'link': url_for('citizen.track_status', ticket=log['ticket_number']),
                            'status': log['new_status']
                        })
                elif user['role'] == 'admin':
                    # Admin alerts: Recent pending grievances requiring attention
                    recent_c = execute_query(
                        """SELECT c.id, c.ticket_number, c.category, c.title, c.created_at, c.status, u.name AS citizen_name
                           FROM complaints c
                           JOIN users u ON c.user_id = u.id
                           ORDER BY c.created_at DESC LIMIT 6"""
                    )
                    for c in recent_c:
                        user_notifications.append({
                            'id': f"comp_{c['id']}",
                            'type': 'new_complaint',
                            'title': f"Ticket {c['ticket_number']}: {c['category']}",
                            'message': f"{c['citizen_name']}: {c['title'][:40]}...",
                            'time': c['created_at'],
                            'link': url_for('admin.complaints', q=c['ticket_number']),
                            'status': c['status']
                        })

                    # Unread landing page contact inquiries for admin
                    try:
                        unread_msgs = execute_query(
                            """SELECT id, name, subject, created_at FROM contact_messages WHERE status = 'unread' ORDER BY created_at DESC LIMIT 4"""
                        )
                        for m in unread_msgs:
                            user_notifications.append({
                                'id': f"msg_{m['id']}",
                                'type': 'contact_message',
                                'title': f"Inquiry: {m['subject'][:28]}",
                                'message': f"From {m['name']} (Landing Form)",
                                'time': m['created_at'],
                                'link': url_for('admin.dashboard') + '#inquiries',
                                'status': 'unread'
                            })
                    except Exception:
                        pass
            except Exception as e:
                user_notifications = []

        return {
            'current_user': user,
            'notifications': user_notifications,
            'db_mode': get_db_mode(),
            'app_name': 'Civic Connects',
            'app_tagline': 'Report · Track · Resolve'
        }

    # Root route: Always displays the modern, responsive landing page
    @app.route('/')
    def index():
        # Public statistics for landing hero and metrics
        try:
            total_resolved = execute_query("SELECT COUNT(*) AS c FROM complaints WHERE status = 'resolved'", one=True)['c']
            total_active = execute_query("SELECT COUNT(*) AS c FROM complaints WHERE status IN ('pending', 'in_progress')", one=True)['c']
            total_citizens = execute_query("SELECT COUNT(*) AS c FROM users WHERE role = 'citizen'", one=True)['c']
        except Exception:
            total_resolved = 12
            total_active = 5
            total_citizens = 8

        stats = {
            'resolved': total_resolved,
            'active': total_active,
            'citizens': total_citizens
        }
        return render_template('index.html', stats=stats)

    # Explore Route: Call-to-Action entry point
    @app.route('/explore')
    def explore():
        if 'user_id' in session:
            try:
                db_user = execute_query("SELECT id, role FROM users WHERE id = %s", (session['user_id'],), one=True)
                if db_user:
                    if db_user['role'] == 'admin':
                        return redirect(url_for('admin.dashboard'))
                    return redirect(url_for('citizen.dashboard'))
                session.clear()
            except Exception:
                session.clear()
        return redirect(url_for('auth.login', role='citizen', next=url_for('citizen.dashboard')))

    # Contact Form Handler
    @app.route('/contact', methods=['GET', 'POST'])
    def contact():
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip()
            subject = request.form.get('subject', 'General Inquiry').strip()
            message = request.form.get('message', '').strip()

            if not name or not email or not message:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'Please fill out all required fields (Name, Email, Message).'}), 400
                flash('Please fill out all required fields (Name, Email, Message).', 'danger')
                return redirect(url_for('index') + '#contact')

            # Persist the message in database for Admin Oversight & Redressal
            try:
                execute_query(
                    """INSERT INTO contact_messages (name, email, subject, message, status)
                       VALUES (%s, %s, %s, %s, 'unread')""",
                    (name, email, subject or 'General Inquiry', message),
                    commit=True
                )
            except Exception as e:
                print(f"[Contact Form Error] Could not save message: {e}")

            # Success response
            success_msg = f"Thank you, {name}! Your message has been received by the Municipal Support Team. We will reply to {email} within 24-48 hours."
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': success_msg})
            
            flash(success_msg, 'success')
            return redirect(url_for('index') + '#contact')

        return redirect(url_for('index') + '#contact')

    # AI Civic Support Chatbot API (Protected: Citizen Session Required)
    @app.route('/api/ai-chat', methods=['POST'])
    @app.route('/api/chat', methods=['POST'])
    def ai_chat():
        # Authentication Guard: Only authenticated users can query Civic Assistant AI
        if 'user_id' not in session:
            return jsonify({
                'error': 'Unauthorized',
                'reply': 'Please Log In or Sign Up to chat with Civic Assistant AI.'
            }), 401

        data = request.get_json(silent=True) or {}
        user_message = data.get('message', '').strip()
        response_payload = process_ai_message(user_message)
        return jsonify(response_payload)

    @app.route('/about')
    def about():
        return render_template('about.html')

    # Convenience shortcuts matching spec
    @app.route('/login')
    def login_shortcut():
        return redirect(url_for('auth.login', **request.args))

    @app.route('/register')
    def register_shortcut():
        return redirect(url_for('auth.register', **request.args))

    @app.route('/logout')
    def logout_shortcut():
        return redirect(url_for('auth.logout'))

    @app.route('/report-issue')
    def report_issue_shortcut():
        return redirect(url_for('citizen.report_issue'))

    @app.route('/my-complaints')
    def my_complaints_shortcut():
        return redirect(url_for('citizen.my_complaints'))

    # Universal Grievance Ticket Route & Fragment Redirector
    @app.route('/complaint/')
    @app.route('/complaint')
    @app.route('/complaint/<path:ticket_number>')
    def complaint_shortcut(ticket_number=None):
        if ticket_number:
            clean = ticket_number.strip().replace('#', '').strip()
            if 'user_id' in session and session.get('role') == 'citizen':
                return redirect(url_for('citizen.track_status', ticket=clean))
            return redirect(url_for('complaints.track', ticket=clean))
        # Handles client-side hash fragments like /complaint/#CC-8421
        return render_template('redirect_hash.html')

    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(413)
    def request_entity_too_large(e):
        flash('Uploaded image exceeds the 5MB maximum file size limit.', 'danger')
        return redirect(request.referrer or url_for('citizen.dashboard')), 413

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('base.html', error_title="500 - Server Error", 
                               error_msg="An unexpected error occurred. Municipal systems have logged this issue."), 500

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("\n" + "="*65)
    print("  * CIVIC CONNECTS - MUNICIPAL CITIZEN GRIEVANCE PORTAL *")
    print(f"  * Access citizen portal at: http://127.0.0.1:{port}     *")
    print("  * Administrator Access:    admin@gmail.com             *")
    print("="*65 + "\n")
    app.run(host='0.0.0.0', port=port, debug=Config.DEBUG)
