import json
import requests
import importlib.util
import sys
import os
from typing import Dict, Any, List
from tools_loader import ToolsLoader


class GatewayRouterAgent:
    def __init__(self, db_setup):
        self.db_setup = db_setup
        self.tools_loader = ToolsLoader(db_setup)
        self.gemini_api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"

    def get_api_key(self) -> str:
        """Get Gemini API key from database"""
        conn = self.db_setup.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM Settings WHERE key = 'gemini_api_key'")
        result = cursor.fetchone()
        conn.close()

        if result:
            return result[0]
        else:
            raise Exception("Gemini API key not configured. Please set it in Settings.")

    def get_components(self) -> List[Dict[str, str]]:
        """Get all available components from database"""
        conn = self.db_setup.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ComponentName, PythonFile, Description FROM ComponentLookup")
        components = cursor.fetchall()
        conn.close()

        return [{"name": comp[0], "file": comp[1], "description": comp[2]} for comp in components]

    def create_routing_prompt(self, user_request: str, chat_history: List[Dict], components: List[Dict]) -> str:
        """Create prompt for Gemini to route the request"""
        components_text = "\n".join([f"- {comp['name']}: {comp['description']}" for comp in components])

        chat_context = "\n".join([f"{msg['sender']}: {msg['message']}" for msg in chat_history[-5:]])  # Last 5 messages

        prompt = f"""
You are a routing agent for a modular chat application. Based on the user's request and chat history, 
select the most appropriate component to handle the request.

Available Components:
{components_text}

Recent Chat History:
{chat_context}

User Request: {user_request}

Instructions:
- Respond with ONLY the exact component name that should handle this request
- If no component matches, respond with "NO_MATCH"
- Do not include any explanations or additional text

Examples:
- For "add user john with email john@test.com" -> AddUserComponent
- For "create new task" -> AddTaskComponent  
- For "show all users" -> ListUserComponent
- For "list my tasks" -> ListTaskComponent
"""
        return prompt

    def call_gemini_api(self, prompt: str) -> str:
        """Call Gemini API for component routing"""
        api_key = self.get_api_key()

        headers = {
            'Content-Type': 'application/json',
        }

        data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
        }

        try:
            response = requests.post(
                f"{self.gemini_api_url}?key={api_key}",
                headers=headers,
                json=data,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    return result['candidates'][0]['content']['parts'][0]['text'].strip()
                else:
                    return "NO_MATCH"
            else:
                raise Exception(f"API Error: {response.status_code} - {response.text}")

        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")

    def load_component(self, component_name: str, component_file: str):
        """Dynamically load a component module"""
        try:
            # Check if file exists in components directory
            components_dir = "components"
            if not os.path.exists(components_dir):
                os.makedirs(components_dir)

            file_path = os.path.join(components_dir, component_file)

            if not os.path.exists(file_path):
                raise Exception(f"Component file not found: {file_path}")

            # Load module dynamically
            spec = importlib.util.spec_from_file_location(component_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            return module

        except Exception as e:
            raise Exception(f"Failed to load component {component_name}: {str(e)}")

    def execute_component(self, component_name: str, user_request: str, chat_history: List[Dict]) -> str:
        """Execute the selected component and handle tools if needed"""
        try:
            # Get component info from database
            conn = self.db_setup.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT PythonFile FROM ComponentLookup WHERE ComponentName = ?", (component_name,))
            result = cursor.fetchone()
            conn.close()

            if not result:
                return f"Component {component_name} not found in database."

            component_file = result[0]

            # Load and execute component
            module = self.load_component(component_name, component_file)

            if not hasattr(module, 'DoWork'):
                return f"Component {component_name} does not have DoWork method."

            # Prepare input data
            input_data = {
                'chat_history': chat_history,
                'request': user_request
            }

            # Execute component
            component_result = module.DoWork(input_data)

            if isinstance(component_result, dict):
                result_message = str(component_result.get('result', 'Component executed'))
                next_root = component_result.get('nextRoot', '')
                tool_data = component_result.get('tool_data', {})

                # If nextRoot is specified, execute the tool
                if next_root:
                    tool_result = self.tools_loader.execute_tool(next_root, tool_data)
                    return f"{result_message}\n\n{tool_result}"
                else:
                    return result_message
            else:
                return str(component_result)

        except Exception as e:
            return f"Error executing component {component_name}: {str(e)}"

    def process_request(self, user_request: str, chat_history: List[Dict]) -> str:
        """Main method to process user request"""
        try:
            # Get available components
            components = self.get_components()

            if not components:
                return "No components available. Please add components in Settings first."

            # Create routing prompt
            prompt = self.create_routing_prompt(user_request, chat_history, components)

            # Get component selection from Gemini
            selected_component = self.call_gemini_api(prompt)

            if selected_component == "NO_MATCH":
                return "I couldn't find an appropriate component to handle your request. Available components: " + ", ".join(
                    [comp['name'] for comp in components])

            # Execute the selected component
            return self.execute_component(selected_component, user_request, chat_history)

        except Exception as e:
            return f"❌ **Router Error**: {str(e)}"