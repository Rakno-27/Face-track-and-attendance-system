import os
import time
import base64
import logging
import cv2
import numpy as np
import datetime
import secrets
from io import BytesIO
from PIL import Image
from datetime import timedelta
from flask import Flask, render_template, request, jsonify, Response, session, redirect

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# ─── Database Configuration ──────────────────────────────────────
from database import db
from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///facetrack.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'connect_args': {'timeout': 30}}
db.init_app(app)

# ─── Auth Ints ───────────────────────────────────────────────────
app.secret_key = 'facetrack_secure_session_key'
app.permanent_session_lifetime = timedelta(minutes=60)

# ─── Blueprints ──────────────────────────────────────────────────
from routes.auth_routes import auth_bp
from routes.student_routes import student_bp
from routes.attendance_routes import attendance_bp
from routes.admin_routes import admin_bp

app.register_blueprint(auth_bp)
app.register_blueprint(student_bp)
app.register_blueprint(attendance_bp)
app.register_blueprint(admin_bp)

@app.before_request
def restrict_access():
    session.permanent = True
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
        
    if request.method in ['POST', 'DELETE']:
        if request.endpoint not in ['auth.login', 'auth.logout']:
            req_token = request.headers.get('X-CSRFToken') or request.form.get('csrf_token')
            if not req_token or req_token != session.get('csrf_token'):
                return jsonify({"error": "CSRF validation securely failed"}), 403

    allowed_routes = ['auth.login', 'auth.logout', 'static']
    
    if request.endpoint not in allowed_routes and 'user_id' not in session:
        if request.path.startswith('/api/'):
            return jsonify({"error": "Unauthorized"}), 401
        return redirect('/login')
        
    if request.path.startswith('/api/admin/') or request.path.startswith('/settings') or request.path == '/admin':
        if session.get('role') != 'admin':
            return jsonify({"error": "Administrative privileges inherently required."}), 403

# ─── Initialization ──────────────────────────────────────────────
with app.app_context():
    db.create_all()

from services.face_service import reload_cache, identify_frame
with app.app_context():
    reload_cache(app)

from services.video_service import CameraManager
camera_manager = CameraManager(app=app)

from services.attendance_service import get_current_session, get_daily_schedule, mark_attendance

# ─── Render Routes ───────────────────────────────────────────────
@app.route("/")
def index():
    if 'user_id' in session:
        return redirect('/admin' if session.get('role') == 'admin' else '/attendance')
    return redirect('/login')

@app.route("/admin")
def admin_dash():
    if session.get('role') != 'admin':
        return redirect('/attendance')
    return render_template("index.html", role="admin", user=session.get('username'))

@app.route("/admin/analytics")
def analytics_dash():
    if session.get('role') != 'admin':
        return redirect('/attendance')
    return render_template("analytics.html", role="admin", user=session.get('username'))

@app.route("/settings")
def settings_strict_block():
    if session.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
    return redirect('/admin')

@app.route("/attendance")
def teacher_dash():
    return render_template("index.html", role="teacher", user=session.get('username'))

# ─── Camera & Timetable APIs ─────────────────────────────────────
@app.route("/api/camera/start", methods=["POST"])
def start_camera():
    camera_manager.start()
    return jsonify({"success": True})

@app.route("/api/camera/stop", methods=["POST"])
def stop_camera():
    camera_manager.stop()
    return jsonify({"success": True})

def gen_frames():
    while True:
        frame = camera_manager.wait_and_get_frame()
        if frame is None:
            time.sleep(0.05)
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
               
@app.route("/video_feed")
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/api/timetable/current", methods=["GET"])
def get_timetable_current():
    return jsonify(get_current_session(app=app))

@app.route("/api/timetable/daily", methods=["GET"])
def get_timetable_daily():
    now = datetime.datetime.now()
    day_name = now.strftime("%A")
    schedule = get_daily_schedule(now, app=app)
    is_weekend = day_name in ["Saturday", "Sunday"] and len(schedule) == 0
    return jsonify({
        "day": day_name,
        "is_weekend": is_weekend,
        "server_time": now.isoformat(),
        "schedule": schedule
    })

@app.route("/api/identify", methods=["POST"])
def identify():
    b64 = request.json.get("image_base64", "")
    
    session_info = get_current_session(app=app)
    if session_info["status"] != "open":
        return jsonify({"faces": [], "marked": [], "error": session_info["msg"]}), 400

    subject = session_info["session"]["subject"]
    lecture = session_info["session"]["lecture"]
    start_time = session_info["session"]["start"]
    end_time = session_info["session"]["end"]

    raw = base64.b64decode(b64.split(",")[-1])
    img = Image.open(BytesIO(raw)).convert("RGB")
    frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    h, w = frame.shape[:2]
    if w > 640:
        scale = 640 / w
        frame = cv2.resize(frame, (0, 0), fx=scale, fy=scale)

    try:
        results = identify_frame(frame)
    except Exception as e:
        logging.error(f"Error during manual identification: {e}")
        return jsonify({"faces": [], "marked": [], "error": "Internal processing error. Check logs."}), 500

    marked = []

    for r in results:
        if r["recognized"]:
            ok, msg = mark_attendance(
                r["student_id"], r["name"], r["confidence"],
                subject, lecture, start_time, end_time, app
            )
            r["marked"] = ok
            r["msg"] = msg
            if ok:
                marked.append(r["name"])

    return jsonify({"faces": results, "marked": marked})

# ─── Run ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000, threaded=True)