from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

# --- CONFIG ---
TRIGGERS = ["@Team", "@Teamleader", "@Elite Teamleader", "@High Teamleader"]
REPLY_TEXT = "Team take"

# --- START EDGE ---
options = webdriver.EdgeOptions()
options.add_argument("--start-maximized")

driver = webdriver.Edge(options=options)
driver.get("https://discord.com/app")

print("👉 Please log in manually in the Edge window and open your desired channel.")
input("Press Enter once ready...")

last_seen = ""

while True:
    try:
        # Find all messages in the currently open channel
        messages = driver.find_elements(By.CSS_SELECTOR, "li.messageListItem__5126c div.messageContent_c19a55")

        if not messages:
            continue

        # Take the very last message
        last_message_el = messages[-1]
        last_text = last_message_el.text.strip()

        # Avoid duplicates
        if last_text and last_text != last_seen:
            print("📩 New message:", repr(last_text))
            last_seen = last_text

            # Trigger check
            if any(trigger.lower() in last_text.lower() for trigger in TRIGGERS):
                print("🤖 Trigger detected → sending reply...")
                box = driver.find_element(By.CSS_SELECTOR, "div[role='textbox']")
                box.click()
                box.send_keys(REPLY_TEXT + Keys.ENTER)
                print("✅ Sent:", REPLY_TEXT)

        time.sleep(1)  # small delay for efficiency

    except Exception as e:
        print("⚠️ Error:", e)
        time.sleep(2)
