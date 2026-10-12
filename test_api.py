"""Comprehensive automated tests for Students Database CRUD API & LLM Extension.

Features verified:
1. Isolated temporary SQLite database to guarantee real `students.db` is never modified.
2. Lifespan context execution via `with TestClient(app) as client:` to test automatic startup seeding.
3. Complete CRUD coverage (POST, GET list + filters, GET by ID, PATCH, DELETE).
4. Validation & error status codes (400, 404, 409, 422, 503).
5. Tested without GEMINI_API_KEY (expects 503), even if a .env file exists.

Run with:
    python test_api.py
or:
    pytest test_api.py -v
"""

import gc
import os
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

import database
from main import app


def run_all_tests():
    """Run all API endpoint test cases using an isolated temporary SQLite database."""
    # Create temporary database file (ignore_cleanup_errors for Windows file-locking quirks)
    temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    temp_db_path = Path(temp_dir.name) / "test_students.db"

    # Save original DB_PATH
    orig_db_path = database.DB_PATH
    database.DB_PATH = temp_db_path

    try:
        # User requirement 2: Use `with TestClient(app) as client:` so lifespan seeding runs
        with TestClient(app) as client:
            print("========================================")
            print(" RUNNING STUDENTS API AUTOMATED TESTS   ")
            print("========================================")

            # 1. Root / Health endpoint
            res = client.get("/")
            assert res.status_code == 200, f"Expected 200, got {res.status_code}"
            assert "Students API is running" in res.json()["message"]
            print("[PASS] GET / -> 200 OK")

            # 2. Startup Seeding Check (5 dummy students)
            res = client.get("/students")
            assert res.status_code == 200
            students = res.json()
            assert len(students) == 5, f"Expected 5 seeded students, got {len(students)}"
            seeded_names = [s["name"] for s in students]
            assert "Aarav Sen" in seeded_names
            assert "Kabir Basu" in seeded_names
            print(f"[PASS] Startup seed check -> 5 dummy students present: {seeded_names}")

            # 3. POST /students - Create valid student
            new_student_payload = {
                "name": "Priya Sharma",
                "date_of_birth": "2005-09-15",
                "email": "priya.sharma@example.com",
                "phone": "9888877777",
                "course": "Computer Science",
                "address": "Bengaluru",
                "enrollment_date": "2024-08-15"
            }
            res = client.post("/students", json=new_student_payload)
            assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.text}"
            created = res.json()
            student_id = created["id"]
            assert created["name"] == "Priya Sharma"
            assert created["email"] == "priya.sharma@example.com"
            print(f"[PASS] POST /students -> 201 Created (ID: {student_id})")

            # 4. POST /students - Validation error: missing both email and phone (422)
            invalid_payload = {
                "name": "No Contact Student",
                "date_of_birth": "2004-01-01"
            }
            res = client.post("/students", json=invalid_payload)
            assert res.status_code == 422, f"Expected 422, got {res.status_code}"
            print("[PASS] POST /students (missing email & phone) -> 422 Unprocessable Entity")

            # 5. POST /students - Duplicate email constraint (409)
            duplicate_email_payload = {
                "name": "Another Priya",
                "date_of_birth": "2005-09-15",
                "email": "priya.sharma@example.com",
                "phone": "9111122222"
            }
            res = client.post("/students", json=duplicate_email_payload)
            assert res.status_code == 409, f"Expected 409, got {res.status_code}"
            assert "already exists" in res.json()["detail"]
            print("[PASS] POST /students (duplicate email) -> 409 Conflict")

            # 6. GET /students - Filtering & Query params
            # 6a. Filter by name (partial match)
            res = client.get("/students?name=Aarav")
            assert res.status_code == 200
            data = res.json()
            assert len(data) == 1 and data[0]["name"] == "Aarav Sen"
            print("[PASS] GET /students?name=Aarav -> Filtered correctly")

            # 6b. Filter by course
            res = client.get("/students?course=Computer+Science")
            assert res.status_code == 200
            cs_students = res.json()
            assert len(cs_students) >= 2  # Aarav, Ishita, and newly added Priya
            assert all("Computer Science" in s["course"] for s in cs_students)
            print(f"[PASS] GET /students?course=Computer Science -> Found {len(cs_students)} matches")

            # 6c. Filter by born_after and born_before
            res = client.get("/students?born_after=2005-01-01&born_before=2007-01-01")
            assert res.status_code == 200
            filtered_by_dob = res.json()
            for s in filtered_by_dob:
                assert "2005-01-01" < s["date_of_birth"] < "2007-01-01"
            print(f"[PASS] GET /students?born_after=...&born_before=... -> {len(filtered_by_dob)} matched date bounds")

            # 6d. Pagination skip & limit
            res = client.get("/students?skip=1&limit=2")
            assert res.status_code == 200
            assert len(res.json()) == 2
            print("[PASS] GET /students?skip=1&limit=2 -> Pagination verified")

            # 7. GET /students/{student_id} - View single student
            res = client.get(f"/students/{student_id}")
            assert res.status_code == 200
            assert res.json()["name"] == "Priya Sharma"
            print(f"[PASS] GET /students/{student_id} -> 200 OK")

            # 7b. GET /students/{student_id} - Non-existent ID (404)
            res = client.get("/students/99999")
            assert res.status_code == 404
            assert res.json()["detail"] == "Student not found"
            print("[PASS] GET /students/99999 -> 404 Not Found")

            # 8. PATCH /students/{student_id} - Partial updates
            # 8a. Update single field
            update_payload = {"course": "AI & Machine Learning"}
            res = client.patch(f"/students/{student_id}", json=update_payload)
            assert res.status_code == 200
            assert res.json()["course"] == "AI & Machine Learning"
            assert res.json()["name"] == "Priya Sharma"  # Other fields preserved
            print(f"[PASS] PATCH /students/{student_id} -> 200 OK (course updated)")

            # 8b. Empty update payload (400 Bad Request)
            res = client.patch(f"/students/{student_id}", json={})
            assert res.status_code == 400
            assert "No fields to update" in res.json()["detail"]
            print(f"[PASS] PATCH /students/{student_id} with {{}} -> 400 Bad Request")

            # 8c. Update non-existent student (404)
            res = client.patch("/students/99999", json={"name": "Ghost"})
            assert res.status_code == 404
            print("[PASS] PATCH /students/99999 -> 404 Not Found")

            # 8d. Update with email conflict (409)
            res = client.patch(f"/students/{student_id}", json={"email": "aarav@example.com"})
            assert res.status_code == 409
            print("[PASS] PATCH /students/{student_id} with conflicting email -> 409 Conflict")

            # 9. DELETE /students/{student_id}
            # 9a. Delete existing student (204)
            res = client.delete(f"/students/{student_id}")
            assert res.status_code == 204
            print(f"[PASS] DELETE /students/{student_id} -> 204 No Content")

            # 9b. Verify deletion (404)
            res = client.get(f"/students/{student_id}")
            assert res.status_code == 404
            print(f"[PASS] GET /students/{student_id} after deletion -> 404 Not Found")

            # 9c. Delete already deleted / non-existent student (404)
            res = client.delete(f"/students/{student_id}")
            assert res.status_code == 404
            print(f"[PASS] DELETE /students/{student_id} on non-existent -> 404 Not Found")

            # 10. POST /ask - LLM Extension
            # 10a. Request validation: question length < 3 chars (422)
            res = client.post("/ask", json={"question": "hi"})
            assert res.status_code == 422
            print("[PASS] POST /ask with question < 3 chars -> 422 Unprocessable Entity")

            # 10b. User requirement: /ask test works with no GEMINI_API_KEY set (expects 503), even if .env exists
            original_api_key = os.environ.get("GEMINI_API_KEY")
            try:
                # Remove or empty out GEMINI_API_KEY
                os.environ.pop("GEMINI_API_KEY", None)

                res = client.post("/ask", json={"question": "Which students are studying Computer Science?"})
                assert res.status_code == 503, f"Expected 503 when API key is unset, got {res.status_code}"
                assert "GEMINI_API_KEY is not set" in res.json()["detail"]
                print("[PASS] POST /ask without GEMINI_API_KEY -> 503 Service Unavailable (gracefully handled)")
            finally:
                # Restore original key if one was present
                if original_api_key is not None:
                    os.environ["GEMINI_API_KEY"] = original_api_key

            print("========================================")
            print(" ALL TESTS PASSED SUCCESSFULLY! (100%)  ")
            print(" Real students.db was NOT touched.      ")
            print("========================================")

    finally:
        # Restore real DB_PATH and cleanup temp directory
        database.DB_PATH = orig_db_path
        gc.collect()
        try:
            temp_dir.cleanup()
        except Exception:
            pass


# Enables running directly via `python test_api.py` or with `pytest`
def test_all():
    run_all_tests()


if __name__ == "__main__":
    run_all_tests()
