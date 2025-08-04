import os
import time
import re
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

# === CONFIGURATION ===
BRAVE_PATH = "C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe"
DRIVER_PATH = "G:\\Software\\chromedriver-win64\\chromedriver.exe"
BATCH_DIR = "G:\\IITG\\Fellowship\\Prompts\\Questionaire and Answer\\After Validation\\trait_batches_500_nomap"
OUTPUT_DIR = "G:\\IITG\\Fellowship\\Prompts\\Questionaire and Answer\\After Validation\\Responses"
DELAY_AFTER_SUBMIT = 60
BATCHES_PER_GROUP = 15

# === SETUP ===
options = uc.ChromeOptions()
options.binary_location = BRAVE_PATH
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")

driver = uc.Chrome(
    options=options,
    version_main=137,
    driver_executable_path=DRIVER_PATH
)

driver.get("https://chat.openai.com/chat")
input("🔐 Manually log in and paste the personality prompt. Press ENTER when ready to start batch submission...")

os.makedirs(OUTPUT_DIR, exist_ok=True)
batch_files = sorted(os.listdir(BATCH_DIR))
batch_count = 0

for filename in batch_files:
    batch_path = os.path.join(BATCH_DIR, filename)
    output_path = os.path.join(OUTPUT_DIR, filename)

    if os.path.exists(output_path):
        print(f"✅ Already processed: {filename}")
        continue

    print(f"🚀 Injecting {filename} into ChatGPT...")

    try:
        # Load batch JSON
        with open(batch_path, "r", encoding="utf-8") as f:
            json_text = f.read()

        # Locate the ProseMirror editor
        editor_div = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.ProseMirror"))
        )

        # Inject JSON using execCommand
        driver.execute_script("""
            const editor = arguments[0];
            editor.focus();
            editor.innerHTML = '';
            const text = arguments[1];
            editor.dispatchEvent(new InputEvent('input', { bubbles: true }));
            document.execCommand('insertText', false, text);
        """, editor_div, json_text)

        # Click the submit button
        send_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "composer-submit-button"))
        )
        send_button.click()

    except Exception as e:
        print(f"❌ Injection/submission failed for {filename}: {e}")
        driver.save_screenshot(f"error_{filename}.png")
        continue

    print("⏳ Waiting for response...")
    #WebDriverWait(driver, 180).until(
    #lambda d: d.find_element(By.ID, "composer-submit-button").get_attribute("aria-label") == "Start voice mode"
    #)
    #WebDriverWait(driver, 180).until(
    #lambda d: d.find_element(By.ID, "composer-submit-button").get_attribute("aria-label") == "Start voice mode"
    #)
    #time.sleep(DELAY_AFTER_SUBMIT)
    #try:
     #   WebDriverWait(driver, 90).until(
      #      lambda d: d.find_element(By.ID, "composer-submit-button").get_attribute("aria-label") == "Start voice mode"
       # )
        #print("✅ Response complete.")
    #except Exception:
     #   print("⚠️ Timed out waiting for response. Proceeding anyway.")
      #  time.sleep(5)  # Small grace wait

      #WebDriverWait(driver, 60).until(
    #lambda d: (
       # (elements := d.find_elements(By.CSS_SELECTOR, "div.markdown")) and 
       # len(elements[-1].get_attribute("innerText").strip()) > 300
   # )
#)
    time.sleep(DELAY_AFTER_SUBMIT)

    # Extract last markdown response
    elements = driver.find_elements(By.CSS_SELECTOR, "div.markdown")
    response_text = elements[-1].text if elements else "❌ No response found"

    # Attempt to extract JSON array using regex
    match = re.search(r"(\[\s*\{[\s\S]*?\}\s*\])", response_text)
    if match:
        try:
            cleaned = json.loads(match.group(1))
            with open(output_path, "w", encoding="utf-8") as out:
                json.dump(cleaned, out, indent=2)
            print(f"✅ Saved cleaned JSON: {output_path}")
        except json.JSONDecodeError:
            with open(output_path, "w", encoding="utf-8") as out:
                out.write(response_text)
            print(f"⚠️ Saved raw text due to JSON error: {output_path}")
    else:
        with open(output_path, "w", encoding="utf-8") as out:
            out.write(response_text)
        print(f"⚠️ No JSON found. Saved raw response: {output_path}")

    print("-" * 40)
    batch_count += 1

    if batch_count % BATCHES_PER_GROUP == 0:
        input("🔁 Re-paste the personality prompt manually. Press ENTER to continue...")

print("🎉 All batches submitted successfully.")
driver.quit()
