# File: app.py
from flask import Flask, jsonify
import threading
import time
import sys
from config_loader import load_config
from discord_bot import DiscordBot

# Initialize Flask application
app = Flask(__name__)

# Global variables for bot instance and configuration
bot_instance = None
bot_thread = None
is_running = False

# --- Core Bot Monitoring Loop ---
def bot_monitor_loop():
    """The main loop run in a separate thread."""
    global bot_instance, is_running
    
    # Check if the bot driver was set up successfully
    if not bot_instance or not bot_instance.driver:
        print("‼️ Bot driver failed to initialize. Thread is stopping.")
        is_running = False
        return

    print("✅ Bot monitoring thread started.")
    
    try:
        while is_running:
            bot_instance.check_for_new_message()
            time.sleep(1.5) # Polling interval
    
    except Exception as e:
        print(f"🔥 Critical crash in bot thread: {e}")
    
    finally:
        if bot_instance:
            bot_instance.quit()
        is_running = False
        print("🛑 Bot monitoring thread stopped.")


# --- Flask Endpoints ---

@app.route('/start', methods=['POST', 'GET'])
def start_bot():
    """Initializes and starts the bot monitoring thread."""
    global bot_instance, bot_thread, is_running
    
    if is_running:
        return jsonify({"status": "error", "message": "Bot is already running."}), 400

    # 1. Load configuration
    config, success = load_config()
    if not success:
        return jsonify({"status": "error", "message": "Failed to load configuration. Check console for details."}), 500
    
    # 2. Initialize Bot
    bot_instance = DiscordBot(
        triggers=config.get('TRIGGERS', []),
        reply_text=config.get('REPLY_TEXT', 'Auto-reply.')
    )

    # 3. Setup Driver (Requires Manual Input - this is the necessary roadblock)
    if not bot_instance.setup_driver():
        return jsonify({"status": "error", "message": "Web driver setup failed. Check console."}), 500

    # 4. Start Thread
    is_running = True
    bot_thread = threading.Thread(target=bot_monitor_loop, daemon=True)
    bot_thread.start()

    return jsonify({"status": "success", "message": "Discord Bot initialized and monitoring started."})

@app.route('/stop', methods=['POST', 'GET'])
def stop_bot():
    """Stops the bot monitoring thread and closes the browser."""
    global bot_instance, is_running, bot_thread
    
    if not is_running:
        return jsonify({"status": "error", "message": "Bot is not running."}), 400

    is_running = False # Signal the loop to exit
    
    # Clean up the driver immediately
    if bot_instance:
        bot_instance.quit()
        bot_instance = None
    
    # Don't join the thread here as it might block the web server
    
    return jsonify({"status": "success", "message": "Discord Bot shutdown initiated."})

@app.route('/status', methods=['GET'])
def bot_status():
    """Returns the current status of the bot."""
    global is_running
    return jsonify({"status": "running" if is_running else "stopped"})


# --- Main Execution ---
if __name__ == '__main__':
    # When running the microservice, you still need to manually run the /start endpoint 
    # after the server starts, or trigger the setup_driver() first, as it requires
    # interactive user input.
    print("🚀 Starting Discord Bot Microservice (Flask).")
    print("Navigate to http://127.0.0.1:5000/start to initialize and run the bot.")
    
    # Set a custom host/port if needed, but 5000 is standard
    try:
        app.run(debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\nServer shutting down...")
        stop_bot()
        sys.exit(0)
