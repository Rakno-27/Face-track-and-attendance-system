from flask import Blueprint, request, jsonify
from models import Student
from database import db
import datetime

student_api = Blueprint('student_api', __name__)

@student_api.route('/api/students', methods=['GET'])
def get_students():
    students = Student.query.all()
    out = []
    for s in students:
        out.append({
            "student_id": str(s.id),
            "name": s.name,
            "department": s.roll_number,
            "roll_number": s.roll_number,
            "samples": 5 if s.encoding else 0,
            "created": "SQL Native"
        })
    return jsonify(out)

@student_api.route('/api/students', methods=['POST'])
def add_student():
    data = request.json
    sid = data.get("student_id")
    if not sid: return jsonify({"error": "Missing ID"}), 400
    
    if Student.query.filter_by(roll_number=sid).first() or Student.query.get(sid) if sid.isdigit() else None:
        return jsonify({"error": "Student ID exists"}), 400
        
    s = Student(name=data.get("name",""), roll_number=sid)
    db.session.add(s)
    db.session.commit()
    return jsonify({"success": True})

@student_api.route('/api/students/<sid>', methods=['DELETE'])
def delete_student(sid):
    s = Student.query.filter_by(roll_number=sid).first() or (Student.query.get(int(sid)) if sid.isdigit() else None)
    if s:
        db.session.delete(s)
        db.session.commit()
    return jsonify({"success": True})

@student_api.route('/api/students/<sid>/stats', methods=['GET'])
def student_stats(sid):
    return jsonify({
        "total_sessions": 0,
        "attended": 0,
        "percentage": "0.0",
        "last_seen": "N/A",
        "status":"Good"
    })
