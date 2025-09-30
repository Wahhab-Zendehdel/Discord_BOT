# File: bot_gui.py
# This script uses Tkinter for the GUI and runs the Discord bot (Selenium/Flask)
# in a separate thread for background processing.

import tkinter as tk
from tkinter import ttk  # Import ttk for themed widgets
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
import threading
import time
import sys
import os
import json
import queue

# --- CONSOLIDATED LOGIC IMPORTS (Standard Python/External Libraries) ---
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys 
from selenium.webdriver.edge.service import Service
from selenium.common.exceptions import WebDriverException, NoSuchElementException, TimeoutException

# --- CONFIGURATION / UTILITIES (Merged from config_loader.py) ---
# Define consistent global defaults for configuration file safety/fallback
DEFAULT_TRIGGERS = ['@team']
DEFAULT_REPLY = 'Team Take'

def resource_path(relative_path):
    """ Get absolute path to read-only bundled resource, works for dev and for PyInstaller. 
        Used only for msedgedriver.exe """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

CONFIG_FILE = 'config.json'
# Path for external, editable files (always relative to the executable/script location)
# This MUST NOT use sys._MEIPASS as we want to save and load from the same directory as the .exe
EXTERNAL_CONFIG_PATH = os.path.join(os.path.abspath("."), CONFIG_FILE)


def load_config():
    """ Loads configuration from the external JSON file. """
    print(f"Loading configuration from: {EXTERNAL_CONFIG_PATH}")
    try:
        # Use the external path for the config file
        with open(EXTERNAL_CONFIG_PATH, 'r') as f:
            config = json.load(f)
        
        # Validation checks
        if not all(k in config for k in ['TRIGGERS', 'REPLY_TEXT']):
            print("❌ Configuration Error: 'TRIGGERS' or 'REPLY_TEXT' keys are missing. Using defaults for missing keys.")
            # Use config.get(key, default) to keep valid parts and default missing parts
            return {
                'TRIGGERS': config.get('TRIGGERS', DEFAULT_TRIGGERS),
                'REPLY_TEXT': config.get('REPLY_TEXT', DEFAULT_REPLY)
            }, True
            
        return config, True
        
    except FileNotFoundError:
        print(f"⚠️ Warning: Config file '{CONFIG_FILE}' not found at expected location. Creating a default file.")
        default_config = {'TRIGGERS': DEFAULT_TRIGGERS, 'REPLY_TEXT': DEFAULT_REPLY}
        # Immediately save the default config to create the file
        save_config(default_config) 
        return default_config, True
        
    except json.JSONDecodeError:
        print(f"❌ Critical Error: Config file '{CONFIG_FILE}' is not valid JSON. Using defaults.")
        return {'TRIGGERS': DEFAULT_TRIGGERS, 'REPLY_TEXT': DEFAULT_REPLY}, False
        
    except Exception as e:
            print(f"❌ An unexpected error occurred while loading config: {e}. Using defaults.")
            return {'TRIGGERS': DEFAULT_TRIGGERS, 'REPLY_TEXT': DEFAULT_REPLY}, False

