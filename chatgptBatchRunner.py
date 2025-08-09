import os
import time
import re
import json
import hashlib
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

# === CONFIGURATION ===
BRAVE_PATH = "C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe"
DRIVER_PATH = "G:\\Software\\chromedriver-win64\\chromedriver.exe"
BATCH_DIR = "G:\\IITG\\Fellowship\\Experiment Design\\Code\\trait_batches_500_nomap"
OUTPUT_DIR = "G:\\IITG\\Fellowship\\Experiment Design\\Code\\Responses"
CLEANUP_INTERVAL = 60  # purge every 60 batches
counter = True

options = uc.ChromeOptions()
options.binary_location = BRAVE_PATH
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")

driver = uc.Chrome(
    options=options,
    version_main=139,
    driver_executable_path=DRIVER_PATH
)

driver.get("https://chat.openai.com/chat")
input("Manually log in and paste the personality prompt. Press ENTER when ready to start batch submission...")

os.makedirs(OUTPUT_DIR, exist_ok=True)
batch_files = sorted(os.listdir(BATCH_DIR))
seen_hashes = {}

def clean_json_string(json_str):
    cleaned = json_str.replace("“", "\"").replace("”", "\"").replace("’", "'")
    cleaned = re.sub(r",\s*(\]|\})", r"\1", cleaned)
    return cleaned

def extract_json_flexible(response_text):
    match = re.search(r"(\[\s*\{[\s\S]+?\}\s*\])", response_text)
    if match:
        return match.group(1), "direct"
    block_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", response_text)
    if block_match:
        nested = re.search(r"(\[\s*\{[\s\S]+?\}\s*\])", block_match.group(1))
        if nested:
            return nested.group(1), "codeblock"
    fallback_objs = re.findall(r"\{[\s\S]+?\}", response_text)
    if fallback_objs:
        try:
            joined = "[" + ",".join(fallback_objs) + "]"
            json.loads(joined)
            return joined, "fragment-fallback"
        except:
            pass
    return None, "none"

def clean_assistant_dom():
    try:
        driver.execute_script("""
            const assistantBlocks = document.querySelectorAll("div[data-message-author-role='assistant']");
            assistantBlocks.forEach((el, idx) => {
                if (idx < assistantBlocks.length - 1) {
                    el.innerHTML = "<div style='color:gray'>[Purged for memory]</div>";
                }
            });
        """)
        print("🧹 DOM cleanup: older assistant messages purged. {batch_number}")
    except Exception as e:
        print(f"⚠️ DOM cleanup failed: {e}")

