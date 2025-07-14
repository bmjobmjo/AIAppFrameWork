import sqlite3
import json
import re
from typing import Dict, Any, List


def DoWork(json_data: Dict[str, Any]):
    """
    SQL Query Tool - Executes SQL queries and returns formatted results
    Input JSON: { 'queries': 'SQL queries separated by semicolons', 'database': 'database_path' }
    """
    try:
        # Get queries and database path from input
        queries = json_data.get('queries', '')
        database_path = json_data.get('database', 'router.db')

        if not queries:
            return {
                'error': 'No SQL queries provided',
                'results': []
            }

        # Split queries by semicolon and clean them
        query_list = split_sql_queries(queries)

        if not query_list:
            return {
                'error': 'No valid SQL queries found',
                'results': []
            }

        # Execute queries
        results = execute_queries(query_list, database_path)

        return {
            'success': True,
            'total_queries': len(query_list),
            'results': results
        }

    except Exception as e:
        return {
            'error': f'SQL Tool Error: {str(e)}',
            'results': []
        }


def split_sql_queries(queries: str) -> List[str]:
    """Split SQL queries by semicolon and clean them"""
    # Split by semicolon
    query_list = queries.split(';')

    # Clean and filter queries
    cleaned_queries = []
    for query in query_list:
        query = query.strip()
        if query and not query.isspace():
            cleaned_queries.append(query)

    return cleaned_queries


def execute_queries(query_list: List[str], database_path: str) -> List[Dict[str, Any]]:
    """Execute list of SQL queries and return results"""
    results = []

    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    try:
        for i, query in enumerate(query_list):
            try:
                # Execute query
                cursor.execute(query)

                # Determine query type
                query_type = get_query_type(query)

                if query_type == 'SELECT':
                    # For SELECT queries, return structured data
                    result = handle_select_query(cursor, query)
                else:
                    # For other queries (INSERT, UPDATE, DELETE), return execution info
                    result = handle_modification_query(cursor, query, query_type)

                results.append({
                    'query_index': i + 1,
                    'query': query,
                    'type': query_type,
                    'success': True,
                    'data': result
                })

            except sqlite3.Error as e:
                results.append({
                    'query_index': i + 1,
                    'query': query,
                    'type': get_query_type(query),
                    'success': False,
                    'error': str(e)
                })

        # Commit changes for modification queries
        conn.commit()

    finally:
        conn.close()

    return results


def get_query_type(query: str) -> str:
    """Determine the type of SQL query"""
    query_upper = query.strip().upper()

    if query_upper.startswith('SELECT'):
        return 'SELECT'
    elif query_upper.startswith('INSERT'):
        return 'INSERT'
    elif query_upper.startswith('UPDATE'):
        return 'UPDATE'
    elif query_upper.startswith('DELETE'):
        return 'DELETE'
    elif query_upper.startswith('CREATE'):
        return 'CREATE'
    elif query_upper.startswith('DROP'):
        return 'DROP'
    elif query_upper.startswith('ALTER'):
        return 'ALTER'
    else:
        return 'OTHER'


def handle_select_query(cursor, query: str) -> Dict[str, Any]:
    """Handle SELECT query and return JSON format with headers and records"""
    # Get column names
    columns = [description[0] for description in cursor.description]

    # Get all rows
    rows = cursor.fetchall()

    # Convert rows to list of dictionaries
    records = []
    for row in rows:
        record = {}
        for i, value in enumerate(row):
            record[columns[i]] = value
        records.append(record)

    return {
        'headers': columns,
        'records': records,
        'row_count': len(records)
    }


def handle_modification_query(cursor, query: str, query_type: str) -> Dict[str, Any]:
    """Handle INSERT, UPDATE, DELETE queries"""
    rows_affected = cursor.rowcount

    result = {
        'rows_affected': rows_affected,
        'message': f'{query_type} query executed successfully'
    }

    # For INSERT queries, try to get the last inserted row ID
    if query_type == 'INSERT':
        last_id = cursor.lastrowid
        if last_id:
            result['last_insert_id'] = last_id

    return result


def format_results_for_display(results: List[Dict[str, Any]]) -> str:
    """Format results for chat display"""
    if not results:
        return "No results to display."

    output_lines = []
    output_lines.append("📊 **SQL Query Results:**\n")

    for result in results:
        query_num = result['query_index']
        query_type = result['type']

        output_lines.append(f"**Query {query_num}** ({query_type}):")
        output_lines.append(f"```sql\n{result['query']}\n```")

        if result['success']:
            if query_type == 'SELECT':
                data = result['data']
                output_lines.append(f"✅ **Found {data['row_count']} rows**")

                if data['records']:
                    # Show first few records as preview
                    output_lines.append("\n**Sample Records:**")
                    for i, record in enumerate(data['records'][:3]):  # Show first 3 records
                        output_lines.append(f"Row {i + 1}: {json.dumps(record, indent=2)}")

                    if len(data['records']) > 3:
                        output_lines.append(f"... and {len(data['records']) - 3} more rows")
                else:
                    output_lines.append("No records found.")
            else:
                data = result['data']
                output_lines.append(f"✅ {data['message']}")
                output_lines.append(f"Rows affected: {data['rows_affected']}")

                if 'last_insert_id' in data:
                    output_lines.append(f"Last insert ID: {data['last_insert_id']}")
        else:
            output_lines.append(f"❌ **Error:** {result['error']}")

        output_lines.append("---")

    return "\n".join(output_lines)


# Test function
if __name__ == "__main__":
    # Test the tool
    test_data = {
        'queries': 'SELECT * FROM Users; SELECT * FROM ComponentLookup;',
        'database': 'router.db'
    }

    result = DoWork(test_data)
    print("Test result:")
    print(json.dumps(result, indent=2))

    # Test display formatting
    if 'results' in result:
        display_text = format_results_for_display(result['results'])
        print("\nFormatted display:")
        print(display_text)