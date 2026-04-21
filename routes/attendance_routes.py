import datetime
from flask import Blueprint, request, jsonify, send_file, session
from database import db
from models import Student, Session, Subject, Attendance
import pandas as pd
import io

attendance_bp = Blueprint('attendance_bp', __name__)

@attendance_bp.route("/api/attendance", methods=["GET"])
def get_attendance():
    subject = request.args.get("subject", "").strip()
    date = request.args.get("date", "").strip()
    status = request.args.get("status", "").strip()
    search = request.args.get("search", "").strip()
    limit = int(request.args.get("limit", 300))

    with db.session.begin_nested() or db.session() as current_session:
        if status.lower() == 'absent':
            subq = db.session.query(Attendance.student_id, Attendance.session_id).subquery()
            
            query = db.session.query(
                Student.roll_number, Student.name, Session.date, Subject.name.label("subj_name"), Session.is_custom
            ).select_from(Student, Session).join(Subject, Session.subject_id == Subject.id)\
             .outerjoin(subq, db.and_(Student.id == subq.c.student_id, Session.id == subq.c.session_id))\
             .filter(subq.c.student_id == None)
             
            if subject: query = query.filter(Subject.name == subject)
            if date: query = query.filter(Session.date == date)
            if search: query = query.filter(db.or_(Student.name.ilike(f"%{search}%"), Student.roll_number.ilike(f"%{search}%")))

            results = query.limit(limit).all()
            return jsonify([{
                "student_id": str(r[0]), "name": r[1], "date": r[2], "subject": r[3],
                "lecture": "Custom" if r[4] else "Lecture", "time": "--:--:--",
                "status": "Absent", "confidence": 0.0
            } for r in results])
            
        else:
            query = db.session.query(
                Student.roll_number, Student.name, Session.date, 
                Subject.name.label("subj_name"), Session.is_custom, 
                Attendance.timestamp, Attendance.status
            ).join(Attendance, Student.id == Attendance.student_id)\
             .join(Session, Attendance.session_id == Session.id)\
             .join(Subject, Session.subject_id == Subject.id)

            if subject: query = query.filter(Subject.name == subject)
            if date: query = query.filter(Session.date == date)
            if status and status.lower() != 'recorded only': query = query.filter(Attendance.status.ilike(status))
            if search: query = query.filter(db.or_(Student.name.ilike(f"%{search}%"), Student.roll_number.ilike(f"%{search}%")))

            results = query.order_by(Attendance.timestamp.desc()).limit(limit).all()
            return jsonify([{
                "student_id": str(r[0]), "name": r[1], "date": r[2], "subject": r[3],
                "lecture": "Custom" if r[4] else "Lecture", 
                "time": r[5].strftime("%H:%M:%S") if hasattr(r[5], 'strftime') else (str(r[5])[11:19] if r[5] and len(str(r[5])) > 18 else "00:00:00"),
                "status": r[6], "confidence": 99.0
            } for r in results])

@attendance_bp.route("/api/attendance/summary", methods=["GET"])
def summary():
    subject = request.args.get("subject", "")
    today = datetime.date.today().isoformat()

    query = db.session.query(Attendance.id).join(Session).join(Subject).filter(Session.date == today)
    if subject: query = query.filter(Subject.name == subject)
    
    present_count = query.count()
    total = Student.query.count()
    records_q = db.session.query(
        Student.roll_number, Student.name, Subject.name.label("subj"),
        Session.is_custom, Attendance.timestamp, Attendance.status
    ).join(Attendance, Student.id == Attendance.student_id)\
     .join(Session, Attendance.session_id == Session.id)\
     .join(Subject, Session.subject_id == Subject.id)\
     .filter(Session.date == today)
     
    if subject: records_q = records_q.filter(Subject.name == subject)
    
    records_res = records_q.order_by(Attendance.timestamp.desc()).limit(15).all()
    
    rec_list = []
    for r in records_res:
        rec_list.append({
            "student_id": str(r[0]),
            "name": r[1],
            "subject": r[2],
            "lecture": "Custom" if r[3] else "Lecture",
            "time": r[4].strftime("%H:%M:%S") if hasattr(r[4], 'strftime') else (str(r[4])[11:19] if r[4] and len(str(r[4])) > 18 else "00:00:00"),
            "confidence": 99.0,
            "status": r[5]
        })
        
    return jsonify({
        "date": today, "subject": subject,
        "present": present_count,
        "total_students": total,
        "absent": max(total - present_count, 0),
        "rate": round((present_count / total * 100), 1) if total > 0 else 0,
        "records": rec_list
    })

@attendance_bp.route("/export/<fmt>", methods=["GET"])
def export_file(fmt):
    if fmt not in ["csv", "excel"]: return jsonify({"error": "Invalid format"}), 400
    if session.get('role') != 'admin': return jsonify({"error": "Unauthorized"}), 403
    
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    subject = request.args.get("subject", "").strip()
    student = request.args.get("student", "").strip()
    status = request.args.get("status", "").strip()
    
    if status.lower() == 'absent':
        subq = db.session.query(Attendance.student_id, Attendance.session_id).subquery()
        query = db.session.query(
            Student.name.label('Student Name'),
            Student.roll_number.label('Roll Number'),
            Subject.name.label('Subject'),
            Session.date.label('Date'),
            db.literal_column("'Absent'").label('Status')
        ).select_from(Student, Session).join(Subject, Session.subject_id == Subject.id)\
         .outerjoin(subq, db.and_(Student.id == subq.c.student_id, Session.id == subq.c.session_id))\
         .filter(subq.c.student_id == None)
         
        if start_date: query = query.filter(Session.date >= start_date)
        if end_date: query = query.filter(Session.date <= end_date)
        if subject: query = query.filter(Subject.name == subject)
        if student: query = query.filter(db.or_(Student.name.ilike(f"%{student}%"), Student.roll_number.ilike(f"%{student}%")))
            
        records = query.all()
        
    else:
        query = db.session.query(
            Student.name.label('Student Name'),
            Student.roll_number.label('Roll Number'),
            Subject.name.label('Subject'),
            Session.date.label('Date'),
            Attendance.status.label('Status')
        ).join(Attendance, Student.id == Attendance.student_id)\
         .join(Session, Attendance.session_id == Session.id)\
         .join(Subject, Session.subject_id == Subject.id)
         
        if start_date: query = query.filter(Session.date >= start_date)
        if end_date: query = query.filter(Session.date <= end_date)
        if subject: query = query.filter(Subject.name == subject)
        if status and status.lower() != 'recorded only': query = query.filter(Attendance.status.ilike(status))
        if student: query = query.filter(db.or_(Student.name.ilike(f"%{student}%"), Student.roll_number.ilike(f"%{student}%")))
            
        records = query.all()
        
    df = pd.DataFrame(records, columns=['Student Name', 'Roll Number', 'Subject', 'Date', 'Status'])
    
    if fmt == "csv":
        out = io.StringIO()
        df.to_csv(out, index=False)
        buf = io.BytesIO(out.getvalue().encode())
        buf.seek(0)
        return send_file(buf, mimetype="text/csv", as_attachment=True, download_name="attendance_export.csv")
    else:
        out = io.BytesIO()
        df.to_excel(out, index=False, engine='openpyxl')
        out.seek(0)
        return send_file(out, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="attendance_export.xlsx")
