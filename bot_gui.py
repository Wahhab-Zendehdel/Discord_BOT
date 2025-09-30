# File: bot_gui.py
# This script uses Tkinter for the GUI and runs the Discord bot (Selenium/Flask)
# in a separate thread for background processing.

import tkinter as tk
from tkinter import ttk  # Import ttk for themed widgets
from tkinter.scrolledtext import ScrolledText
import threading
import time
import requests
import sys
import os
import json
from contextlib import redirect_stdout
from io import StringIO
import queue

# --- CONSOLIDATED LOGIC IMPORTS (Standard Python/External Libraries) ---
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys 
from selenium.webdriver.edge.service import Service
from selenium.common.exceptions import WebDriverException, NoSuchElementException, TimeoutException

# --- CONFIGURATION / UTILITIES (Merged from config_loader.py) ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller. """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_config(config_filename='config.json'):
    """ Loads configuration from a JSON file. """
    filepath = resource_path(config_filename)
    print(f"Loading configuration from: {filepath}")
    try:
        with open(filepath, 'r') as f:
            config = json.load(f)
        if not all(k in config for k in ['TRIGGERS', 'REPLY_TEXT']):
            print("❌ Configuration Error: 'TRIGGERS' or 'REPLY_TEXT' keys are missing.")
            return {}, False
        return config, True
    except FileNotFoundError:
        print(f"❌ Critical Error: Config file '{config_filename}' not found. Please create it.")
        return {}, False
    except json.JSONDecodeError:
        print(f"❌ Critical Error: Config file '{config_filename}' is not valid JSON.")
        return {}, False
    except Exception as e:
            print(f"❌ An unexpected error occurred while loading config: {e}")
            return {}, False

# --- DISCORD BOT CLASS (Modified from discord_bot.py) ---
class DiscordBot:
    """ Handles Discord monitoring logic, modified to use state flags instead of input(). """
    def __init__(self, triggers, reply_text):
        self.triggers = triggers
        self.reply_text = reply_text
        self.driver = None
        self.last_seen = ""
        self.is_monitoring = threading.Event() # Used to stop the loop
        self.is_driver_ready = threading.Event() # Used to signal login is complete
        self.message_selector = "li.messageListItem__5126c div.messageContent_c19a55"
        self.textbox_selector = "div[role='textbox']"

    def setup_driver(self):
        """Initializes the Edge WebDriver."""
        try:
            options = webdriver.EdgeOptions()
            options.add_argument("--start-maximized")
            options.add_argument("--log-level=3")

            driver_path = resource_path("msedgedriver.exe")
            service = Service(executable_path=driver_path)

            print("⚙️ Initializing Edge browser and opening Discord...")
            self.driver = webdriver.Edge(service=service, options=options)
            self.driver.get("https://discord.com/app")
            
            print("\n👉 ACTION REQUIRED: Please log in manually in the Edge window and open your desired channel.")
            print("Click 'START MONITORING' in the GUI once ready.")
            return True
        except WebDriverException as e:
            print("❌ Driver Setup Error: Could not initialize WebDriver.")
            print("   Ensure 'msedgedriver.exe' is correct and in the same directory.")
            print(f"   Details: {e.msg.splitlines()[0]}")
            return False
        except Exception as e:
            print(f"❌ An unexpected error occurred during setup: {e}")
            return False

    def start_monitoring_loop(self):
        """Starts the main monitoring loop, waiting for the ready signal."""
        if not self.driver:
            print("❌ Cannot start monitoring: Driver is not initialized.")
            return

        # Wait indefinitely until the user clicks the "Start Monitoring" button
        print("Waiting for monitoring signal from GUI...")
        self.is_driver_ready.wait()
        
        print("✅ Monitoring started.")
        self.is_monitoring.set()

        try:
            while self.is_monitoring.is_set():
                self.check_for_new_message()
                time.sleep(1.5) # Polling interval
        except Exception:
             # Errors handled in check_for_new_message, just stop the loop
             pass
        finally:
            self.quit()

    def check_for_new_message(self):
        """ Checks for the latest message and handles the reply. """
        try:
            messages = self.driver.find_elements(By.CSS_SELECTOR, self.message_selector)
            if not messages:
                return

            last_message_el = messages[-1]
            last_text = last_message_el.text.strip()

            if last_text and last_text != self.last_seen:
                print(f"📩 New message: {repr(last_text)}")
                self.last_seen = last_text

                if any(trigger.lower() in last_text.lower() for trigger in self.triggers):
                    print("🤖 Trigger detected.")
                    self._send_reply()
            
        except NoSuchElementException:
            print("⚠️ Monitoring Warning: Page structure error (logged out?).")
        except WebDriverException as e:
            print(f"❌ Monitoring Error: Connection to browser lost. Stopping bot.")
            self.is_monitoring.clear()
            raise
        except Exception as e:
            print(f"❌ An unexpected error occurred during monitoring: {e}")

    def _send_reply(self):
        """ Sends the configured reply. """
        try:
            box = self.driver.find_element(By.CSS_SELECTOR, self.textbox_selector)
            box.click()
            box.send_keys(self.reply_text + Keys.ENTER)
            print(f"✅ Reply Sent: '{self.reply_text}'")
        except Exception as e:
            print(f"❌ Reply Error: {e}")

    def quit(self):
        """Closes the browser and cleans up resources."""
        if self.driver:
            print("🛑 Closing browser...")
            self.driver.quit()
            self.driver = None
            self.is_monitoring.clear()
            self.is_driver_ready.clear()


