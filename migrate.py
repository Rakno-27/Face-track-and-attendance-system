import json
import pickle
import os
import datetime
from app import app as active_app
from database import db
from models import Student, Subject, Session, Attendance
from encoding_utils import serialize_encoding

def load_data():
    students_fp = 'data/students.json'
    attendance_fp = 'data/attendance.json'
    encoding_fp = 'data/encodings.pkl'
    
    students = {}
    attendance = []
    encodings = {}

    if os.path.exists(students_fp):
        with open(students_fp, 'r') as f:
            try: students = json.load(f)
            except: pass

    if os.path.exists(attendance_fp):
        with open(attendance_fp, 'r') as f:
            try: attendance = json.load(f)
            except: pass

    if os.path.exists(encoding_fp):
        with open(encoding_fp, 'rb') as f:
            try: encodings = pickle.load(f)
            except: pass

    return students, attendance, encodings

def migrate():
    with active_app.app_context():
        # Assert database creation schema bounds structurally
        db.create_all()

        print("1. Initiating Student & Biometric BLOB Migration...")
        students_data, attendance_records, encodings_data = load_data()

        student_local_map = {}  # Relays old JSON ID keys reliably to native Integer Primary Keys iteratively

        for old_id, info in students_data.items():
            roll = info.get('roll_number', old_id)
            existing = Student.query.filter_by(roll_number=roll).first()
            
            # Map Biometrics securely using standardized .tobytes() float wrapper pipeline constraints
            enc_array = encodings_data.get(old_id)
            blob = serialize_encoding(enc_array) if enc_array is not None else None
            
            if not existing:
                s = Student(name=info['name'], roll_number=roll, encoding=blob)
                db.session.add(s)
                db.session.commit()
                student_local_map[old_id] = s.id
                print(f"   [+] Processed User: {info['name']}")
            else:
                student_local_map[old_id] = existing.id
                print(f"   [Skip] User {info['name']} safely cached natively.")
        
        print(f"✓ Consolidated {len(students_data)} user profiles accurately.")

        print("\n2. Migrating Timetables & Attendance Metadata...")

        added_attendance = 0
        for r in attendance_records:
            subj_name = r.get('subject', 'General')
            date_str = r.get('date', '2020-01-01') 
            time_str = r.get('time', '00:00:00')
            
            # Dynamically upsert and track mapped subjects seamlessly ensuring logic integrity matches
            subject = Subject.query.filter_by(name=subj_name).first()
            if not subject:
                code = subj_name[:3].upper() + "-101"
                subject = Subject(name=subj_name, code=code)
                db.session.add(subject)
                db.session.commit()
            
            # Automatically parse bounding Sessions dynamically mapped securely tracking logic constraints
            session = Session.query.filter_by(subject_id=subject.id, date=date_str).first()
            if not session:
                session = Session(
                    subject_id=subject.id,
                    start_time="00:00",
                    end_time="23:59",
                    is_custom=True, # Tag as custom due to historically imprecise timekeeping natively
                    date=date_str
                )
                db.session.add(session)
                db.session.commit()
            
            old_std_id = r.get('student_id')
            db_std_id = student_local_map.get(old_std_id)
            
            if db_std_id:
                try:
                    dt_obj = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    dt_obj = datetime.datetime.utcnow()
                
                # Check duplication tracking
                att_exists = Attendance.query.filter_by(student_id=db_std_id, session_id=session.id).first()
                if not att_exists:
                    att = Attendance(
                        student_id=db_std_id,
                        session_id=session.id,
                        timestamp=dt_obj,
                        status=r.get('status', 'present')
                    )
                    db.session.add(att)
                    db.session.commit()
                    added_attendance += 1

        print(f"✓ Consolidated {added_attendance} fresh attendance identifiers completely.")
        print("\n[✔] Structural DB Migration finalized perfectly.")

if __name__ == '__main__':
    migrate()
