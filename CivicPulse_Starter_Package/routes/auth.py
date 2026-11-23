from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import re
from db import execute_query

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('citizen.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        role = request.form.get('role', 'citizen').strip().lower()
        remember_me = request.form.get('remember_me')

        if not email or not password:
            flash('Please enter both email address and password.', 'danger')
            return render_template('auth/login.html', email=email, role=role)

        user = execute_query(
            "SELECT * FROM users WHERE email = %s AND role = %s",
            (email, role),
            one=True
        )

        if not user or not check_password_hash(user['password_hash'], password):
            cross_role_user = execute_query(
                "SELECT role FROM users WHERE email = %s",
                (email,),
                one=True
            )
            if cross_role_user and cross_role_user['role'] != role:
                flash(f"Account exists under the '{cross_role_user['role'].capitalize()}' portal. Please toggle role to {cross_role_user['role'].capitalize()}.", 'warning')
            else:
                flash('Invalid email address or password. Please verify credentials.', 'danger')
            return render_template('auth/login.html', email=email, role=role)

        session.clear()
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        session['user_email'] = user['email']
        session['role'] = user['role']
        if remember_me:
            session.permanent = True

        flash(f"Welcome back, {user['name']}!", 'success')
        
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
        
        if user['role'] == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('citizen.dashboard'))

    return render_template('auth/login.html', role=request.args.get('role', 'citizen'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('citizen.dashboard'))

    if request.method == 'POST':
        role = request.form.get('role', 'citizen').strip().lower()
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        admin_passkey = request.form.get('admin_passkey', '').strip()

        if not name or not email or not phone or not password:
            flash('All required fields must be completed.', 'danger')
            return render_template('auth/register.html', role=role, name=name, email=email, phone=phone, address=address)

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash('Please provide a valid email address.', 'danger')
            return render_template('auth/register.html', role=role, name=name, email=email, phone=phone, address=address)

        if password != confirm_password:
            flash('Passwords do not match. Please re-enter.', 'danger')
            return render_template('auth/register.html', role=role, name=name, email=email, phone=phone, address=address)

        if len(password) < 6:
            flash('Password must be at least 6 characters in length.', 'danger')
            return render_template('auth/register.html', role=role, name=name, email=email, phone=phone, address=address)

        if role == 'admin':
            MUNICIPAL_AUTH_KEY = "CIVIC-ADMIN-2026"
            if admin_passkey != MUNICIPAL_AUTH_KEY:
                flash('Invalid Municipal Authorization Key. For security, authority registration requires key "CIVIC-ADMIN-2026".', 'danger')
                return render_template('auth/register.html', role=role, name=name, email=email, phone=phone, address=address)

        existing_user = execute_query("SELECT id FROM users WHERE email = %s", (email,), one=True)
        if existing_user:
            flash('An account with this email address already exists. Please log in.', 'warning')
            return redirect(url_for('auth.login', role=role))

        password_hash = generate_password_hash(password)
        user_id = execute_query(
            """INSERT INTO users (name, email, phone, address, password_hash, role)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (name, email, phone, address, password_hash, role),
            commit=True
        )

        session.clear()
        session['user_id'] = user_id
        session['user_name'] = name
        session['user_email'] = email
        session['role'] = role

        flash(f'Registration successful! Welcome to Civic Connects, {name}.', 'success')
        if role == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('citizen.dashboard'))

    return render_template('auth/register.html', role=request.args.get('role', 'citizen'))

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been securely logged out. Thank you for using Civic Connects.', 'info')
    return redirect(url_for('index'))