# --- GUI APPLICATION CLASS ---
class BotGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Discord Auto-Reply Bot")
        self.geometry("800x600")
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Setup modern Windows 11-like theme
        self.style = ttk.Style(self)
        self.style.theme_use('clam') # 'clam' is a clean, flat base theme
        self.configure(bg='#f3f3f3') # Light gray background for modern feel

        self.bot_instance = None
        self.bot_thread = None
        self.log_queue = queue.Queue()
        self.is_running = False

        self._create_widgets()
        self.after(100, self._process_queue) # Start monitoring queue

    def _create_widgets(self):
        # 1. Define Modern Styles using ttk.Style
        
        # Frame and Label backgrounds matching the window background
        self.style.configure('Control.TFrame', background='#f3f3f3')
        self.style.configure('LogLabel.TLabel', background='#f3f3f3', foreground='#2b2b2b', font=("Segoe UI", 10, "bold"))
        
        # Base button style: flat, modern font, reduced border
        self.style.configure('Modern.TButton', 
                            font=('Segoe UI', 10, 'bold'), 
                            padding=10, 
                            relief='flat', 
                            background='#e1e1e1', # Very light gray for base state
                            foreground='#2b2b2b',
                            borderwidth=0)
        
        # Primary RUN button (Blue - Windows accent color)
        self.style.configure('Run.TButton', background='#0078d4', foreground='white')
        self.style.map('Run.TButton', 
                       background=[('active', '#005a9e'), ('disabled', '#cccccc')],
                       foreground=[('disabled', '#666666')])
        
        # Secondary MONITOR button (Green - Success/Go action)
        self.style.configure('Monitor.TButton', background='#107c10', foreground='white')
        self.style.map('Monitor.TButton', 
                       background=[('active', '#0c630c'), ('disabled', '#cccccc')],
                       foreground=[('disabled', '#666666')])

        # Danger STOP button (Red - Stop action)
        self.style.configure('Stop.TButton', background='#d43600', foreground='white')
        self.style.map('Stop.TButton', 
                       background=[('active', '#a32a00'), ('disabled', '#cccccc')],
                       foreground=[('disabled', '#666666')])
                       
        
        # 2. Control Frame (using ttk.Frame)
        control_frame = ttk.Frame(self, padding="10 10 10 10", style='Control.TFrame')
        control_frame.pack(fill='x')

        # Run Button (using ttk.Button)
        self.run_btn = ttk.Button(control_frame, text="1. RUN BOT (Open Browser)", command=self._start_bot_thread, 
                                 style='Run.TButton')
        self.run_btn.pack(side=tk.LEFT, padx=10)

        # Start Monitoring Button (using ttk.Button)
        self.monitor_btn = ttk.Button(control_frame, text="2. START MONITORING", command=self._start_monitoring, 
                                     state=tk.DISABLED, style='Monitor.TButton')
        self.monitor_btn.pack(side=tk.LEFT, padx=10)

        # Stop Button (using ttk.Button)
        self.stop_btn = ttk.Button(control_frame, text="STOP", command=self._stop_bot_thread, 
                                  state=tk.DISABLED, style='Stop.TButton')
        self.stop_btn.pack(side=tk.RIGHT, padx=10)

        # 3. Log Window
        log_label = ttk.Label(self, text="Bot Log and Status:", anchor='w', style='LogLabel.TLabel')
        log_label.pack(fill='x', pady=(10, 0), padx=10)

        self.log_text = ScrolledText(self, state='disabled', height=20, bg="#1e1e1e", fg="#f3f3f3", font=("Consolas", 10), relief=tk.FLAT)
        self.log_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Define color tags for the log window (Windows Terminal inspired)
        self.log_text.tag_config('error_tag', foreground='#ff5555')       # Red for errors (❌)
        self.log_text.tag_config('success_tag', foreground='#00ff7f')     # Bright Green for success (✅)
        self.log_text.tag_config('action_tag', foreground='#00bfff')      # Bright Blue for actions/prompts (👉, ⚙️)
        self.log_text.tag_config('warning_tag', foreground='#ffff00')     # Yellow for warnings/stops (⚠️, 🛑)
        self.log_text.tag_config('info_tag', foreground='#f3f3f3')        # Light Gray/White for general info (📩)

        # Redirect standard output to the log queue
        sys.stdout = self.StdoutRedirector(self.log_queue)

    def _process_queue(self):
        """Polls the queue for new log messages and updates the text widget."""
        while not self.log_queue.empty():
            # Get the (message, tag) tuple
            msg, tag = self.log_queue.get()
            
            self.log_text.config(state='normal')
            
            # Ensure the new message starts on a fresh line unless it's the very first entry.
            # This ensures each log entry is on its own line.
            if self.log_text.index(tk.END) != '1.0':
                msg = '\n' + msg
            
            # Insert message and apply the determined tag
            self.log_text.insert(tk.END, msg, tag)
            
            self.log_text.see(tk.END)
            self.log_text.config(state='disabled')
        self.after(100, self._process_queue)

    def _start_bot_thread(self):
        """Handler for the 'RUN BOT' button."""
        if self.is_running:
            print("Bot is already running.")
            return

        # 1. Load config and initialize bot instance
        config, success = load_config()
        if not success:
            return

        self.bot_instance = DiscordBot(
            triggers=config.get('TRIGGERS', []),
            reply_text=config.get('REPLY_TEXT', 'Auto-reply from the bot.')
        )
        
        # 2. Setup driver (this opens the Edge browser)
        if not self.bot_instance.setup_driver():
            self.bot_instance = None
            return

        # 3. Start monitoring loop in a background thread
        self.is_running = True
        self.bot_thread = threading.Thread(target=self.bot_instance.start_monitoring_loop, daemon=True)
        self.bot_thread.start()

        # Update button states
        self.run_btn.config(state=tk.DISABLED)
        self.monitor_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.NORMAL)

    def _start_monitoring(self):
        """Handler for the 'START MONITORING' button."""
        if self.bot_instance and self.bot_instance.driver:
            print("\n>> Signal received: Starting message monitoring...")
            # Set the event flag to allow the monitoring loop to proceed
            self.bot_instance.is_driver_ready.set()
            self.monitor_btn.config(state=tk.DISABLED)
        else:
            print("❌ Error: Driver is not initialized. Press 'RUN BOT' first.")

    def _stop_bot_thread(self):
        """Handler for the 'STOP' button."""
        if self.bot_instance:
            print("\n>> Stopping bot and closing browser...")
            self.bot_instance.is_monitoring.clear()
            self.bot_instance.quit() # Clean up driver
            self.is_running = False
            self.bot_instance = None
            # Restore initial button states
            self.run_btn.config(state=tk.NORMAL)
            self.monitor_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.DISABLED)
            print("Bot stopped.")

    def _on_closing(self):
        """Graceful shutdown when the window is closed."""
        self._stop_bot_thread()
        sys.stdout = sys.__stdout__ # Restore stdout
        self.destroy()

    class StdoutRedirector:
        """Helper class to redirect stdout print statements to the Tkinter queue."""
        def __init__(self, queue):
            self.queue = queue
        
        def write(self, s):
            # Check for non-empty string that isn't just whitespace
            if s and s.strip():
                tag = 'info_tag'
                s_strip = s.strip().lower()
                
                # Tag determination logic (using emojis/keywords)
                if 'critical error' in s_strip or '❌' in s:
                    tag = 'error_tag'
                elif 'trigger detected' in s_strip or '✅' in s or 'reply sent' in s_strip:
                    tag = 'success_tag'
                elif 'action required' in s_strip or '👉' in s or 'waiting' in s_strip or '⚙️' in s:
                    tag = 'action_tag'
                elif 'stop' in s_strip or 'monitoring warning' in s_strip or '⚠️' in s or 'closing browser' in s_strip or 'stopping bot' in s_strip or '🛑' in s:
                    tag = 'warning_tag'

                timestamp = time.strftime("[%H:%M:%S] ")
                # Put (message, tag) tuple into the queue. Newline handling is in _process_queue.
                self.queue.put((timestamp + s.strip(), tag))

        def flush(self):
            # Required for file-like objects
            pass

if __name__ == '__main__':
    # Add a fallback for the driver path to help PyInstaller or development
    # This ensures the script knows where to look for msedgedriver.exe
    if not os.path.exists(resource_path("msedgedriver.exe")):
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("CRITICAL: msedgedriver.exe not found in the same directory.")
        print("Please download it and place it alongside this script.")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        
    app = BotGUI()
    app.mainloop()
