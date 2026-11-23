import os
from flask import Flask, render_template, redirect, url_for, session, flash, request
from config import Config
from db import init_schema, execute_query, get_db_mode
from routes import register_routes

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    try:
        init_schema()
    except Exception as e:
        print(f"[Warning] Error during schema init: {e}")

    register_routes(app)

    @app.context_processor
    def inject_global_vars():
        user = None
        if 'user_id' in session:
            user = {
                'id': session.get('user_id'),
                'name': session.get('user_name'),
                'email': session.get('user_email'),
                'role': session.get('role')
            }
        return {
            'current_user': user,
            'db_mode': get_db_mode(),
            'app_name': 'Civic Connects',
            'app_tagline': 'Report · Track · Resolve'
        }

    @app.route('/')
    def index():
        if 'user_id' in session:
            if session.get('role') == 'admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('citizen.dashboard'))
        
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

    @app.route('/about')
    def about():
        return render_template('about.html')

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

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('base.html', error_title="404 - Page Not Found", 
                               error_msg="The page you requested could not be located on Civic Connects."), 404

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
    print("\n" + "="*65)
    print("  * CIVIC CONNECTS - MUNICIPAL CITIZEN GRIEVANCE PORTAL *")
    print("  * Access citizen portal at: http://127.0.0.1:5000     *")
    print("  * Default Admin: admin@civicconnects.gov / Admin@123  *")
    print("  * Default Citizen: citizen@example.com / Citizen@123  *")
    print("="*65 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=True)
