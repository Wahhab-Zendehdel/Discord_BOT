# File: discord_bot.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.service import Service
from selenium.common.exceptions import WebDriverException, NoSuchElementException, TimeoutException
import time
from config_loader import resource_path # Import utility

class DiscordBot:
    """
    A class to handle Discord message monitoring and replying using Selenium.
    """
    def __init__(self, triggers, reply_text):
        self.triggers = triggers
        self.reply_text = reply_text
        self.driver = None
        self.last_seen = ""
        self.message_selector = "li.messageListItem__5126c div.messageContent_c19a55"
        self.textbox_selector = "div[role='textbox']"

    def setup_driver(self):
        """Initializes the Edge WebDriver."""
        try:
            options = webdriver.EdgeOptions()
            options.add_argument("--start-maximized")
            options.add_argument("--log-level=3") # Suppress console warnings

            # Point to the bundled msedgedriver.exe
            driver_path = resource_path("msedgedriver.exe")
            service = Service(executable_path=driver_path)

            print("⚙️ Initializing Edge browser...")
            self.driver = webdriver.Edge(service=service, options=options)
            self.driver.get("https://discord.com/app")
            
            # This is crucial for manual login
            print("\n👉 ACTION REQUIRED: Please log in manually in the Edge window and open your desired channel.")
            input("Press Enter once you are logged in and positioned in the channel...")
            print("Bot is starting to monitor...")
            return True
        except WebDriverException as e:
            print(f"❌ Driver Setup Error: Could not initialize WebDriver.")
            print("   Ensure 'msedgedriver.exe' is in the correct location and matches your Edge version.")
            print(f"   Details: {e.msg.splitlines()[0]}")
            return False
        except Exception as e:
            print(f"❌ An unexpected error occurred during setup: {e}")
            return False

    def check_for_new_message(self):
        """
        Checks for the latest message and handles the reply if a trigger is found.
        
        Returns:
            bool: True if a reply was sent, False otherwise.
        """
        if not self.driver:
            print("❌ Cannot check messages: Driver is not initialized.")
            return False

        try:
            # 1. Find all messages
            messages = self.driver.find_elements(By.CSS_SELECTOR, self.message_selector)

            if not messages:
                return False

            # 2. Extract and sanitize the last message text
            last_message_el = messages[-1]
            last_text = last_message_el.text.strip()

            # 3. Check for duplicates and empty messages
            if last_text and last_text != self.last_seen:
                print(f"📩 New message: {repr(last_text)}")
                self.last_seen = last_text

                # 4. Check for trigger
                if any(trigger.lower() in last_text.lower() for trigger in self.triggers):
                    print("🤖 Trigger detected.")
                    self._send_reply()
                    return True
            
            return False

        except NoSuchElementException:
            # This is common if the page structure changes or Discord logs out
            print("⚠️ Monitoring Warning: Message elements (CSS selectors) not found. Check if the page is loaded/logged in.")
            return False
        except WebDriverException as e:
            print(f"❌ Monitoring Error: Connection to browser lost or issue with element interaction. Details: {e.msg.splitlines()[0]}")
            self.quit()
            # Re-raise to let the main loop know it should stop
            raise
        except Exception as e:
            print(f"❌ An unexpected error occurred during monitoring: {e}")
            return False

    def _send_reply(self):
        """Finds the text box and sends the configured reply."""
        try:
            box = self.driver.find_element(By.CSS_SELECTOR, self.textbox_selector)
            box.click()
            box.send_keys(self.reply_text + Keys.ENTER)
            print(f"✅ Reply Sent: '{self.reply_text}'")
        except NoSuchElementException:
            print("❌ Reply Error: Could not find the message text box (CSS selector changed?).")
        except Exception as e:
            print(f"❌ An unexpected error occurred while sending reply: {e}")

    def quit(self):
        """Closes the browser and cleans up resources."""
        if self.driver:
            print("🛑 Closing browser...")
            self.driver.quit()
            self.driver = None


# Example run for local testing (not used by the microservice)
if __name__ == '__main__':
    from config_loader import load_config
    
    config, success = load_config()
    if not success:
        sys.exit(1)

    bot = DiscordBot(
        triggers=config.get('TRIGGERS', []),
        reply_text=config.get('REPLY_TEXT', 'Auto-reply from the bot.')
    )
    
    if bot.setup_driver():
        # Start the monitoring loop
        try:
            while True:
                bot.check_for_new_message()
                time.sleep(1) # Polling interval
        except KeyboardInterrupt:
            print("\nShutting down bot as requested by user.")
        except Exception:
             # Already handled/logged in check_for_new_message
             pass
        finally:
            bot.quit()
