"""Main FastAPI application for the Students Database CRUD Application.

This file defines the FastAPI application instance, lifespan events, and all REST endpoints:
- GET / : Root endpoint providing API status and link to docs
- POST /students : Create a new student (201 Created)
- GET /students : List students with filtering, search, and pagination (200 OK)
- GET /students/{student_id} : Retrieve a single student by ID (200 OK or 404 Not Found)
- PATCH /students/{student_id} : Partially update student fields (200 OK, 400 Bad Request, 404 Not Found, 409 Conflict)
- DELETE /students/{student_id} : Delete a student by ID (204 No Content or 404 Not Found)
- POST /ask : Ask natural language questions about students using Google Gemini
"""

import os
import sqlite3
from contextlib import asynccontextmanager
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Response

from database import get_conn, init_db, seed_if_empty
from llm import ask_about_students
from schemas import AskRequest, AskResponse, StudentCreate, StudentOut, StudentUpdate

# Load environment variables (.env file)
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI Lifespan Context Manager.

    Executes on application startup:
    1. Ensures the SQLite table schema exists (`init_db`).
    2. Seeds 5 realistic dummy student records if table is empty (`seed_if_empty`).
    """
    init_db()
    seed_if_empty()
    yield


# Initialize FastAPI application
app = FastAPI(
    title="Students Database API",
    description="Backend CRUD API with LLM Question-Answering using Google Gemini and n8n webhook integration.",
    version="1.0",
    lifespan=lifespan,
)


def notify_n8n(student: dict):
    """Optional Background Task: Sends new student payload to an n8n webhook URL.

    Runs in the background after the response is returned to the user,
    preventing any external network delay or failure from affecting the client.
    """
    url = os.getenv("N8N_WEBHOOK_URL")
    if not url:
        return
    try:
        httpx.post(url, json=student, timeout=10)
    except Exception as e:
        print("n8n webhook failed:", e)


# ---------- ROOT / HEALTH ----------
@app.get("/", summary="API Health / Home")
def home():
    """Welcoming endpoint with link to the interactive documentation."""
    return {"message": "Students API is running. Open /docs to test it."}


# ---------- CREATE ----------
@app.post("/students", response_model=StudentOut, status_code=201, summary="Create a new student")
def create_student(student: StudentCreate, background: BackgroundTasks):
    """Create a new student record in the database.

    - Validates fields via Pydantic (`StudentCreate`).
    - Enforces unique email constraint (returns 409 Conflict if duplicate).
    - Triggers non-blocking background task to notify n8n if configured.
    """
    data = student.model_dump(mode="json")
    cols = ", ".join(data.keys())
    placeholders = ", ".join("?" for _ in data)
    try:
        with get_conn() as conn:
            cur = conn.execute(
                f"INSERT INTO students ({cols}) VALUES ({placeholders})", list(data.values())
            )
            row = conn.execute("SELECT * FROM students WHERE id = ?", (cur.lastrowid,)).fetchone()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="A student with this email already exists")

    result = dict(row)
    background.add_task(notify_n8n, result)
    return result


# ---------- READ (list + filter) ----------
@app.get("/students", response_model=list[StudentOut], summary="List and filter students")
def list_students(
    name: Optional[str] = Query(None, description="Partial search for student name"),
    course: Optional[str] = Query(None, description="Partial search for course/department"),
    born_after: Optional[str] = Query(None, description="Filter students born after date (YYYY-MM-DD)"),
    born_before: Optional[str] = Query(None, description="Filter students born before date (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0, description="Pagination offset (records to skip)"),
    limit: int = Query(50, ge=1, le=200, description="Pagination limit (max records to return)"),
):
    """Retrieve a list of student records with optional search filters and pagination."""
    sql, params = "SELECT * FROM students WHERE 1=1", []
    if name:
        sql += " AND name LIKE ?"
        params.append(f"%{name}%")
    if course:
        sql += " AND course LIKE ?"
        params.append(f"%{course}%")
    if born_after:
        sql += " AND date_of_birth > ?"
        params.append(born_after)
    if born_before:
        sql += " AND date_of_birth < ?"
        params.append(born_before)
    sql += " ORDER BY id LIMIT ? OFFSET ?"
    params += [limit, skip]
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


# ---------- READ (one) ----------
@app.get("/students/{student_id}", response_model=StudentOut, summary="Get student details by ID")
def get_student(student_id: int):
    """Retrieve details for a single student by their unique ID."""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Student not found")
    return dict(row)


# ---------- UPDATE ----------
@app.patch("/students/{student_id}", response_model=StudentOut, summary="Partially update a student")
def update_student(student_id: int, update: StudentUpdate):
    """Partially update only the fields sent in the request body.

    - Returns 400 Bad Request if no fields are provided in the payload.
    - Returns 404 Not Found if the student ID does not exist.
    - Returns 409 Conflict if attempting to update email to an already existing email.
    """
    changes = update.model_dump(mode="json", exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No fields to update")

    sets = ", ".join(f"{k} = ?" for k in changes)
    try:
        with get_conn() as conn:
            cur = conn.execute(
                f"UPDATE students SET {sets} WHERE id = ?", [*changes.values(), student_id]
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Student not found")
            row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="A student with this email already exists")
    return dict(row)


# ---------- DELETE ----------
@app.delete("/students/{student_id}", status_code=204, summary="Delete a student by ID")
def delete_student(student_id: int):
    """Delete a student record by ID.

    - Returns 204 No Content on successful deletion.
    - Returns 404 Not Found if the student does not exist.
    """
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Student not found")
    return Response(status_code=204)


# ---------- LLM ----------
@app.post("/ask", response_model=AskResponse, summary="Ask questions about students via Google Gemini")
def ask(req: AskRequest):
    """Query Google Gemini with student data context.

    - Backend extracts SQLite student data.
    - Data is passed strictly as context to Gemini.
    - Model answers only using provided database facts.
    - Returns 503 if GEMINI_API_KEY is not configured.
    - Returns 502 if the Gemini API call encounters an upstream issue.
    """
    try:
        return {"answer": ask_about_students(req.question)}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")
