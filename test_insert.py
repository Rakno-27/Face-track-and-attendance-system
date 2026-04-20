from app import app
from database import db
from models import Student
import random

def run():
    with app.app_context():
        # Create dummy student
        roll = f"TEST-ROLL-{random.randint(1000, 9999)}"
        s = Student(name="Test Sequence", roll_number=roll)
        db.session.add(s)
        db.session.commit()
        
        print(f"Generated Sequence Code: {s.student_code}")
        
        # Verify it persisted correctly
        s_db = Student.query.filter_by(roll_number=roll).first()
        print(f"DB Read Result: {s_db.student_code}")

if __name__ == "__main__":
    run()
