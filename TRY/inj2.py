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
input("Manually log in and paste the personality prompt. Press ENTER when ready to start batch submission...")

os.makedirs(OUTPUT_DIR, exist_ok=True)
batch_files = sorted(os.listdir(BATCH_DIR))
batch_count = 0

# === CLEAN JSON STRING FUNCTION ===
def clean_json_string(json_str):
    cleaned = json_str.replace("“", "\"").replace("”", "\"").replace("’", "'")
    cleaned = re.sub(r",\s*(\]|\})", r"\1", cleaned)
    return cleaned

# === JSON EXTRACTOR FUNCTION ===
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

    # === FORMAT INJECTION + NONCE ===
    format_reminder = (
        "REMINDER: Respond only with:\n"
        "[\n"
        "  {\n"
        "    \"trait\": \"...\",\n"
        "    \"question\": \"...\",\n"
        "    \"selected_option\": \"...\"\n"
        "  }\n"
        "]\n"
        "No summaries, no commentary, no headings."
    )
    unique_suffix = f"\n<!-- batch_id: {filename} -->"
    json_text += f"\n\n{format_reminder}{unique_suffix}"

    try:
        editor_div = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.ProseMirror"))
        )
        print("🧠 Found ChatGPT input editor.")

        driver.execute_script("""
            const editor = arguments[0];
            editor.focus();
            editor.innerHTML = '';
            const text = arguments[1];
            editor.dispatchEvent(new InputEvent('input', { bubbles: true }));
            document.execCommand('insertText', false, text);
        """, editor_div, json_text)
        print("✍️ Injected JSON into editor.")

        send_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "composer-submit-button"))
        )
        send_button.click()
        print("📤 Submitted batch to ChatGPT.")

        WebDriverWait(driver, 20).until(
            lambda d: d.execute_script("return document.querySelectorAll('div.markdown').length > 0")
        )

        driver.execute_script("""
            window.__chatObserverContext__ = {
                done: false,
                lastText: '',
                lastChangeAt: Date.now(),
            };

            const thread = document.querySelector("#thread");
            const interval = 1000;
            const threshold = 5000;

            window.__chatObserverContext__.intervalHandle = setInterval(() => {
                const elms = thread.querySelectorAll("div.markdown");
                const latest = elms[elms.length - 1]?.innerText.trim() || "";
                if (latest !== window.__chatObserverContext__.lastText) {
                    window.__chatObserverContext__.lastText = latest;
                    window.__chatObserverContext__.lastChangeAt = Date.now();
                } else {
                    const duration = Date.now() - window.__chatObserverContext__.lastChangeAt;
                    if (duration > threshold && latest.length > 20) {
                        window.__chatObserverContext__.done = true;
                        clearInterval(window.__chatObserverContext__.intervalHandle);
                    }
                }
            }, interval);
        """)
        print("👁️ Waiting for response to stabilize...")
        WebDriverWait(driver, 180).until(
            lambda d: d.execute_script("return window.__chatObserverContext__?.done === true")
        )
        print("✅ Response stabilized.")

    except Exception as e:
        print(f"❌ Injection or response wait failed for {filename}: {e}")
        driver.save_screenshot(f"error_{filename}.png")
        continue

    try:
        elements = driver.find_elements(By.CSS_SELECTOR, "div.markdown")
        if not elements:
            raise ValueError("❌ No markdown elements found.")

        last_elem = elements[-1]
        response_text = last_elem.text.strip()
        response_html = last_elem.get_attribute("innerHTML").strip()

        # ⛏️ Try to extract code block manually
        code_block_json = None
        pre_blocks = last_elem.find_elements(By.TAG_NAME, "pre")
        for pre in pre_blocks:
            try:
                code_elem = pre.find_element(By.TAG_NAME, "code")
                class_attr = code_elem.get_attribute("class") or ""
                code_text = code_elem.text.strip()
                if "language-json" in class_attr or code_text.startswith("["):
                    code_block_json = code_text
                    break
            except:
                continue

        parse_source = code_block_json if code_block_json else response_text

        print("\n🔍 ----- DEBUG -----")
        print("📦 Using code block:", bool(code_block_json))
        print("🧾 Text preview:\n", response_text[:400])
        print("📎 HTML preview:\n", response_html[:400])
        print("🔍 ------------------\n")

        json_text_to_parse, source_type = extract_json_flexible(parse_source)

        if json_text_to_parse:
            try:
                sanitized = clean_json_string(json_text_to_parse)
                cleaned = json.loads(sanitized)
                with open(output_path, "w", encoding="utf-8") as out:
                    json.dump(cleaned, out, indent=2)
                print(f"✅ Saved JSON ({source_type}): {output_path}")
            except json.JSONDecodeError as e:
                print(f"⚠️ Decode error ({source_type}): {e}")
                with open(output_path, "w", encoding="utf-8") as out:
                    out.write(parse_source)
                with open(output_path + ".html", "w", encoding="utf-8") as out:
                    out.write(response_html)
                print("⚠️ Fallback saved: raw + .html")
        else:
            with open(output_path, "w", encoding="utf-8") as out:
                out.write(parse_source)
            with open(output_path + ".html", "w", encoding="utf-8") as out:
                out.write(response_html)
            print("⚠️ No pattern matched. Saved raw + .html.")

    except Exception as e:
        print(f"❌ Failed to process response: {e}")
        driver.save_screenshot(f"error_{filename}_parse.png")

    print("-" * 40)
    batch_count += 1

print("🎉 All batches submitted successfully.")
driver.quit()
