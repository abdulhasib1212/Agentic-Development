import sqlite3
import ollama
import json
import tkinter as tk
from tkinter import ttk, messagebox

# ==========================================
# 1. LOCAL DATABASE SETUP
# ==========================================
conn = sqlite3.connect(":memory:")
cursor = conn.cursor()
cursor.execute("CREATE TABLE appointments (id INT, patient TEXT, date TEXT, status TEXT)")
cursor.executemany("INSERT INTO appointments VALUES (?, ?, ?, ?)", [
    (101, "Alice Smith", "October 12th", "Pending"),
    (102, "Bob Jones", "October 15th", "Confirmed"),
    (103, "Charlie Brown", "November 2nd", "Cancelled"),
    (104, "Diana Prince", "December 25th", "Confirmed")
])
conn.commit()

chat_history = []

# ==========================================
# 2. POWERFUL, FLEXIBLE READ/WRITE TOOLS
# ==========================================
def lookup_by_name(patient_name):
    """Tool: Searches records utilizing string name fragments."""
    cursor.execute("SELECT id, patient, date, status FROM appointments WHERE patient LIKE ?", (f"%{patient_name}%",))
    rows = cursor.fetchall()
    if rows:
        return "\n".join([f"ID: {r[0]} | Patient: {r[1]} | Date: {r[2]} | Status: {r[3]}" for r in rows])
    return f"No records found matching name text '{patient_name}'."

def lookup_by_id(appointment_id):
    """Tool: Searches records utilizing absolute numerical keys."""
    try:
        cursor.execute("SELECT id, patient, date, status FROM appointments WHERE id = ?", (int(appointment_id),))
        row = cursor.fetchone()
        if row:
            return f"ID: {row[0]} | Patient: {row[1]} | Date: {row[2]} | Status: {row[3]}"
        return f"No table index matches ID key {appointment_id}."
    except ValueError:
        return "Error: ID parameter must be an integer."

def update_appointment(appointment_id, new_status=None, new_date=None):
    """
    UPGRADED MUTATOR TOOL: Safely updates status, date, or BOTH at the same time
    based on what the model passes inside the JSON parameters.
    """
    try:
        id_int = int(appointment_id)
        cursor.execute("SELECT patient, date, status FROM appointments WHERE id = ?", (id_int,))
        row = cursor.fetchone()
        if not row:
            return f"Error: Cannot alter record. ID {id_int} does not exist."
        
        changes = []
        # Dynamically build SQL depending on what parameters the AI passed
        if new_status:
            clean_status = new_status.strip().capitalize()
            if clean_status in ["Confirmed", "Cancelled", "Pending"]:
                cursor.execute("UPDATE appointments SET status = ? WHERE id = ?", (clean_status, id_int))
                changes.append(f"Status -> {clean_status}")
            else:
                return f"Rejected: Invalid status choice '{new_status}'."
                
        if new_date:
            clean_date = new_date.strip()
            cursor.execute("UPDATE appointments SET date = ? WHERE id = ?", (clean_date, id_int))
            changes.append(f"Date -> {clean_date}")
            
        if not changes:
            return "No modification parameters were provided to the update tool."
            
        conn.commit()
        return f"✅ Success on ID {id_int} ({row[0]}): Modified {', '.join(changes)}."
    except ValueError:
        return "Error: ID parameter must be an integer."

# ==========================================
# 3. UPDATED SYSTEM SCHEMAS WITH OPTIONAL PARAMETERS
# ==========================================
hospital_tools = [
    {
        'type': 'function',
        'function': {
            'name': 'lookup_by_name',
            'description': 'Search for patients and view their details using a text name.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'patient_name': {'type': 'string', 'description': 'The name of the patient.'}
                },
                'required': ['patient_name']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'lookup_by_id',
            'description': 'Search for a patient record explicitly by using their numerical index ID.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'appointment_id': {'type': 'integer', 'description': 'The exact ID number (e.g., 102).'}
                },
                'required': ['appointment_id']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'update_appointment',
            'description': 'Modify or change a patient\'s status, date, or both. Leave fields blank if they do not need altering.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'appointment_id': {'type': 'integer', 'description': 'The explicit appointment numerical ID.'},
                    'new_status': {'type': 'string', 'description': 'Optional. Must be exactly: Confirmed, Cancelled, or Pending.'},
                    'new_date': {'type': 'string', 'description': 'Optional. The new appointment date text (e.g., October 20th).'}
                },
                'required': ['appointment_id']
            }
        }
    }
]

