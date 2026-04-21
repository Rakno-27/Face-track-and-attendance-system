import datetime
from database import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='teacher')  # 'admin' or 'teacher'

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_code = db.Column(db.String(20), unique=True, index=True, nullable=True)
    name = db.Column(db.String(100), nullable=False)
    roll_number = db.Column(db.String(50), unique=True, nullable=False)
    encoding = db.Column(db.LargeBinary, nullable=True)  # Stored as BLOB via bytes format
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

from sqlalchemy import event, select

@event.listens_for(Student, "before_insert")
def generate_student_code(mapper, connection, target):
    if not target.student_code:
        prefix = "STU"
        stmt = select(Student.student_code).where(
            Student.student_code.like(f"{prefix}%")
        ).order_by(Student.student_code.desc()).limit(1)
        
        result = connection.execute(stmt).scalar()
        if result:
            try:
                last_num = int(result[3:])
                new_num = last_num + 1
            except ValueError:
                new_num = 1
        else:
            new_num = 1
            
        target.student_code = f"{prefix}{new_num:03d}"

def bulk_generate_student_codes(count=1):
    """
    Statically binds safe sequence ranges dynamically cleanly bypassing uncommitted flushes securely natively.
    """
    prefix = "STU"
    stmt = select(Student.student_code).where(
        Student.student_code.like(f"{prefix}%")
    ).order_by(Student.student_code.desc()).limit(1)
    
    result = db.session.execute(stmt).scalar()
    if result:
        try:
            last_num = int(result[3:])
        except ValueError:
            last_num = 0
    else:
        last_num = 0

    codes = []
    for i in range(1, count + 1):
        codes.append(f"{prefix}{(last_num + i):03d}")
    return codes

def roll_number_to_student_code(roll_number):
    """
    Extracts native SQL mapping cleanly verifying active bounding cleanly implicitly.
    """
    s = Student.query.filter_by(roll_number=str(roll_number)).first()
    if s and s.student_code:
        return s.student_code
    return "Student not registered"

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), nullable=False)

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    start_time = db.Column(db.String(20), nullable=False)
    end_time = db.Column(db.String(20), nullable=False)
    is_custom = db.Column(db.Boolean, default=False, nullable=False)
    date = db.Column(db.String(20), nullable=False)
    
    subject = db.relationship('Subject', backref=db.backref('sessions', lazy=True))

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='present')

    student = db.relationship('Student', backref=db.backref('attendances', lazy=True))
    session = db.relationship('Session', backref=db.backref('attendances', lazy=True))
