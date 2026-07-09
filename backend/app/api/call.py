from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.mcube_service import MCubeService
from app.db.db_service import (
    get_all_students,
    get_student_by_id,
    add_student,
    update_call_status,
    delete_student,
    get_db_stats
)

router = APIRouter(prefix="/api")
mcube = MCubeService()

# Schema for adding a new student
class StudentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=5)
    preferred_university: str = Field(..., min_length=1)

# Endpoint to fetch all student records
@router.get("/students")
def get_students_list():
    students = get_all_students()
    return students

# Endpoint to add a new student (Admin Panel Query)
@router.post("/students")
def create_student(req: StudentCreateRequest):
    try:
        student_id = add_student(req.name, req.phone, req.preferred_university)
        return {
            "id": student_id,
            "name": req.name,
            "phone": req.phone,
            "preferred_university": req.preferred_university,
            "call_status": "Pending"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to insert student record.")

# Endpoint to trigger a call to a student by ID
@router.post("/students/{student_id}/call")
def trigger_call_to_student(student_id: int):
    student = get_student_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")
        
    try:
        # Trigger outbound call via MCube Click-to-Call
        call_id = mcube.make_call(student["phone"])
        
        # Update call status in SQLite database
        update_call_status(student_id, "Calling", call_id)
        
        return {
            "status": "Calling",
            "student_id": student_id,
            "call_id": call_id
        }
    except Exception as e:
        # If call fails, update status to Failed in database
        update_call_status(student_id, "Failed")
        raise HTTPException(status_code=500, detail=f"Failed to trigger MCube call: {str(e)}")


# Endpoint to delete a student
@router.delete("/students/{student_id}")
def delete_student_record(student_id: int):
    success = delete_student(student_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete student record.")
    return {"status": "Success", "message": f"Deleted student ID {student_id}"}


# Endpoint to fetch database stats
@router.get("/stats")
def get_dashboard_stats():
    return get_db_stats()