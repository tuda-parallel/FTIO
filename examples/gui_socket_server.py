#!/usr/bin/env python3
"""
Simple GUI log server to receive logs from FTIO prediction analysis.
Run this before running the FTIO predictor to see real-time logs in the GUI.
"""

import socket
import json
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk
from datetime import datetime
import queue


class LogGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("FTIO Prediction Log Visualizer")
        self.root.geometry("1200x800")
        
        # Create log queue for thread-safe updates
        self.log_queue = queue.Queue()
        
        # Create UI elements
        self.setup_ui()
        
        # Start socket server in a separate thread
        self.server_thread = threading.Thread(target=self.start_server, daemon=True)
        self.server_thread.start()
        
        # Schedule periodic UI updates
        self.update_logs()
    
    def setup_ui(self):
        """Create the GUI elements"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="FTIO Real-time Log Monitor", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # Status frame
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Connection status
        self.status_label = ttk.Label(status_frame, text="Server Status: Starting...", 
                                     font=('Arial', 10, 'bold'))
        self.status_label.grid(row=0, column=0, padx=(0, 20))
        
        # Log count
        self.log_count_label = ttk.Label(status_frame, text="Logs Received: 0")
        self.log_count_label.grid(row=0, column=1)
        
        # Filter frame
        filter_frame = ttk.Frame(main_frame)
        filter_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(filter_frame, text="Filter by type:").grid(row=0, column=0, padx=(0, 10))
        
        self.filter_var = tk.StringVar(value="all")
        filter_combo = ttk.Combobox(filter_frame, textvariable=self.filter_var, 
                                   values=["all", "predictor_start", "adwin", "change_detection", 
                                          "change_point", "prediction_result", "debug"])
        filter_combo.grid(row=0, column=1, padx=(0, 20))
        filter_combo.bind('<<ComboboxSelected>>', self.filter_logs)
        
        # Clear button
        clear_btn = ttk.Button(filter_frame, text="Clear Logs", command=self.clear_logs)
        clear_btn.grid(row=0, column=2)
        
        # Log display
        log_frame = ttk.Frame(main_frame)
        log_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Text widget with scrollbar
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, 
                                                 width=100, height=30, 
                                                 font=('Consolas', 10))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure text tags for different log types
        self.log_text.tag_configure("predictor_start", foreground="purple")
        self.log_text.tag_configure("adwin", foreground="blue")
        self.log_text.tag_configure("change_detection", foreground="green", font=('Consolas', 10, 'bold'))
        self.log_text.tag_configure("change_point", foreground="red", font=('Consolas', 10, 'bold'))
        self.log_text.tag_configure("prediction_result", foreground="black")
        self.log_text.tag_configure("debug", foreground="gray")
        self.log_text.tag_configure("error", foreground="red")
        self.log_text.tag_configure("timestamp", foreground="gray", font=('Consolas', 9))
        
        self.log_count = 0
        self.all_logs = []  # Store all logs for filtering
    
    def start_server(self):
        """Start the socket server to receive logs"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('localhost', 9999))
            self.server_socket.listen(5)
            
            # Update status
            self.log_queue.put(('status', 'Server Status: Listening on localhost:9999'))
            
            while True:
                try:
                    client_socket, addr = self.server_socket.accept()
                    self.log_queue.put(('status', f'Server Status: Connected to {addr[0]}:{addr[1]}'))
                    
                    # Handle client in separate thread
                    client_thread = threading.Thread(target=self.handle_client, 
                                                   args=(client_socket,), daemon=True)
                    client_thread.start()
                    
                except Exception as e:
                    self.log_queue.put(('error', f'Server error: {str(e)}'))
                    
        except Exception as e:
            self.log_queue.put(('error', f'Failed to start server: {str(e)}'))
    
    def handle_client(self, client_socket):
        """Handle incoming log messages from a client"""
        try:
            buffer = ""
            while True:
                data = client_socket.recv(4096).decode('utf-8')
                if not data:
                    break
                
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            log_data = json.loads(line)
                            self.log_queue.put(('log', log_data))
                        except json.JSONDecodeError as e:
                            self.log_queue.put(('error', f'JSON decode error: {str(e)}'))
                            
        except Exception as e:
            self.log_queue.put(('error', f'Client handler error: {str(e)}'))
        finally:
            client_socket.close()
    
    def update_logs(self):
        """Update the GUI with new log messages (called periodically)"""
        try:
            while True:
                msg_type, data = self.log_queue.get_nowait()
                
                if msg_type == 'status':
                    self.status_label.config(text=data)
                elif msg_type == 'log':
                    self.add_log_message(data)
                elif msg_type == 'error':
                    self.add_log_message({
                        'timestamp': datetime.now().timestamp(),
                        'type': 'error',
                        'message': data,
                        'data': {}
                    })
                    
        except queue.Empty:
            pass
        
        # Schedule next update
        self.root.after(100, self.update_logs)
    
    def add_log_message(self, log_data):
        """Add a log message to the display"""
        self.log_count += 1
        self.log_count_label.config(text=f"Logs Received: {self.log_count}")
        
        # Store for filtering
        self.all_logs.append(log_data)
        
        # Check filter
        if self.should_show_log(log_data):
            self.display_log(log_data)
    
    def should_show_log(self, log_data):
        """Check if log should be displayed based on current filter"""
        filter_type = self.filter_var.get()
        return filter_type == "all" or log_data.get('type') == filter_type
    
    def display_log(self, log_data):
        """Display a single log message"""
        timestamp = datetime.fromtimestamp(log_data['timestamp']).strftime('%H:%M:%S.%f')[:-3]
        log_type = log_data.get('type', 'info')
        message = log_data.get('message', '')
        
        # Insert timestamp
        self.log_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
        
        # Insert main message with appropriate tag
        self.log_text.insert(tk.END, f"{message}\n", log_type)
        
        # Auto-scroll to bottom
        self.log_text.see(tk.END)
    
    def filter_logs(self, event=None):
        """Filter logs based on selected type"""
        self.log_text.delete(1.0, tk.END)
        for log_data in self.all_logs:
            if self.should_show_log(log_data):
                self.display_log(log_data)
    
    def clear_logs(self):
        """Clear all logs"""
        self.log_text.delete(1.0, tk.END)
        self.all_logs.clear()
        self.log_count = 0
        self.log_count_label.config(text="Logs Received: 0")


def main():
    root = tk.Tk()
    app = LogGUI(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nShutting down GUI...")


if __name__ == "__main__":
    main()
