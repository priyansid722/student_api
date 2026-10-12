"""Database module for the Students Database CRUD Application.

This module manages the SQLite database connection, table initialization,
and automatic dummy data seeding on application startup.
"""

import sqlite3
from pathlib import Path

# Path to the SQLite database file in the same directory as this file
DB_PATH = Path(__file__).parent / "students.db"


def get_conn():
    """Establish and return a connection to the SQLite database.

    Using `conn.row_factory = sqlite3.Row` allows columns to be accessed
    both by name (dict-like) and index, simplifying data serialization.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows behave like dicts
    return conn


def init_db():
    """Create the students table if it does not already exist.

    Table Schema:
    - id: Unique integer, automatically increments for every new student.
    - name: Full name of the student (mandatory).
    - date_of_birth: Date formatted as YYYY-MM-DD (mandatory).
    - email: Optional unique email address (enforces no duplicate emails).
    - phone: Optional phone number.
    - course: Optional course or department name.
    - address: Optional location/address.
    - enrollment_date: Optional enrollment date (YYYY-MM-DD).
    """
    with get_conn() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                date_of_birth TEXT NOT NULL,
                email TEXT UNIQUE,
                phone TEXT,
                course TEXT,
                address TEXT,
                enrollment_date TEXT
            )"""
        )


def seed_if_empty():
    """Insert 5 DUMMY students if the table is currently empty.

    This ensures that when testing or presenting a live demo,
    there are already realistic sample records to query and display.
    """
    dummy = [
        ("Aarav Sen", "2004-03-12", "aarav@example.com", "9000000001", "Computer Science", "Kolkata", "2024-08-01"),
        ("Diya Roy", "2006-07-25", "diya@example.com", "9000000002", "Data Science", "Howrah", "2025-08-01"),
        ("Rohan Das", "2003-11-02", "rohan@example.com", None, "Electronics", "Salt Lake", "2023-08-01"),
        ("Ishita Ghosh", "2005-01-18", "ishita@example.com", "9000000004", "Computer Science", "Durgapur", "2024-08-01"),
        ("Kabir Basu", "2007-05-30", None, "9000000005", "Mechanical", "Siliguri", "2025-08-01"),
    ]
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO students (name, date_of_birth, email, phone, course, address, enrollment_date) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                dummy,
            )
