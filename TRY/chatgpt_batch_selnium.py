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
BATCH_DIR = "G:\\IITG\\Fellowship\\Prompts\\Questionaire and Answer\\After Validation\\trait_batches_clean_all_250"
OUTPUT_DIR = "G:\\IITG\\Fellowship\\Prompts\\Questionaire and Answer\\After Validation\\Rseponses"
DELAY_AFTER_SUBMIT = 60
BATCHES_PER_GROUP = 37

# === Setup ===
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
input("Manually log in and paste the personality prompt. Press ENTER when ready to start batch submission...")

os.makedirs(OUTPUT_DIR, exist_ok=True)
batch_files = sorted(os.listdir(BATCH_DIR))
batch_count = 0

for filename in batch_files:
    batch_path = os.path.join(BATCH_DIR, filename)
    output_path = os.path.join(OUTPUT_DIR, filename)

    if os.path.exists(output_path):
        print(f"Already processed: {filename}")
        continue

    print(f"Submitting {filename}...")

    try:
        # Wait for the file upload input to appear
        upload_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
        )

        # Make visible, clear previously selected files, and upload
        driver.execute_script("arguments[0].style.display = 'block';", upload_input)
        driver.execute_script("arguments[0].value = '';", upload_input)
        upload_input.send_keys(batch_path)

        # Wait for and click the send button after file upload
        send_button = WebDriverWait(driver, 25).until(
            EC.element_to_be_clickable((By.ID, "composer-submit-button"))
        )
        send_button.click()

    except Exception as e:
        print(f"Error uploading/submitting {filename}: {e}")
        driver.save_screenshot(f"error_{filename}.png")
        continue

    print(" Waiting for response...")
    time.sleep(DELAY_AFTER_SUBMIT)

    # Get last markdown response
    elements = driver.find_elements(By.CSS_SELECTOR, "div.markdown")
    response_text = elements[-1].text if elements else "\u274c No response found"

    # Try to extract the JSON array only
    match = re.search(r"(\[\s*\{.*?\}\s*\])", response_text, re.DOTALL)
    if match:
        json_str = match.group(1)
        try:
            parsed = json.loads(json_str)
            with open(output_path, "w", encoding="utf-8") as out:
                json.dump(parsed, out, indent=2)
            print(f" Saved cleaned JSON: {output_path}")
        except json.JSONDecodeError:
            with open(output_path, "w", encoding="utf-8") as out:
                out.write(response_text)
            print(f"Saved raw response due to JSON error: {output_path}")
    else:
        with open(output_path, "w", encoding="utf-8") as out:
            out.write(response_text)
        print(f" Saved raw response (no JSON detected): {output_path}")

    print("-" * 40)

    batch_count += 1
    if batch_count % BATCHES_PER_GROUP == 0:
        input(" Re-paste personality prompt manually. Press ENTER to continue...")

print("All batches submitted successfully.")
driver.quit()
