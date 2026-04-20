import sqlite3

def patch():
    conn = sqlite3.connect('instance/facetrack.db')
    cursor = conn.cursor()
    
    # Check if student_code exists
    cursor.execute("PRAGMA table_info(student)")
    cols = [c[1] for c in cursor.fetchall()]
    
    if "student_code" not in cols:
        cursor.execute("ALTER TABLE student ADD COLUMN student_code VARCHAR(20);")
        cursor.execute("CREATE UNIQUE INDEX ix_student_student_code ON student (student_code);")
        print("Added student_code column natively.")
        
    if "created_at" not in cols:
        cursor.execute("ALTER TABLE student ADD COLUMN created_at DATETIME;")
        print("Added created_at column natively.")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    patch()
