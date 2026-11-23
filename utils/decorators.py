from functools import wraps
from flask import session, redirect, url_for, flash, request

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function

def citizen_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in as a Citizen to continue.', 'warning')
            return redirect(url_for('auth.login', next=request.path))
        if session.get('role') != 'citizen':
            flash('Citizen credentials required to view this portal.', 'danger')
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in with Administrator credentials.', 'warning')
            return redirect(url_for('auth.login', next=request.path))
        if session.get('role') != 'admin':
            flash('Access denied. Administrator clearance is required.', 'danger')
            return redirect(url_for('citizen.dashboard'))
        return f(*args, **kwargs)
    return decorated_function
