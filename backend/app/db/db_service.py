import os
import sqlite3
import logging

logger = logging.getLogger(__name__)

# Locate the database file path relative to this file
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(CURRENT_DIR, "crm.db")

def get_db_connection():
    """Establishes and returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Returns rows as dictionary-like objects
    return conn

def init_db():
    """Initializes the database and creates the students table if it doesn't exist."""
    logger.info(f"Initializing database at {DB_PATH}")
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Create students table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL UNIQUE,
                preferred_university TEXT NOT NULL,
                call_status TEXT NOT NULL DEFAULT 'Pending',
                call_id TEXT
            )
        """)
        
        # Insert initial mock data if the table is empty
        cursor.execute("SELECT COUNT(*) FROM students")
        if cursor.fetchone()[0] == 0:
            mock_students = [
                ("Aditya Sharma", "+919876543210", "Apex University"),
                ("Rohan Gupta", "+919876543211", "Harvard University"),
                ("Sneha Reddy", "+919876543212", "Stanford University")
            ]
            cursor.executemany(
                "INSERT INTO students (name, phone, preferred_university) VALUES (?, ?, ?)",
                mock_students
            )
            conn.commit()
            logger.info("Inserted initial mock student records into the database.")
            
    except Exception as e:
        logger.exception("Failed to initialize database table")
    finally:
        conn.close()

def get_all_students():
    """Retrieves all student records from the database."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students ORDER BY id DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching students: {e}")
        return []
    finally:
        conn.close()

def get_student_by_id(student_id: int):
    """Retrieves a single student record by its database ID."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error fetching student by ID: {e}")
        return None
    finally:
        conn.close()

def add_student(name: str, phone: str, preferred_university: str):
    """Adds a new student record to the database."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO students (name, phone, preferred_university) VALUES (?, ?, ?)",
            (name.strip(), phone.strip(), preferred_university.strip())
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        logger.warning(f"Failed to add student: Phone number {phone} already exists.")
        raise ValueError("A student with this phone number already exists.")
    except Exception as e:
        logger.error(f"Error adding student: {e}")
        raise e
    finally:
        conn.close()

def update_call_status(student_id: int, status: str, call_id: str = None):
    """Updates the call status and call ID of a student."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if call_id:
            cursor.execute(
                "UPDATE students SET call_status = ?, call_id = ? WHERE id = ?",
                (status, call_id, student_id)
            )
        else:
            cursor.execute(
                "UPDATE students SET call_status = ? WHERE id = ?",
                (status, student_id)
            )
        conn.commit()
        logger.info(f"Updated student ID {student_id} status to '{status}' (Call ID: {call_id})")
    except Exception as e:
        logger.error(f"Error updating call status: {e}")
    finally:
        conn.close()


def delete_student(student_id: int):
    """Deletes a student record by its database ID."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
        conn.commit()
        logger.info(f"Deleted student ID {student_id} from database.")
        return True
    except Exception as e:
        logger.error(f"Error deleting student: {e}")
        return False
    finally:
        conn.close()


def get_db_stats():
    """Computes and returns student calling metrics from database."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM students")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM students WHERE LOWER(call_status) = 'pending'")
        pending = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM students WHERE LOWER(call_status) = 'calling'")
        calling = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM students WHERE LOWER(call_status) = 'failed'")
        failed = cursor.fetchone()[0]
        
        return {
            "total": total,
            "pending": pending,
            "calling": calling,
            "failed": failed
        }
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return {"total": 0, "pending": 0, "calling": 0, "failed": 0}
    finally:
        conn.close()
