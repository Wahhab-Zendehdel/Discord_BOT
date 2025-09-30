# Discord Auto-Reply Bot

This project is a versatile and powerful auto-reply bot for Discord, designed to monitor channels and automatically respond to trigger messages. It uses Selenium to interact with the Discord web application in a browser, providing a flexible solution that does not require a Discord API bot token.

The bot can be run in three different modes:
- **GUI Application:** A user-friendly graphical interface for easy control.
- **Command-Line Script:** A simple script for headless or automated environments.
- **Flask Microservice:** An API-driven approach for integration with other systems.

## Features

- **Trigger-Based Replies:** Automatically sends a pre-configured message when specific keywords or phrases are detected.
- **Multiple Execution Modes:** Run the bot with a GUI, from the command line, or as a microservice.
- **Configuration via JSON:** Easily customize triggers and reply text by editing a `config.json` file.
- **Manual Login:** Operates through a standard browser, requiring a manual user login, which enhances security and avoids Discord API limitations.
- **Cross-Platform:** Built with Python, making it compatible with Windows, macOS, and Linux.

## Requirements

Before you begin, ensure you have the following installed:

- **Python 3.x:** Download from [python.org](https://www.python.org/).
- **Microsoft Edge:** The bot uses Edge as its browser for automation.
- **Required Python Libraries:** Install using pip:
  ```bash
  pip install flask selenium requests
  ```

## Setup Instructions

1. **Download `msedgedriver.exe`:**
   - The bot requires the Microsoft Edge WebDriver to control the browser.
   - **Check your Edge version:** Open Edge, go to `Settings > About Microsoft Edge`, and note the version number (e.g., `123.0.1234.56`).
   - **Download the matching driver:** Visit the [Microsoft Edge WebDriver page](https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/) and download the driver that corresponds to your Edge version.
   - **Place the driver:** Unzip the downloaded file and place `msedgedriver.exe` in the root directory of the project, alongside the Python scripts.

2. **Configure the Bot:**
   - Open the `config.json` file in a text editor.
   - **`TRIGGERS`**: A list of strings that the bot will look for in new messages. The bot is not case-sensitive.
   - **`REPLY_TEXT`**: The message the bot will send when a trigger is detected.

   Example `config.json`:
   ```json
   {
     "TRIGGERS": [
       "@Team",
       "urgent help"
     ],
     "REPLY_TEXT": "Message received. The team has been notified."
   }
   ```

## Usage Guide

The bot requires a one-time manual login after each launch. Follow the instructions for your chosen execution mode.

### 1. GUI Application (`bot_gui.py`)

This is the recommended method for most users.

- **Run the script:**
  ```bash
  python bot_gui.py
  ```
- **Instructions:**
  1. Click **"1. RUN BOT (Open Browser)"**. A new Edge window will open and navigate to Discord.
  2. **Log in to Discord manually** in the Edge window and navigate to the server and channel you want to monitor.
  3. Once you are in the correct channel, click **"2. START MONITORING"** in the GUI.
  4. The bot is now active. You can minimize the GUI and the browser window.
  5. To stop the bot, click **"STOP"**.

### 2. Command-Line Script (`run_bot.py`)

Ideal for users who prefer a terminal-based interface.

- **Run the script:**
  ```bash
  python run_bot.py
  ```
- **Instructions:**
  1. The script will automatically start the background server and open a new Edge window for Discord.
  2. **Log in to Discord manually** and navigate to the desired channel.
  3. The bot will start monitoring automatically after a brief delay. The console will indicate when monitoring has begun.
  4. To stop the bot, press `Ctrl+C` in the terminal where you ran the script.

### 3. Flask Microservice (`app.py`)

For advanced users or integration purposes.

- **Run the server:**
  ```bash
  python app.py
  ```
- **Instructions:**
  1. The server will start and be accessible at `http://127.0.0.1:5000`.
  2. To start the bot, send a `POST` or `GET` request to the `/start` endpoint (e.g., by navigating to `http://127.0.0.1:5000/start` in a browser).
  3. This will open the Edge browser. **Log in to Discord manually** and navigate to the channel.
  4. Press `Enter` in the console window that is running `app.py` to confirm that you are logged in and ready to monitor.
  5. The bot is now running.
  6. To stop the bot, send a request to the `/stop` endpoint.

## How It Works

The project is composed of several key components:

- **`discord_bot.py`**: The core class that uses Selenium to drive the web browser, monitor for messages, and send replies.
- **`app.py`**: A Flask web server that provides API endpoints (`/start`, `/stop`, `/status`) to control the bot.
- **`run_bot.py`**: A command-line utility that automates the process of starting the Flask server and initializing the bot.
- **`bot_gui.py`**: A Tkinter-based GUI that provides a user-friendly interface for managing the bot.
- **`config.json`**: The configuration file where users define triggers and reply messages.
- **`config_loader.py`**: A utility module for loading and validating the `config.json` file.

## License

This project is licensed under the terms of the `LICENSE` file.