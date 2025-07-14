import tkinter as tk
from tkinter import ttk, messagebox
import json
import requests
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod


# Data structures
@dataclass
class TableDisplayRequest:
    tab_title: str
    table_headings: List[str]
    rows_data: List[Dict[str, Any]]


@dataclass
class AgentResponse:
    success: bool
    data: Any
    next_route: Optional[str] = None
    message: Optional[str] = None


# UI Table Display Tool
class TableDisplayTool:
    def __init__(self, parent_notebook: ttk.Notebook):
        self.notebook = parent_notebook
        self.tabs = {}  # tab_title -> tab_frame mapping

    def display_table(self, request: TableDisplayRequest) -> bool:
        """Display table data in a tab"""
        try:
            # Check if tab already exists
            if request.tab_title in self.tabs:
                # Refresh existing tab
                self._refresh_tab(request)
            else:
                # Create new tab
                self._create_tab(request)

            # Focus on the tab
            self._focus_tab(request.tab_title)
            return True

        except Exception as e:
            messagebox.showerror("Table Display Error", f"Failed to display table: {str(e)}")
            return False

    def _create_tab(self, request: TableDisplayRequest):
        """Create a new tab with table"""
        # Create tab frame
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text=request.tab_title)

        # Create treeview for table display
        tree_frame = ttk.Frame(tab_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create treeview with scrollbars
        tree = ttk.Treeview(tree_frame, columns=request.table_headings, show='headings')

        # Configure column headings
        for heading in request.table_headings:
            tree.heading(heading, text=heading)
            tree.column(heading, width=150, anchor='center')

        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # Pack treeview and scrollbars
        tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Add control buttons
        button_frame = ttk.Frame(tab_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(button_frame, text="Refresh",
                   command=lambda: self._refresh_current_tab(request.tab_title)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Export CSV",
                   command=lambda: self._export_csv(request)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close Tab",
                   command=lambda: self._close_tab(request.tab_title)).pack(side=tk.RIGHT, padx=5)

        # Store tab info
        self.tabs[request.tab_title] = {
            'frame': tab_frame,
            'tree': tree,
            'request': request
        }

        # Populate data
        self._populate_table(tree, request.rows_data, request.table_headings)

    def _refresh_tab(self, request: TableDisplayRequest):
        """Refresh existing tab with new data"""
        if request.tab_title in self.tabs:
            tree = self.tabs[request.tab_title]['tree']
            # Clear existing data
            for item in tree.get_children():
                tree.delete(item)
            # Add new data
            self._populate_table(tree, request.rows_data, request.table_headings)
            # Update stored request
            self.tabs[request.tab_title]['request'] = request

    def _populate_table(self, tree: ttk.Treeview, rows_data: List[Dict], headings: List[str]):
        """Populate treeview with data"""
        for row_data in rows_data:
            values = []
            for heading in headings:
                values.append(str(row_data.get(heading, '')))
            tree.insert('', tk.END, values=values)

    def _focus_tab(self, tab_title: str):
        """Focus on the specified tab"""
        if tab_title in self.tabs:
            tab_frame = self.tabs[tab_title]['frame']
            for i in range(self.notebook.index('end')):
                if self.notebook.tab(i, 'text') == tab_title:
                    self.notebook.select(i)
                    break

    def _close_tab(self, tab_title: str):
        """Close the specified tab"""
        if tab_title in self.tabs:
            tab_frame = self.tabs[tab_title]['frame']
            self.notebook.forget(tab_frame)
            del self.tabs[tab_title]

    def _refresh_current_tab(self, tab_title: str):
        """Refresh current tab by re-executing the agent"""
        # This would trigger the agent to re-execute
        messagebox.showinfo("Refresh", f"Refreshing {tab_title}...")

    def _export_csv(self, request: TableDisplayRequest):
        """Export table data to CSV"""
        try:
            import csv
            from tkinter import filedialog

            filename = filedialog.asksaveasfilename(
                defaultextension='.csv',
                filetypes=[('CSV files', '*.csv'), ('All files', '*.*')],
                title='Export Table Data'
            )

            if filename:
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=request.table_headings)
                    writer.writeheader()
                    writer.writerows(request.rows_data)

                messagebox.showinfo("Export", f"Data exported to {filename}")

        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {str(e)}")


# Base Agent Interface
class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def execute(self, query: str, **kwargs) -> AgentResponse:
        pass


# Gemini Integration (Mock for now)
class GeminiQueryGenerator:
    def __init__(self, api_key: str = None):
        self.api_key = api_key

    def generate_query(self, user_query: str, table_design: Dict) -> str:
        """Generate SQL query based on user request and table design"""
        # Mock implementation - in real scenario, this would call Gemini API

        # For demo purposes, return a mock query based on user input
        if "active users" in user_query.lower():
            return "SELECT user_id, username, email, status, last_login FROM users WHERE status = 'active'"
        elif "recent" in user_query.lower():
            return "SELECT user_id, username, email, created_date FROM users WHERE created_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)"
        elif "admin" in user_query.lower():
            return "SELECT user_id, username, email, role FROM users WHERE role = 'admin'"
        else:
            return "SELECT user_id, username, email, status FROM users LIMIT 100"


# User List Agent
class UserListAgent(BaseAgent):
    def __init__(self, gemini_generator: GeminiQueryGenerator, db_connection=None):
        super().__init__("UserListAgent")
        self.gemini_generator = gemini_generator
        self.db_connection = db_connection

        # Table design for user queries
        self.table_design = {
            "table_name": "users",
            "columns": {
                "user_id": "INT PRIMARY KEY",
                "username": "VARCHAR(50)",
                "email": "VARCHAR(100)",
                "status": "VARCHAR(20)",
                "role": "VARCHAR(20)",
                "created_date": "DATE",
                "last_login": "DATETIME"
            },
            "indexes": ["username", "email", "status", "role"]
        }

    def execute(self, query: str, **kwargs) -> AgentResponse:
        """Execute user list query and return table display format"""
        try:
            # Generate SQL query using Gemini
            sql_query = self.gemini_generator.generate_query(query, self.table_design)

            # Execute query and get results (mock data for demo)
            results = self._execute_query(sql_query)

            # Determine table headings based on query
            headings = self._get_table_headings(sql_query)

            # Format response for table display
            response_data = {
                "tab_title": self._generate_tab_title(query),
                "table_headings": headings,
                "rows_data": results
            }

            return AgentResponse(
                success=True,
                data=response_data,
                next_route="TableDisplayTool",
                message=f"Found {len(results)} users"
            )

        except Exception as e:
            return AgentResponse(
                success=False,
                data=None,
                message=f"Error executing user list query: {str(e)}"
            )

    def _execute_query(self, sql_query: str) -> List[Dict]:
        """Execute SQL query and return results (mock implementation)"""
        # Mock data - in real scenario, this would execute against actual database
        mock_users = [
            {"user_id": 1, "username": "john_doe", "email": "john@example.com", "status": "active", "role": "user",
             "created_date": "2024-01-15", "last_login": "2025-07-10 10:30:00"},
            {"user_id": 2, "username": "jane_smith", "email": "jane@example.com", "status": "active", "role": "admin",
             "created_date": "2024-02-20", "last_login": "2025-07-09 14:15:00"},
            {"user_id": 3, "username": "bob_wilson", "email": "bob@example.com", "status": "inactive", "role": "user",
             "created_date": "2024-03-10", "last_login": "2025-06-15 09:45:00"},
            {"user_id": 4, "username": "alice_brown", "email": "alice@example.com", "status": "active", "role": "user",
             "created_date": "2024-04-05", "last_login": "2025-07-10 08:20:00"},
            {"user_id": 5, "username": "charlie_davis", "email": "charlie@example.com", "status": "active",
             "role": "admin", "created_date": "2024-05-12", "last_login": "2025-07-10 11:10:00"}
        ]

        # Filter based on query type (simplified)
        if "active" in sql_query.lower():
            return [user for user in mock_users if user["status"] == "active"]
        elif "admin" in sql_query.lower():
            return [user for user in mock_users if user["role"] == "admin"]
        else:
            return mock_users

    def _get_table_headings(self, sql_query: str) -> List[str]:
        """Extract column names from SQL query"""
        # Simplified extraction - in real scenario, would parse SQL properly
        if "user_id, username, email, status, last_login" in sql_query:
            return ["user_id", "username", "email", "status", "last_login"]
        elif "user_id, username, email, created_date" in sql_query:
            return ["user_id", "username", "email", "created_date"]
        elif "user_id, username, email, role" in sql_query:
            return ["user_id", "username", "email", "role"]
        else:
            return ["user_id", "username", "email", "status"]

    def _generate_tab_title(self, query: str) -> str:
        """Generate appropriate tab title based on query"""
        if "active" in query.lower():
            return "Active Users"
        elif "admin" in query.lower():
            return "Admin Users"
        elif "recent" in query.lower():
            return "Recent Users"
        else:
            return "User List"


# Main Application Framework
class MainApplication:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("User Management System")
        self.root.geometry("1200x800")

        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Initialize tools and agents
        self.table_display_tool = TableDisplayTool(self.notebook)
        self.gemini_generator = GeminiQueryGenerator()
        self.user_list_agent = UserListAgent(self.gemini_generator)

        # Create control panel
        self._create_control_panel()

        # Route mapping
        self.routes = {
            "TableDisplayTool": self._handle_table_display
        }

    def _create_control_panel(self):
        """Create main control panel"""
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        # Query input
        ttk.Label(control_frame, text="User Query:").pack(side=tk.LEFT, padx=5)
        self.query_entry = ttk.Entry(control_frame, width=50)
        self.query_entry.pack(side=tk.LEFT, padx=5)

        # Execute button
        ttk.Button(control_frame, text="Execute Query",
                   command=self._execute_user_query).pack(side=tk.LEFT, padx=5)

        # Sample queries
        sample_frame = ttk.Frame(self.root)
        sample_frame.pack(fill=tk.X, padx=10, pady=2)

        ttk.Label(sample_frame, text="Sample queries:").pack(side=tk.LEFT, padx=5)
        ttk.Button(sample_frame, text="Show active users",
                   command=lambda: self._set_query("show active users")).pack(side=tk.LEFT, padx=2)
        ttk.Button(sample_frame, text="Show admin users",
                   command=lambda: self._set_query("show admin users")).pack(side=tk.LEFT, padx=2)
        ttk.Button(sample_frame, text="Show recent users",
                   command=lambda: self._set_query("show recent users")).pack(side=tk.LEFT, padx=2)

    def _set_query(self, query: str):
        """Set query in entry field"""
        self.query_entry.delete(0, tk.END)
        self.query_entry.insert(0, query)

    def _execute_user_query(self):
        """Execute user query through UserListAgent"""
        query = self.query_entry.get().strip()
        if not query:
            messagebox.showwarning("Input Error", "Please enter a query")
            return

        try:
            # Execute agent
            response = self.user_list_agent.execute(query)

            if response.success:
                # Route to next tool
                if response.next_route and response.next_route in self.routes:
                    self.routes[response.next_route](response.data)

                if response.message:
                    messagebox.showinfo("Success", response.message)
            else:
                messagebox.showerror("Error", response.message)

        except Exception as e:
            messagebox.showerror("Execution Error", f"Failed to execute query: {str(e)}")

    def _handle_table_display(self, data: Dict):
        """Handle table display routing"""
        request = TableDisplayRequest(
            tab_title=data["tab_title"],
            table_headings=data["table_headings"],
            rows_data=data["rows_data"]
        )
        self.table_display_tool.display_table(request)

    def run(self):
        """Run the application"""
        self.root.mainloop()


# Example usage
if __name__ == "__main__":
    app = MainApplication()
    app.run()