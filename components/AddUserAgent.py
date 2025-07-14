import json
import requests
import sqlite3
from typing import Dict, Any


def DoWork(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    AddUserComponent - Uses Gemini AI to parse user requests and generate SQL commands
    Supports both single and multiple user creation
    Input JSON: { 'chat_history': [...], 'request': '...' }
    Returns: { 'result': {...}, 'nextRoot': '...' }
    """
    try:
        request = json_data.get('request', '')

        if not request:
            return {
                'result': '❌ No user request provided',
                'nextRoot': ''
            }

        # Get table structure
        table_structure = get_users_table_structure()

        # Use Gemini to parse the request and generate SQL
        gemini_result = parse_user_request_with_gemini(request, table_structure)

        if not gemini_result['success']:
            return {
                'result': f"❌ {gemini_result.get('error', 'Failed to parse user request')}",
                'nextRoot': ''
            }

        # Extract SQL queries from Gemini response and format properly
        insert_queries = gemini_result['sql_queries']['insert']
        select_queries = gemini_result['sql_queries']['select']

        # Ensure we have strings, not arrays
        if isinstance(insert_queries, list):
            insert_sql = "; ".join(insert_queries)
        else:
            insert_sql = insert_queries

        if isinstance(select_queries, list):
            select_sql = "; ".join(select_queries)
        else:
            select_sql = select_queries

        # Combine all queries
        combined_queries = f"{insert_sql}; {select_sql}"

        return {
            'result': gemini_result['message'],
            'nextRoot': 'SQLQueryTool',
            'tool_data': {
                'queries': combined_queries,
                'database': 'router.db'
            }
        }

    except Exception as e:
        return {
            'result': f'❌ Error processing user creation: {str(e)}',
            'nextRoot': ''
        }


def get_users_table_structure() -> str:
    """Get the Users table structure from database"""
    try:
        conn = sqlite3.connect('router.db')
        cursor = conn.cursor()

        # Get table info
        cursor.execute("PRAGMA table_info(Users)")
        columns = cursor.fetchall()

        conn.close()

        # Format table structure
        structure = "Users Table Structure:\n"
        for col in columns:
            col_name = col[1]
            col_type = col[2]
            not_null = "NOT NULL" if col[3] else "NULL"
            default_val = f"DEFAULT {col[4]}" if col[4] else ""
            primary_key = "PRIMARY KEY" if col[5] else ""

            structure += f"- {col_name}: {col_type} {not_null} {default_val} {primary_key}\n"

        return structure.strip()

    except Exception as e:
        return f"Users Table: id (INTEGER PRIMARY KEY), name (TEXT NOT NULL), email (TEXT UNIQUE NOT NULL), created_at (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"


def get_gemini_api_key() -> str:
    """Get Gemini API key from database"""
    try:
        conn = sqlite3.connect('router.db')
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM Settings WHERE key = 'gemini_api_key'")
        result = cursor.fetchone()
        conn.close()

        if result:
            return result[0]
        else:
            raise Exception("Gemini API key not configured")
    except Exception as e:
        raise Exception(f"Cannot get API key: {str(e)}")


def parse_user_request_with_gemini(user_request: str, table_structure: str) -> Dict[str, Any]:
    """Use Gemini AI to parse user request and generate SQL commands for single or multiple users"""
    try:
        api_key = get_gemini_api_key()

        # Create prompt for Gemini
        prompt = f"""
You are a SQL generator for a user management system. Parse the user's natural language request and generate appropriate SQL commands.
The request may contain SINGLE or MULTIPLE users.

DATABASE TABLE STRUCTURE:
{table_structure}

USER REQUEST: "{user_request}"

INSTRUCTIONS:
1. Extract ALL user information (name and email) from the request
2. If email is not provided for any user, generate reasonable emails based on names
3. For MULTIPLE users, create separate INSERT and SELECT queries for each user
4. Return SQL queries as STRINGS separated by semicolons, NOT as arrays
5. Return response in EXACT JSON format below

REQUIRED JSON RESPONSE FORMAT:
{{
    "success": true,
    "user_count": number_of_users,
    "users_data": [
        {{"name": "user1_name", "email": "user1_email"}},
        {{"name": "user2_name", "email": "user2_email"}}
    ],
    "sql_queries": {{
        "insert": "INSERT INTO Users (name, email) VALUES ('user1', 'email1'); INSERT INTO Users (name, email) VALUES ('user2', 'email2')",
        "select": "SELECT * FROM Users WHERE email = 'email1'; SELECT * FROM Users WHERE email = 'email2'"
    }},
    "message": "🎯 AI Analysis: Creating X user(s) - names and emails"
}}

IMPORTANT RULES:
- Return ONLY valid JSON, no additional text
- SQL queries must be STRINGS with semicolon separators, never arrays
- Use single quotes in SQL values
- Generate realistic emails if not provided (name@example.com)
- Handle various separators: commas, semicolons, "and", line breaks
- If request is unclear, set success to false with error message

EXAMPLES:
Single: "add user john" → 1 user, john@example.com
Multiple: "add users john,jane ; bob,bob@test.com" → 3 users with proper emails
Multiple: "create users: Alice Smith email alice@co.com and Bob Wilson" → 2 users
"""

        # Call Gemini API
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{"parts": [{"text": prompt}]}]
        }

        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}",
            headers=headers,
            json=data,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                gemini_text = result['candidates'][0]['content']['parts'][0]['text'].strip()

                # Parse JSON response from Gemini
                try:
                    # Clean the response (remove any markdown formatting)
                    if "```json" in gemini_text:
                        gemini_text = gemini_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in gemini_text:
                        gemini_text = gemini_text.split("```")[1].strip()

                    gemini_json = json.loads(gemini_text)

                    # Validate the response format
                    if not isinstance(gemini_json.get('sql_queries', {}).get('insert'), str):
                        return {
                            "success": False,
                            "error": "Gemini returned SQL queries in wrong format (should be strings, not arrays)"
                        }

                    return gemini_json

                except json.JSONDecodeError as e:
                    return {
                        "success": False,
                        "error": f"Gemini returned invalid JSON: {str(e)}. Response: {gemini_text[:200]}"
                    }
            else:
                return {"success": False, "error": "No response from Gemini API"}
        else:
            return {"success": False, "error": f"Gemini API error: {response.status_code}"}

    except Exception as e:
        return {"success": False, "error": f"Gemini API call failed: {str(e)}"}


# Test function
if __name__ == "__main__":
    # Test the component
    test_cases = [
        "add a user named bijumon",
        "add these users bmjo,bmjo@gmail.com ; devu , devikarb@gmail.com",
        "create users: Alice Smith with email alice@company.com and Bob Wilson",
        "add john, jane@test.com, and mike",
        "register users: Sarah Johnson email sarah@work.com, David Lee, Emma Watson emma@movies.com"
    ]

    print("Testing AddUserComponent with Multiple User Support...")
    print("=" * 60)

    for test in test_cases:
        print(f"\nTesting: {test}")
        result = DoWork({'request': test, 'chat_history': []})
        print(f"Result: {result}")
        print("-" * 40)