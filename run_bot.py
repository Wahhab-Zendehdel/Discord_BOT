# File: run_bot.py
import threading
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.common.exceptions import WebDriverException, TimeoutException
import subprocess
import os
import sys

# --- Utility Function ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller. """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Standard Python execution path
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
    
# --- Configuration ---
FLASK_SERVER_URL = "http://127.0.0.1:5000"
START_ENDPOINT = f"{FLASK_SERVER_URL}/start"
DRIVER_PATH = resource_path("msedgedriver.exe")

def start_flask_server():
    """Starts the Flask server using app.py as a subprocess."""
    print("Starting Flask microservice...")
    
    try:
        if getattr(sys, 'frozen', False):
            # If frozen (packaged), run the executable itself in a separate process
            # Note: We still let the output go to console for visibility
            server_process = subprocess.Popen([sys.executable])
        else:
            # If running in development, run the app.py script.
            # Using the '-u' flag ensures output is unbuffered, which is better for real-time console visibility.
            # We remove the output piping so errors are printed directly to the console.
            server_process = subprocess.Popen([sys.executable, '-u', 'app.py'])
            
        print(f"Flask process started with PID: {server_process.pid}")
        return server_process
    except FileNotFoundError:
        print("❌ Error: Python interpreter or app.py not found. Ensure 'app.py' exists and Python is in PATH.")
        return None
    except Exception as e:
        print(f"❌ Error starting Flask server: {e}")
        return None

def trigger_bot_via_webdriver():
    """
    Starts a minimal web driver instance to hit the /start endpoint, 
    automating the bot setup and manual login prompt.
    """
    print("Initializing automation client to trigger bot startup...")
    client_driver = None
    try:
        # 1. Setup minimal Edge options for the client
        options = webdriver.EdgeOptions()
        options.add_argument("--headless") # Run client silently in the background
        options.add_argument("--log-level=3")
        
        # 2. Initialize the client driver
        service = Service(executable_path=DRIVER_PATH)
        client_driver = webdriver.Edge(service=service, options=options)
        
        # 3. Hit the /start endpoint
        print(f"Attempting to access {START_ENDPOINT}...")
        client_driver.get(START_ENDPOINT)
        
        # 4. Check the response (The response is JSON, but since we are running headless,
        # we check the page source for the expected success message)
        time.sleep(2) # Give Flask time to process the request and launch the main browser
        
        # Note: We rely on the /start function in app.py launching the *main* bot browser.
        if "success" in client_driver.page_source.lower():
            print("✅ Bot startup triggered successfully via web driver.")
            print("The main Discord browser window should now be open, awaiting login.")
        else:
            print("❌ Bot startup failed or returned an error. Check the server console.")
            
    except WebDriverException as e:
        print(f"❌ WebDriver Error in client: Could not launch client driver or connection error.")
        print(f"   Details: {e.msg.splitlines()[0]}")
    except Exception as e:
        print(f"❌ An unexpected error occurred in the client driver: {e}")
    finally:
        if client_driver:
            # Close the silent client browser immediately after execution
            client_driver.quit()

def wait_for_server_start(url, max_retries=10, delay=1):
    """Waits for the Flask server to become available."""
    print(f"Waiting for server at {url} to be ready...")
    for i in range(max_retries):
        # We need to check if the server subprocess has already crashed
        if server_process and server_process.poll() is not None:
            print("❌ Server process crashed immediately upon startup. Check console for Flask server errors.")
            return False

        try:
            response = requests.get(f"{url}/status") # Use the /status endpoint
            if response.status_code == 200:
                print("Server is ready.")
                return True
        except requests.exceptions.ConnectionError:
            print(f"Attempt {i+1}/{max_retries}: Server not yet available, retrying in {delay}s...")
            time.sleep(delay)
    print("❌ Failed to connect to server after multiple attempts.")
    return False

# --- Main Execution ---
if __name__ == '__main__':
    server_process = None
    try:
        # 1. Start the Flask server in a separate subprocess
        server_process = start_flask_server()
        if not server_process:
            sys.exit(1)
            
        # 2. Wait for the server to spin up
        if wait_for_server_start(FLASK_SERVER_URL):
            # 3. Trigger the bot startup via a separate web driver client
            trigger_bot_via_webdriver()
            
            # The main execution thread can now wait for the server subprocess to exit
            print("\nRunner script finished its job. Bot process is now running in the background.")
            print("Press Ctrl+C to stop the entire process group.")
            server_process.wait() # Wait for the Flask server to finish

    except KeyboardInterrupt:
        print("\nInterrupt received. Shutting down...")
    
    finally:
        # Gracefully terminate the server process if it's still running
        if server_process and server_process.poll() is None:
            # Use a platform-specific kill to stop the server subprocess
            print("Attempting to terminate Flask server process...")
            try:
                if os.name == 'nt': # Windows
                    # /T kills the process and any child processes it started (like the actual browser)
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(server_process.pid)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else: # Unix/Linux/macOS
                    server_process.terminate()
            except Exception as e:
                print(f"Warning: Could not gracefully kill process: {e}")
        
        # Give a moment for cleanup
        time.sleep(1)
        sys.exit(0)
