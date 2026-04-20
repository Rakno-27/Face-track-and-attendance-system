from flask import Blueprint, request, render_template, redirect, url_for, session
from auth import verify_and_login, logout_user

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        # Localized validation handling the exclusion block securely tracking state bounds.
        req_token = request.form.get('csrf_token')
        if not req_token or req_token != session.get('csrf_token'):
            return "CSRF Token Validation Automatically Forcibly Failed.", 403

        username = request.form.get('username')
        password = request.form.get('password')
        
        # Trigger our backend logic (returns boolean success and message)
        success, msg = verify_and_login(username, password)
        if success:
            # Extract dynamically injected role from Flask Session
            role = session.get('role')
            if role == 'admin':
                return redirect('/admin')
            else:
                return redirect('/attendance')
        else:
            error = msg
            
    # Bridge rendering flawlessly natively securely into FaceTrack's minimal CSS
    return render_template('login.html', error=error)

@auth_bp.route('/logout')
def logout():
    # Safely clear the server-side credentials
    logout_user()
    return redirect(url_for('auth.login'))
