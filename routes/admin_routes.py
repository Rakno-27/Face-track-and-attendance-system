from flask import Blueprint, request, jsonify, session
from database import db
from models import Student, Session, Subject, Attendance
import logging
from sqlalchemy import func

admin_bp = Blueprint('admin_bp', __name__)

@admin_bp.route("/api/admin/reset", methods=["DELETE"])
def admin_reset():
    Attendance.query.delete()
    db.session.commit()
    from services.attendance_service import clear_attendance_cache
    clear_attendance_cache()
    return jsonify({"success": True, "message": "Attendance SQLite explicitly flushed."})

@admin_bp.route("/api/admin/attendance/session", methods=["DELETE"])
def admin_reset_session():
    data = request.json or {}
    subject = data.get("subject", "")
    date = data.get("date", "")
    
    if not subject or not date: return jsonify({"error": "Subject and Date are strictly required"}), 400
        
    subj_q = Subject.query.filter_by(name=subject).first()
    if not subj_q: return jsonify({"error": "Subject tightly scoped missing"}), 404
    sess = Session.query.filter_by(subject_id=subj_q.id, date=date).all()
    sess_ids = [s.id for s in sess]
    
    if sess_ids:
        deleted_count = Attendance.query.filter(Attendance.session_id.in_(sess_ids)).delete(synchronize_session=False)
        db.session.commit()
        from services.attendance_service import clear_attendance_cache
        clear_attendance_cache()
    else:
        deleted_count = 0
            
    logging.info(f"Admin explicitly bounded DB wipe: {subject} on {date}. Blocked {deleted_count} IDs.")
    return jsonify({"success": True, "message": f"Cleared {deleted_count} records cleanly natively.", "count": deleted_count})

@admin_bp.route("/api/admin/encodings", methods=["DELETE"])
def admin_clear_encodings():
    for s in Student.query.filter(Student.encoding.isnot(None)).all():
        s.encoding = None
    db.session.commit()
    
    from flask import current_app
    from services.face_service import reload_cache
    reload_cache(current_app)
    
    logging.info("Admin definitively cleared SQL ORM vectors globally.")
    return jsonify({"success": True, "message": "All face encodings permanently dropped bounding constraints."})

@admin_bp.route("/api/admin/custom_sessions", methods=["GET"])
def get_custom_sessions():
    customs = []
    for sess in Session.query.filter_by(is_custom=True).all():
        subj = Subject.query.get(sess.subject_id)
        customs.append({
            "id": str(sess.id),
            "date": sess.date,
            "start": sess.start_time,
            "end": sess.end_time,
            "subject": subj.name if subj else "Custom",
            "lecture": "Custom",
            "is_custom": True
        })
    return jsonify(customs)

@admin_bp.route("/api/admin/custom_sessions", methods=["POST"])
def add_custom_session():
    data = request.json
    subj_name = data.get("subject", "Custom Override")
    subj = Subject.query.filter_by(name=subj_name).first()
    if not subj:
        subj = Subject(name=subj_name, code=subj_name)
        db.session.add(subj)
        db.session.commit()
        
    new_session = Session(
        subject_id=subj.id,
        start_time=data.get("start"),
        end_time=data.get("end"),
        date=data.get("date"),
        is_custom=True
    )
    db.session.add(new_session)
    db.session.commit()
    return jsonify({"success": True})

@admin_bp.route("/api/admin/custom_sessions/<sid>", methods=["DELETE"])
def delete_custom_session(sid):
    if not str(sid).isdigit(): return jsonify({"success": True})
    s = Session.query.get(int(sid))
    if s and s.is_custom:
        db.session.delete(s)
        db.session.commit()
    return jsonify({"success": True})

@admin_bp.route("/api/admin/analytics_data", methods=["GET"])
def analytics_data():
    if session.get('role') != 'admin':
        return jsonify({"error": "Unauthorized"}), 403
        
    t_students = Student.query.count()
    t_sessions = Session.query.count()
    t_attendance = Attendance.query.count()
    
    avg_att = 0
    if t_students > 0 and t_sessions > 0:
        avg_att = round((t_attendance / (t_students * t_sessions)) * 100, 1)

    subj_q = db.session.query(Subject.name, func.count(Attendance.id)).join(Session, Attendance.session_id == Session.id).join(Subject, Session.subject_id == Subject.id).group_by(Subject.name).all()
    subj_labels = [row[0] for row in subj_q]
    subj_data = [row[1] for row in subj_q]

    date_q = db.session.query(func.substr(Attendance.timestamp, 1, 10), func.count(Attendance.id)).group_by(func.substr(Attendance.timestamp, 1, 10)).order_by(func.substr(Attendance.timestamp, 1, 10)).limit(14).all()
    date_labels = [row[0] for row in date_q]
    date_data = [row[1] for row in date_q]

    stu_q = db.session.query(Student.name, func.count(Attendance.id)).join(Attendance, Student.id == Attendance.student_id).group_by(Student.name).order_by(func.count(Attendance.id).desc()).limit(15).all()
    stu_labels = [row[0] for row in stu_q]
    stu_data = [row[1] for row in stu_q]

    return jsonify({
        "metrics": {"total_students": t_students, "total_sessions": t_sessions, "total_attendance": t_attendance, "avg_attendance": avg_att},
        "subject_chart": {"labels": subj_labels, "data": subj_data},
        "daily_chart": {"labels": date_labels, "data": date_data},
        "student_chart": {"labels": stu_labels, "data": stu_data}
    })