# === MAIN LOOP ===
for idx, filename in enumerate(batch_files):
    batch_path = os.path.join(BATCH_DIR, filename)
    output_path = os.path.join(OUTPUT_DIR, filename)
    counter = True
    
    if os.path.exists(output_path):
        print(f"✅ Already processed: {filename}")
        continue

    # Extract batch number directly from filename
    try:
        batch_number = int(re.search(r'\d+', filename).group())
    except:
        batch_number = idx  # fallback

    # Perform DOM cleanup every `cleanup_interval` batches
    if batch_number > 0 and batch_number % CLEANUP_INTERVAL == 0:
        clean_assistant_dom()


    print(f"\n🚀 Injecting {filename} into ChatGPT...")

    try:
        with open(batch_path, "r", encoding="utf-8") as f:
            json_text = f.read()
    except Exception as e:
        print(f"❌ Failed to read JSON file: {e}")
        continue

    prompt_text = f"{json_text}\n\nREMINDER: Respond only with:\n[\n  {{\n    \"trait\": \"...\",\n    \"question\": \"...\",\n    \"selected_option\": \"...\"\n  }}\n]\nNo summaries, no commentary, no headings."

    try:
        editor_div = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.ProseMirror"))
        )
        print("🧠 Found ChatGPT input editor.")

        try:
            driver.execute_script("""
                const editor = arguments[0];
                const text = arguments[1];
                editor.focus();
                editor.innerHTML = '';
                editor.dispatchEvent(new InputEvent('input', { bubbles: true }));
                document.execCommand('insertText', false, text);
                editor.dispatchEvent(new InputEvent('input', { bubbles: true }));
            """, editor_div, prompt_text)
        except Exception as e:
            print(f"❌ Failed to inject prompt via JS: {e}")
            continue

        time.sleep(3)
        try:
            send_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "composer-submit-button"))
            )
            send_button.click()
            print("📤 Submitted batch to ChatGPT.")
        except Exception as e:
            print(f"❌ Failed to click send button: {e}")
            continue

        retries = 0
        max_retries = 15
        found_json = False
        latest_text = ""

        print("⏳ Waiting for response...")
        time.sleep(45)
        poll_interval = 15

        while not found_json:
            for _ in range(max_retries):
                try:
                    latest_text = driver.execute_script("""
                        const blocks = Array.from(document.querySelectorAll("div[data-message-author-role='assistant']"));
                        const last = blocks.at(-1);
                        if (!last) return '';
                        last.scrollIntoView({ behavior: 'auto', block: 'center' });
                        last.focus?.();
                        last.offsetHeight;
                        window.scrollBy(0, 1); window.scrollBy(0, -1);
                        const codes = last.querySelectorAll("pre code");
                        return codes.length > 0
                            ? Array.from(codes).map(c => c.innerText.trim()).join("\\n\\n")
                            : last.innerText.trim();
                    """)
                except Exception as e:
                    print(f"❌ Error during JS execution: {e}")
                    time.sleep(15)
                    retries = 0
                    continue

                print(f"🔍 Retry {retries + 1}: length={len(latest_text)} chars")

                if "]" in latest_text:
                    print("✅ Detected closing bracket in response.")
                    found_json = True
                    break
                else:
                    print("⏳ ']' not found in response yet. Waiting more...")
                    time.sleep(poll_interval)
                    retries += 1

            if not found_json:
                print("🔁 No valid JSON found after retries. Refreshing page for a hard reload...")
                try:
                    driver.refresh()
                    time.sleep(10)  # wait for the page to load after refresh
                   # input("🔄 Page refreshed. Please log in again and press ENTER to resume...")
                    retries = 0
                except Exception as e:
                    print(f"❌ Error during page refresh: {e}")
                counter = False
                time.sleep(20)
                break

        if counter :    
            response_hash = hashlib.sha256(latest_text.encode("utf-8")).hexdigest()
            print(f"🔑 SHA256 of response: {response_hash}")
            if response_hash in seen_hashes:
                print(f"⚠️ Duplicate response detected! Matches: {seen_hashes[response_hash]}")
            else:
                seen_hashes[response_hash] = filename

            json_text, source_type = extract_json_flexible(latest_text)
            if json_text:
                try:
                    cleaned = json.loads(clean_json_string(json_text))
                    with open(output_path, "w", encoding="utf-8") as out:
                        json.dump(cleaned, out, indent=2)
                    print(f"✅ Saved JSON ({source_type}): {output_path}")
                except json.JSONDecodeError as e:
                    print(f"⚠️ JSON decode error: {e}")
                    with open(output_path, "w", encoding="utf-8") as out:
                        out.write(latest_text)
                    print("⚠️ Fallback: saved raw response.")
            else:
                with open(output_path, "w", encoding="utf-8") as out:
                    out.write(latest_text)
                print("⚠️ No JSON pattern matched. Saved raw.")

            print("⏳ Waiting extra 3 seconds before next batch...")
            time.sleep(3)

    except Exception as e:
        print(f"❌ Exception while processing {filename}: {e}")
        driver.save_screenshot(f"error_{filename}.png")

    print("-" * 40)

print("🎉 All batches submitted successfully.")
driver.quit()
