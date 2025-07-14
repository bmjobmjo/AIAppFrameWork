from database_setup import DatabaseSetup


def add_sql_tool():
    """Add SQL Query Tool to the database"""
    db = DatabaseSetup()

    conn = db.get_connection()
    cursor = conn.cursor()

    # Add SQLQueryTool to ToolLookup table
    cursor.execute("""
        INSERT OR REPLACE INTO ToolLookup 
        (ToolName, PythonFile, Description) 
        VALUES (?, ?, ?)
    """, ("SQLQueryTool", "SQLQueryTool.py", "Executes SQL queries and returns formatted results"))

    conn.commit()
    conn.close()

    print("✅ SQLQueryTool added to database successfully!")


if __name__ == "__main__":
    add_sql_tool()