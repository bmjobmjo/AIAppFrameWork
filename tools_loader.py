import importlib.util
import sys
import os
from typing import Dict, Any


class ToolsLoader:
    def __init__(self, db_setup):
        self.db_setup = db_setup

    def get_tool_info(self, tool_name: str) -> Dict[str, str]:
        """Get tool information from database"""
        conn = self.db_setup.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ToolName, PythonFile, Description FROM ToolLookup WHERE ToolName = ?", (tool_name,))
        result = cursor.fetchone()
        conn.close()

        if result:
            return {"name": result[0], "file": result[1], "description": result[2]}
        else:
            return None

    def load_tool(self, tool_name: str, tool_file: str):
        """Dynamically load a tool module"""
        try:
            # Check if file exists in tools directory
            tools_dir = "tools"
            if not os.path.exists(tools_dir):
                os.makedirs(tools_dir)

            file_path = os.path.join(tools_dir, tool_file)

            if not os.path.exists(file_path):
                raise Exception(f"Tool file not found: {file_path}")

            # Load module dynamically
            spec = importlib.util.spec_from_file_location(tool_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            return module

        except Exception as e:
            raise Exception(f"Failed to load tool {tool_name}: {str(e)}")

    def execute_tool(self, tool_name: str, tool_data: Dict[str, Any]) -> str:
        """Execute the specified tool"""
        try:
            # Get tool info from database
            tool_info = self.get_tool_info(tool_name)

            if not tool_info:
                return f"Tool {tool_name} not found in database."

            tool_file = tool_info["file"]

            # Load and execute tool
            module = self.load_tool(tool_name, tool_file)

            if not hasattr(module, 'DoWork'):
                return f"Tool {tool_name} does not have DoWork method."

            # Execute tool
            result = module.DoWork(tool_data)

            # Format result for display if it's a structured result
            if isinstance(result, dict) and 'results' in result:
                # Use the tool's own formatting function if available
                if hasattr(module, 'format_results_for_display'):
                    return module.format_results_for_display(result['results'])
                else:
                    return f"Tool executed successfully. Results: {str(result)}"
            else:
                return str(result)

        except Exception as e:
            return f"Error executing tool {tool_name}: {str(e)}"


# Test function
if __name__ == "__main__":
    from database_setup import DatabaseSetup

    db = DatabaseSetup()
    loader = ToolsLoader(db)

    # Test data
    test_data = {
        'queries': 'SELECT * FROM Users LIMIT 5;',
        'database': 'router.db'
    }

    result = loader.execute_tool("SQLQueryTool", test_data)
    print("Test result:")
    print(result)