  ## 🔴 Live Demo
  **API Docs:** https://student-api-y5uu.onrender.com/docs

# HEAD
# Students Database CRUD Application with LLM Extensio
  - `GET /students` - List all students with query filters (`name`, `course`, `born_after`, `born_before`, `skip`, `limit`).
  - `GET /students/{student_id}` - Retrieve details for a single student.
  - `PATCH /students/{student_id}` - Partial updates (only modifies provided fields, returns 400 for empty payloads).
  - `DELETE /students/{student_id}` - Delete student records with HTTP 204 response.
- **Automatic Startup Seeding**: Automatically sen

A backend REST API built with **FastAPI**, **SQLite**, and **Google Gemini** for the **EWB Edu Tech internship assignment**.

This application provides complete CRUD operations for managing student records, supports advanced filtering and pagination, offers optional background webhook notifications for **n8n**, and features an intelligent **LLM-powered question answering endpoint** powered by Google's official `google-genai` SDK with strict data grounding.

---

## Table of Contents

- [Features](#features)
- [Architecture & Security](#architecture--security)
- [Prerequisites](#prerequisites)
- [Project Structure](#project-structure)
- [Installation & Setup](#installation--setup)
- [How to Get a Gemini API Key](#how-to-get-a-gemini-api-key)
- [Configuring the Environment (`.env`)](#configuring-the-environment-env)
- [Running the Application](#running-the-application)
- [Interactive API Documentation (Swagger / OpenAPI)](#interactive-api-documentation-swagger--openapi)
- [Sample cURL Commands for Testing](#sample-curl-commands-for-testing)
- [Running Automated Tests](#running-automated-tests)
- [Deployment Guide for Render](#deployment-guide-for-render)
- [Code Overview for Demo Presentations](#code-overview-for-demo-presentations)

---

## Features

- **Full CRUD Operations**:
  - `POST /students` - Create a student with strict Pydantic validation (auto-increments ID, checks unique email, requires at least phone or email).eds 5 realistic dummy students on application startup if the database table is empty.
- **LLM Extension (`POST /ask`)**:
  - Accepts natural language questions about students.
  - Backend fetches relevant records from SQLite (AI never gets direct SQL access).
  - Supplies context to Gemini 2.5 Flash via the official `google-genai` library.
  - Strictly grounded: the AI answers only using provided records or explicitly reports when data is unavailable.
- **Optional n8n Automation**:
  - If `N8N_WEBHOOK_URL` is set, new student events are dispatched via asynchronous background tasks without blocking client responses.

---

## Architecture & Security

```
                   +------------------------+
                   |   FastAPI Web Server   |
                   +-----------+------------+
                               |
            +------------------+------------------+
            |                                     |
   +--------v--------+                   +--------v--------+
   |  SQLite Database|                   |  Google Gemini  |
   |  (students.db)  |                   | (google-genai)  |
   +--------+--------+                   +-----------------+
            |                                     ^
            +------- Grounded Context (JSON) -----+
                    (AI NEVER executes SQL)
```

1. **SQL Injection Protection**: The LLM is never given direct access or permissions to construct/execute SQL queries. The backend fetches records safely with parameterized SQLite queries.
2. **Context Grounding**: The LLM receives existing records as a JSON string and is prompted to never hallucinate outside this context.
3. **Graceful Failures**: Missing API keys return HTTP `503 Service Unavailable` instead of unhandled server crashes.
4. **Data Isolation**: Unit/integration tests run against isolated temporary databases and never modify production records.

---

## Prerequisites

- **Python 3.10+** (tested up to Python 3.14)
- **pip** (Python package installer)
- Operating System: Windows, macOS, or Linux

---

## Project Structure

```text
students-api/
│
├── database.py         # SQLite connection, table schema creation, and dummy seed data
├── schemas.py          # Pydantic validation models (Create, Update, Out, Ask)
├── llm.py              # Google Gemini LLM grounding logic using google-genai
├── main.py             # FastAPI app, lifespan setup, endpoints, background tasks
├── test_api.py         # Automated test suite (CRUD, filters, errors, LLM fallback)
├── requirements.txt    # Project dependencies
├── .env.example        # Environment variables template
├── .gitignore          # Git ignore rules (.env, students.db, venv, etc.)
└── README.md           # Documentation and deployment guide
```

---

## Installation & Setup

### 1. Clone or Navigate to the Project

Open your terminal or PowerShell and navigate to the project directory:

```bash
cd students-api
```

### 2. Create a Virtual Environment

On Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

On macOS / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## How to Get a Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/).
2. Sign in with your Google account.
3. Click on the **Get API key** button in the left sidebar or top banner.
4. Click **Create API key** and select a project (or choose "Create API key in new project").
5. Copy the generated API key.

---

## Configuring the Environment (`.env`)

Copy the `.env.example` file to `.env`:

On Windows (PowerShell):
```powershell
Copy-Item .env.example .env
```

On macOS / Linux:
```bash
cp .env.example .env
```

Open `.env` in any text editor and fill in your values:

```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
N8N_WEBHOOK_URL=
```

> **Note**: If `GEMINI_API_KEY` is not provided, all CRUD endpoints will function normally, and calling `POST /ask` will return a clean `503 Service Unavailable` error explaining that the key is missing.

---

## Running the Application

Start the local development server:

```bash
uvicorn main:app --reload
```

The server will start at: `http://127.0.0.1:8000`

---

## Interactive API Documentation (Swagger / OpenAPI)

Once the application is running, open your web browser:

- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

From Swagger UI, you can interactively test every endpoint, inspect request/response schemas, and view real-time responses.

---

## Sample cURL Commands for Testing

### 1. Health / Welcome
```bash
curl -X GET "http://127.0.0.1:8000/"
```

### 2. List All Students (Initial 5 Seeded Students)
```bash
curl -X GET "http://127.0.0.1:8000/students"
```

### 3. Filter Students by Name, Course, and Date of Birth
```bash
# Partial name filter:
curl -X GET "http://127.0.0.1:8000/students?name=Aarav"

# Filter by course:
curl -X GET "http://127.0.0.1:8000/students?course=Computer%20Science"

# Filter by date of birth range with pagination:
curl -X GET "http://127.0.0.1:8000/students?born_after=2004-01-01&born_before=2006-12-31&skip=0&limit=10"
```

### 4. Create a New Student (POST)
```bash
curl -X POST "http://127.0.0.1:8000/students" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Ananya Sen",
    "date_of_birth": "2005-04-14",
    "email": "ananya.sen@example.com",
    "phone": "9830012345",
    "course": "Computer Science",
    "address": "Kolkata",
    "enrollment_date": "2024-07-20"
  }'
```

### 5. Get a Specific Student by ID
```bash
curl -X GET "http://127.0.0.1:8000/students/1"
```

### 6. Partially Update a Student (PATCH)
```bash
curl -X PATCH "http://127.0.0.1:8000/students/1" \
  -H "Content-Type: application/json" \
  -d '{
    "course": "Artificial Intelligence",
    "address": "New Town, Kolkata"
  }'
```

### 7. Delete a Student (DELETE)
```bash
curl -i -X DELETE "http://127.0.0.1:8000/students/5"
```

### 8. Ask Natural Language Questions (LLM Extension)
```bash
curl -X POST "http://127.0.0.1:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Which students are enrolled in Computer Science?"
  }'
```

---

## Running Automated Tests

The automated test suite verifies all CRUD operations, filtering, pagination, validation errors (400, 404, 409, 422), startup seeding, and the LLM fallback (503).

Tests run against an **isolated temporary database**, guaranteeing that your real `students.db` data is never modified.

### Run with Python:
```bash
python test_api.py
```

### Run with pytest:
```bash
pytest test_api.py -v
```

---

## Deployment Guide for Render

You can easily deploy this FastAPI backend to [Render](https://render.com/) for free:

### Step 1: Push Code to GitHub
1. Create a repository on GitHub (e.g., `students-database-api`).
2. Commit and push the `students-api/` folder:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of Students Database CRUD API"
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

### Step 2: Create a Web Service on Render
1. Log in to [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** and select **Web Service**.
3. Connect your GitHub repository.
4. Configure the service settings:
   - **Name**: `students-database-api`
   - **Environment**: `Python 3`
   - **Region**: Choose the closest region (e.g., Singapore / Frankfurt / Oregon)
   - **Branch**: `main`
   - **Root Directory**: (Leave blank if repo root contains `main.py`, or set to `students-api` if in a subfolder)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Step 3: Set Environment Variables on Render
Under the **Environment Variables** section on Render, add:
- `GEMINI_API_KEY`: Your Google Gemini API Key
- `GEMINI_MODEL`: `gemini-2.5-flash`
- `N8N_WEBHOOK_URL`: (Optional webhook URL)

### Step 4: Deploy & Verify
Click **Create Web Service**. Once the build finishes:
- Visit `https://<your-render-app-name>.onrender.com/docs` to test the live API via Swagger UI.

---

## Code Overview for Demo Presentations

When presenting this project in an internship interview or demo, highlight these key components:

1. **`database.py`**:
   - Uses `sqlite3.Row` so query rows behave like Python dictionaries.
   - `init_db()` runs `CREATE TABLE IF NOT EXISTS`, ensuring seamless zero-config setup.
   - `seed_if_empty()` guarantees the application is never blank on first run.

2. **`schemas.py`**:
   - `StudentCreate` uses Pydantic's `@model_validator` to verify that at least one contact channel (email or phone) is provided.
   - `StudentUpdate` excludes unset fields during serialization (`exclude_unset=True`), enabling true partial `PATCH` updates.

3. **`llm.py`**:
   - Demonstrates responsible AI architecture: backend queries the database with `SELECT * FROM students LIMIT 200`, formats it to JSON, and injects it into Gemini prompt context.
   - No SQL is ever generated or run by the LLM, eliminating prompt injection SQL attacks.

4. **`main.py`**:
   - Implements FastAPI `lifespan` context manager for startup tasks.
   - Integrates `BackgroundTasks` for optional n8n webhook notifications so client response times are not delayed.
# student_api
 428f9f4b5016c32b2d8eedf135608cfa99f64b9a
