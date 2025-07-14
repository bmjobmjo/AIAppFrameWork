import sqlite3
import os


class DatabaseSetup:
    def __init__(self, db_path="router.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # ComponentLookup table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ComponentLookup (
                ComponentName TEXT PRIMARY KEY,
                PythonFile TEXT NOT NULL,
                Description TEXT NOT NULL
            )
        """)

        # ToolLookup table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ToolLookup (
                ToolName TEXT PRIMARY KEY,
                PythonFile TEXT NOT NULL,
                Description TEXT NOT NULL
            )
        """)

        # Settings table for API keys and configuration
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Users table for user management
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Insert default AddUserComponent if not exists
        cursor.execute("""
            INSERT OR IGNORE INTO ComponentLookup 
            (ComponentName, PythonFile, Description) 
            VALUES (?, ?, ?)
        """, ("AddUserComponent", "AddUserComponent.py", "Adds new users to the database"))

        conn.commit()
        conn.close()

    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def execute_query(self, query, params=None):
        """Execute a query and return results"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        if query.strip().upper().startswith('SELECT'):
            results = cursor.fetchall()
            conn.close()
            return results
        else:
            conn.commit()
            conn.close()
            return cursor.rowcount


if __name__ == "__main__":
    db = DatabaseSetup()
    print("Database initialized successfully!")