# ==========================================
# 4. GUI WINDOW SYSTEM (Tkinter Layout)
# ==========================================
class AgentHospitalApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🧠 ReAct Logic Layer Engine v2")
        self.root.geometry("900x650")
        
        self.left_frame = ttk.LabelFrame(root, text=" Live Database State (RAM) ", padding=10)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.right_frame = ttk.LabelFrame(root, text=" Internal ReAct Execution Cycle Logs ", padding=10)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.tree = ttk.Treeview(self.left_frame, columns=("ID", "Patient Name", "Date", "Status"), show="headings")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Patient Name", text="Patient Name")
        self.tree.heading("Date", text="Date")
        self.tree.heading("Status", text="Status")
        self.tree.column("ID", width=50, anchor=tk.CENTER)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        self.chat_display = tk.Text(self.right_frame, state=tk.DISABLED, wrap=tk.WORD, height=22, bg="#111111", fg="#a6e22e", font=("Courier", 10))
        self.chat_display.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.input_frame = tk.Frame(self.right_frame)
        self.input_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.user_entry = ttk.Entry(self.input_frame, font=("Arial", 11))
        self.user_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.user_entry.bind("<Return>", lambda event: self.process_agent_action())
        
        self.submit_btn = ttk.Button(self.input_frame, text="Execute", command=self.process_agent_action)
        self.submit_btn.pack(side=tk.RIGHT)
        
        self.refresh_database_view()
        self.append_to_chat("SYSTEM", "ReAct Engine v2 Online. Multi-variable modifications enabled.")

    def refresh_database_view(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        cursor.execute("SELECT id, patient, date, status FROM appointments")
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)

    def append_to_chat(self, sender, text):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"[{sender}]:\n{text}\n")
        self.chat_display.insert(tk.END, "=" * 50 + "\n")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def process_agent_action(self):
        query = self.user_entry.get().strip()
        if not query:
            return
        
        self.user_entry.delete(0, tk.END)
        self.append_to_chat("MANAGER COMMAND", query)
        
        # Enhanced System Instructions dictating absolute tool reliance rules
        system_prompt = (
            "You are a strict reasoning database coordination assistant running inside a ReAct sequence loop.\n"
            "CRITICAL: Look carefully at your tools schema parameters before making assumptions. "
            "You can modify both status and date simultaneously using 'update_appointment'.\n"
            "Do not state that an edit has been made unless a tool observation strictly confirms it."
        )
        
        session_messages = [{"role": "system", "content": system_prompt}]
        for turn in chat_history:
            session_messages.append(turn)
        session_messages.append({"role": "user", "content": query})
        
        loop_counter = 0
        max_loops = 5
        
        while loop_counter < max_loops:
            try:
                response = ollama.chat(
                    model='qwen2.5:1.5b',
                    messages=session_messages,
                    tools=hospital_tools
                )
                
                ai_message = response['message']
                session_messages.append(ai_message)
                
                if 'tool_calls' in ai_message and ai_message['tool_calls']:
                    for tool_call in ai_message['tool_calls']:
                        func_name = tool_call['function']['name']
                        args = tool_call['function']['arguments']
                        
                        self.append_to_chat(f"THOUGHT & ACTION (LOOP {loop_counter+1})", f"Invoking Tool: {func_name}()\nParameters: {json.dumps(args)}")
                        
                        tool_output = ""
                        if func_name == "lookup_by_name":
                            tool_output = lookup_by_name(args.get('patient_name'))
                        elif func_name == "lookup_by_id":
                            tool_output = lookup_by_id(args.get('appointment_id'))
                        elif func_name == "update_appointment":
                            tool_output = update_appointment(
                                appointment_id=args.get('appointment_id'),
                                new_status=args.get('new_status'),
                                new_date=args.get('new_date')
                            )
                            self.refresh_database_view()
                        
                        self.append_to_chat("TOOL OBSERVATION OUTPUT", tool_output)
                        
                        session_messages.append({
                            "role": "tool",
                            "content": tool_output,
                            "name": func_name
                        })
                        
                    loop_counter += 1
                    continue
                
                else:
                    self.append_to_chat("FINAL AI SUMMARY", ai_message['content'])
                    chat_history.append({"role": "user", "content": query})
                    chat_history.append({"role": "assistant", "content": ai_message['content']})
                    break
                    
            except Exception as e:
                messagebox.showerror("Runtime Loop Crash", f"Details: {str(e)}")
                break
        else:
            self.append_to_chat("SYSTEM PROTECTION", "Sequence broke ceiling limit safely.")

if __name__ == "__main__":
    window = tk.Tk()
    app = AgentHospitalApp(window)
    window.mainloop()
