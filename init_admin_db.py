
import sqlite3
from getpass import getpass
from pathlib import Path

from werkzeug.security import generate_password_hash


# -------------------------------------------------
# ADMIN DATABASE CONFIGURATION
# -------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent
DATABASE_PATH = PROJECT_ROOT / "admin.db"


# -------------------------------------------------
# CREATE ADMIN DATABASE AND TABLE
# -------------------------------------------------

def initialize_admin_database():
    connection = sqlite3.connect(DATABASE_PATH)

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.commit()

        print("\nAdmin database initialized successfully.")
        print(f"Database location: {DATABASE_PATH}")

    finally:
        connection.close()


# -------------------------------------------------
# CREATE ADMIN ACCOUNT
# -------------------------------------------------

def create_admin():
    username = input("Enter admin username: ").strip()

    if not username:
        print("Error: Username cannot be empty.")
        return

    password = getpass("Enter admin password: ")
    confirm_password = getpass("Confirm admin password: ")

    if not password:
        print("Error: Password cannot be empty.")
        return

    if password != confirm_password:
        print("Error: Passwords do not match.")
        return

    password_hash = generate_password_hash(password)

    connection = sqlite3.connect(DATABASE_PATH)

    try:
        connection.execute(
            """
            INSERT INTO admins (username, password_hash)
            VALUES (?, ?)
            """,
            (username, password_hash)
        )

        connection.commit()

        print("\nAdmin account created successfully.")
        print(f"Username: {username}")
        print("Password stored as a secure hash.")

    except sqlite3.IntegrityError:
        print("Error: That admin username already exists.")

    finally:
        connection.close()


# -------------------------------------------------
# MAIN
# -------------------------------------------------

if __name__ == "__main__":
    initialize_admin_database()
    create_admin()