def save_config(config_data):
    """ Saves configuration data to the external JSON file. """
    try:
        # Use the external path for the config file
        with open(EXTERNAL_CONFIG_PATH, 'w') as f:
            json.dump(config_data, f, indent=4)
        print(f"✅ Configuration saved to: {EXTERNAL_CONFIG_PATH}")
        return True
    except Exception as e:
        print(f"❌ Error saving configuration: {e}")
        return False

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

            # Use resource_path for the bundled msedgedriver.exe
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
        
        print("✅ Monitoring started. Checking for triggers...")
        self.is_monitoring.set()

        try:
            while self.is_monitoring.is_set():
                # Configuration is now only loaded/updated on application start or via the GUI Settings button.
                # Removed redundant load_config() call here to prevent spam.
                
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

                # Use the instance variables, which hold the latest config from the GUI/load_config
                if any(trigger.lower() in last_text.lower() for trigger in self.triggers):
                    print(f"🤖 Trigger detected (using triggers: {self.triggers}).")
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
            # Use the instance variable
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
        self.current_config = {'TRIGGERS': ['@team'], 'REPLY_TEXT': 'Team Take'}
        
        # Initial load of config
        self.current_config, _ = load_config()

        self._create_widgets()
        self.after(100, self._process_queue) # Start monitoring queue

    def _create_widgets(self):
        # 1. Define Modern Styles using ttk.Style
        self.style.configure('Control.TFrame', background='#f3f3f3')
        self.style.configure('LogLabel.TLabel', background='#f3f3f3', foreground='#2b2b2b', font=("Segoe UI", 10, "bold"))
        self.style.configure('Modern.TButton', 
                            font=('Segoe UI', 10, 'bold'), 
                            padding=10, 
                            relief='flat', 
                            background='#e1e1e1', 
                            foreground='#2b2b2b',
                            borderwidth=0)
        self.style.configure('Run.TButton', background='#0078d4', foreground='white')
        self.style.map('Run.TButton', 
                       background=[('active', '#005a9e'), ('disabled', '#cccccc')],
                       foreground=[('disabled', '#666666')])
        self.style.configure('Monitor.TButton', background='#107c10', foreground='white')
        self.style.map('Monitor.TButton', 
                       background=[('active', '#0c630c'), ('disabled', '#cccccc')],
                       foreground=[('disabled', '#666666')])
        self.style.configure('Stop.TButton', background='#d43600', foreground='white')
        self.style.map('Stop.TButton', 
                       background=[('active', '#a32a00'), ('disabled', '#cccccc')],
                       foreground=[('disabled', '#666666')])
        self.style.configure('Settings.TButton', background='#5e5e5e', foreground='white')
        self.style.map('Settings.TButton', 
                       background=[('active', '#3c3c3c')])
                       
        
        # 2. Control Frame (using ttk.Frame)
        control_frame = ttk.Frame(self, padding="10 10 10 10", style='Control.TFrame')
        control_frame.pack(fill='x')

        # Run Button
        self.run_btn = ttk.Button(control_frame, text="1. RUN BOT (Open Browser)", command=self._start_bot_thread, 
                                 style='Run.TButton')
        self.run_btn.pack(side=tk.LEFT, padx=10)

        # Start Monitoring Button
        self.monitor_btn = ttk.Button(control_frame, text="2. START MONITORING", command=self._start_monitoring, 
                                     state=tk.DISABLED, style='Monitor.TButton')
        self.monitor_btn.pack(side=tk.LEFT, padx=10)
        
        # Settings Button
        self.settings_btn = ttk.Button(control_frame, text="SETTINGS", command=self._create_settings_window, 
                                      style='Settings.TButton')
        self.settings_btn.pack(side=tk.LEFT, padx=(30, 10))

        # Stop Button
        self.stop_btn = ttk.Button(control_frame, text="STOP", command=self._stop_bot_thread, 
                                  state=tk.DISABLED, style='Stop.TButton')
        self.stop_btn.pack(side=tk.RIGHT, padx=10)

        # 3. Log Window
        log_label = ttk.Label(self, text="Bot Log and Status:", anchor='w', style='LogLabel.TLabel')
        log_label.pack(fill='x', pady=(10, 0), padx=10)

        self.log_text = ScrolledText(self, state='disabled', height=20, bg="#1e1e1e", fg="#f3f3f3", font=("Consolas", 10), relief=tk.FLAT)
        self.log_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Define color tags for the log window
        self.log_text.tag_config('error_tag', foreground='#ff5555')       
        self.log_text.tag_config('success_tag', foreground='#00ff7f')     
        self.log_text.tag_config('action_tag', foreground='#00bfff')      
        self.log_text.tag_config('warning_tag', foreground='#ffff00')     
        self.log_text.tag_config('info_tag', foreground='#f3f3f3')        

        # Redirect standard output to the log queue
        sys.stdout = self.StdoutRedirector(self.log_queue)

    def _create_settings_window(self):
        """Creates the pop-up window for configuration settings."""
        if self.is_running:
            messagebox.showwarning("Cannot Change Settings", "Please STOP the bot before changing configuration.")
            return

        settings_win = tk.Toplevel(self)
        settings_win.title("Bot Settings")
        settings_win.geometry("500x300")
        settings_win.configure(bg='#f3f3f3')
        settings_win.transient(self) # Make the settings window stay on top

        frame = ttk.Frame(settings_win, padding="15", style='Control.TFrame')
        frame.pack(fill='both', expand=True)

        # Triggers Field
        ttk.Label(frame, text="Triggers (comma-separated):", style='LogLabel.TLabel').pack(anchor='w', pady=(0, 5))
        
        # Convert list of triggers back to comma-separated string for display
        trigger_str = ", ".join(self.current_config['TRIGGERS'])
        triggers_var = tk.StringVar(value=trigger_str)
        triggers_entry = ttk.Entry(frame, textvariable=triggers_var, width=60)
        triggers_entry.pack(fill='x', pady=(0, 15))

        # Reply Text Field
        ttk.Label(frame, text="Reply Message:", style='LogLabel.TLabel').pack(anchor='w', pady=(0, 5))
        reply_var = tk.StringVar(value=self.current_config['REPLY_TEXT'])
        reply_entry = ttk.Entry(frame, textvariable=reply_var, width=60)
        reply_entry.pack(fill='x', pady=(0, 20))

        def save_and_close():
            # 1. Parse and validate inputs
            new_triggers_str = triggers_var.get().strip()
            new_triggers = [t.strip() for t in new_triggers_str.split(',') if t.strip()]
            new_reply = reply_var.get().strip()

            if not new_reply or not new_triggers:
                 messagebox.showerror("Validation Error", "Triggers and Reply Message cannot be empty.")
                 return

            # 2. Update config object
            new_config = {
                'TRIGGERS': new_triggers,
                'REPLY_TEXT': new_reply
            }

            # 3. Save to file and update GUI instance
            if save_config(new_config):
                self.current_config = new_config
                
                # If the bot instance exists (but isn't monitoring), update its parameters
                if self.bot_instance:
                    self.bot_instance.triggers = new_config['TRIGGERS']
                    self.bot_instance.reply_text = new_config['REPLY_TEXT']
                    
                settings_win.destroy()

        # Save Button
        save_btn = ttk.Button(frame, text="Save Settings", command=save_and_close, style='Monitor.TButton')
        save_btn.pack(side=tk.RIGHT)
        
        # Cancel Button
        cancel_btn = ttk.Button(frame, text="Cancel", command=settings_win.destroy, style='Modern.TButton')
        cancel_btn.pack(side=tk.RIGHT, padx=10)


    def _process_queue(self):
        """Polls the queue for new log messages and updates the text widget."""
        while not self.log_queue.empty():
            # Get the (message, tag) tuple
            msg, tag = self.log_queue.get()
            
            self.log_text.config(state='normal')
            
            # Ensure the new message starts on a fresh line unless it's the very first entry.
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

        # 1. Load config and initialize bot instance (using the current_config)
        # Config is already loaded in __init__ and updated by settings window
        
        self.bot_instance = DiscordBot(
            triggers=self.current_config.get('TRIGGERS', []),
            reply_text=self.current_config.get('REPLY_TEXT', 'Team Take')
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
        self.settings_btn.config(state=tk.DISABLED)

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
            self.settings_btn.config(state=tk.NORMAL)
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
