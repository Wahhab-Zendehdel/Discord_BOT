# File: config_loader.py
import json
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

# --- Configuration Loading ---

def load_config(config_filename='config.json'):
    """
    Loads configuration from a JSON file with comprehensive error handling.

    Returns:
        tuple: (config_dict, success_bool)
    """
    filepath = resource_path(config_filename)
    print(f"Loading configuration from: {filepath}")

    try:
        with open(filepath, 'r') as f:
            config = json.load(f)

        # Basic validation of required keys
        if not all(k in config for k in ['TRIGGERS', 'REPLY_TEXT']):
            print("❌ Configuration Error: 'TRIGGERS' or 'REPLY_TEXT' keys are missing.")
            return {}, False

        if not config['TRIGGERS']:
            print("⚠️ Warning: TRIGGERS list is empty. Bot will not respond to anything.")

        return config, True

    except FileNotFoundError:
        print(f"❌ Critical Error: Configuration file '{config_filename}' not found. Please create it.")
        return {}, False
    except json.JSONDecodeError:
        print(f"❌ Critical Error: Configuration file '{config_filename}' is not valid JSON.")
        return {}, False
    except Exception as e:
        print(f"❌ An unexpected error occurred while loading config: {e}")
        return {}, False

# Example usage (for testing this module independently)
if __name__ == '__main__':
    # You would need a config.json in the same directory for this test to work
    config, success = load_config()
    if success:
        print("Configuration loaded successfully.")
        print("Triggers:", config['TRIGGERS'])
    else:
        print("Configuration failed to load.")
