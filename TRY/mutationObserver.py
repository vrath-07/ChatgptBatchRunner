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
BATCH_DIR = "G:\\IITG\\Fellowship\\Prompts\\Questionaire and Answer\\After Validation\\trait_batches_500_nomap"
OUTPUT_DIR = "G:\\IITG\\Fellowship\\Prompts\\Questionaire and Answer\\After Validation\\Responses"

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
seen_hashes = {}

# === UTILITIES ===
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

# === MAIN LOOP ===
for filename in batch_files:
    batch_path = os.path.join(BATCH_DIR, filename)
    output_path = os.path.join(OUTPUT_DIR, filename)

    if os.path.exists(output_path):
        print(f"✅ Already processed: {filename}")
        continue

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

        driver.execute_script("""
            const editor = arguments[0];
            const text = arguments[1];
            editor.focus();
            editor.innerHTML = '';
            editor.dispatchEvent(new InputEvent('input', { bubbles: true }));
            document.execCommand('insertText', false, text);
            editor.dispatchEvent(new InputEvent('input', { bubbles: true }));
        """, editor_div, prompt_text)

        time.sleep(1.5)

        send_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "composer-submit-button"))
        )
        send_button.click()
        print("📤 Submitted batch to ChatGPT.")

        pre_count = driver.execute_script(
            "return document.querySelectorAll('div[data-message-author-role=\"assistant\"]').length;"
        )
        print("👁️ Waiting for one new assistant response block...")

        WebDriverWait(driver, 180).until(
            lambda d: d.execute_script(
                f"return document.querySelectorAll('div[data-message-author-role=\"assistant\"]').length > {pre_count};"
            )
        )
        print("✅ New assistant response block appeared. Waiting for it to stabilize...")

        # Observe response stabilization
        driver.execute_script("""
            const blocks = document.querySelectorAll("div[data-message-author-role='assistant']");
            const last = blocks[blocks.length - 1];
            window.__observeResponse__ = {
                lastLen: 0,
                stableSince: Date.now(),
                block: last
            };
            console.log("[Observer] Starting stabilization monitor...");
            window.__observeResponse__.interval = setInterval(() => {
                const len = window.__observeResponse__.block.innerText.length;
                if (len !== window.__observeResponse__.lastLen) {
                    console.log("[Observer] Change detected: " + len);
                    window.__observeResponse__.lastLen = len;
                    window.__observeResponse__.stableSince = Date.now();
                }
            }, 1000);
        """)

        WebDriverWait(driver, 120).until(
            lambda d: d.execute_script("return Date.now() - window.__observeResponse__.stableSince > 5000")
        )
        driver.execute_script("clearInterval(window.__observeResponse__.interval);")
        print("✅ Response stabilized.")

        raw_response = driver.execute_script("""
            const blocks = Array.from(document.querySelectorAll("div[data-message-author-role='assistant']"));
            const last = blocks.at(-1);
            const codes = last.querySelectorAll("pre code");
            return codes.length > 0
                ? Array.from(codes).map(c => c.innerText.trim()).join("\\n\\n")
                : last.innerText.trim();
        """)

        print("\n🔍 ----- DEBUG -----")
        print("📏 Combined response length:", len(raw_response))
        print("📄 Response preview:\n", raw_response[:500])
        print("🔍 ------------------\n")

        if not raw_response.strip():
            print("⚠️ Empty response! Skipping save.")
            continue

        response_hash = hashlib.sha256(raw_response.encode("utf-8")).hexdigest()
        print(f"🔑 SHA256 of response: {response_hash}")
        if response_hash in seen_hashes:
            print(f"⚠️ Duplicate response detected! Matches: {seen_hashes[response_hash]}")
        else:
            seen_hashes[response_hash] = filename

        json_text, source_type = extract_json_flexible(raw_response)
        if json_text:
            try:
                cleaned = json.loads(clean_json_string(json_text))
                with open(output_path, "w", encoding="utf-8") as out:
                    json.dump(cleaned, out, indent=2)
                print(f"✅ Saved JSON ({source_type}): {output_path}")
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON decode error: {e}")
                with open(output_path, "w", encoding="utf-8") as out:
                    out.write(raw_response)
                print("⚠️ Fallback: saved raw response.")
        else:
            with open(output_path, "w", encoding="utf-8") as out:
                out.write(raw_response)
            print("⚠️ No JSON pattern matched. Saved raw.")

    except Exception as e:
        print(f"❌ Exception while processing {filename}: {e}")
        driver.save_screenshot(f"error_{filename}.png")

    print("-" * 40)

print("🎉 All batches submitted successfully.")
driver.quit()
