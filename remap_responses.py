import os
import json
import re
import unicodedata
from difflib import SequenceMatcher

# === CONFIGURATION ===
SELECTED_RESPONSES_DIR = r"G:\IITG\Fellowship\Experiment Design\Code\Responses"
MAPPING_BATCHES_DIR = r"G:\IITG\Fellowship\Experiment Design\Code\trait_batches_500"
OUTPUT_DIR = r"G:\IITG\Fellowship\Experiment Design\Code\mapped Responses"
UNKNOWN_LOG_PATH = os.path.join(OUTPUT_DIR, "files_with_unknown_responses.log")

os.makedirs(OUTPUT_DIR, exist_ok=True)

def is_match(q1, q2, threshold=0.98):
    return SequenceMatcher(None, q1.strip(), q2.strip()).ratio() >= threshold

def normalize_quotes(text):
    if not isinstance(text, str):
        return text
    return unicodedata.normalize('NFKD', text).replace("’", "'").replace("“", '"').replace("”", '"')

def brute_force_escape_selected_option_quotes(raw_json):
    def fixer(match):
        key = match.group(1)
        val = match.group(2)
        fixed_val = val[1:-1].replace('"', '\\"')
        return f'{key}"{fixed_val}"'

    pattern = r'("selected_option"\s*:\s*)"(.*?)"'
    return re.sub(pattern, fixer, raw_json, flags=re.DOTALL)

def try_load_json(path, fix_if_needed=True):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"\n📂 Processing: {os.path.basename(path)}")
        if not fix_if_needed:
            raise
        print(f"❌ JSONDecodeError at line {e.lineno}, col {e.colno} — {e.msg}")
        print("🔧 Attempting deep repair...")

        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()

            print("🔹 Step 1: Quote property names...")
            raw = re.sub(
                r'(?<=\{|,|\n)(\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*):',
                lambda m: f'{m.group(1)}"{m.group(2)}"{m.group(3)}:',
                raw
            )

            print("🔹 Step 2: Remove trailing commas...")
            raw = re.sub(r',\s*([\]}])', r'\1', raw)

            print("🔹 Step 3: Force-escape selected_option quotes...")
            raw = brute_force_escape_selected_option_quotes(raw)

            preview = raw.splitlines()[5] if len(raw.splitlines()) > 5 else "(short file)"
            print("🔍 Line 6 preview:", preview)

            parsed = json.loads(raw)

            with open(path, "w", encoding="utf-8") as f:
                json.dump(parsed, f, indent=2, ensure_ascii=False)

            print("✅ Fixed and re-saved.")
            return parsed

        except json.JSONDecodeError as e2:
            print(f"❌ Final parse failed: {e2.msg} at line {e2.lineno}, col {e2.colno}")
        except Exception as fix_err:
            print(f"❌ Unexpected error: {fix_err}")

        return None

def remap_selected_to_label(selected_path, mapping_path, filename):
    selected_data = try_load_json(selected_path)
    original_data = try_load_json(mapping_path, fix_if_needed=False)

    if selected_data is None or original_data is None:
        return None

    remapped = []
    has_unknown = False

    for selected_q in selected_data:
        match_found = False
        for orig_q in original_data:
            if is_match(selected_q["question"], orig_q["question"]):
                selected_text = normalize_quotes(selected_q["selected_option"])
                norm_mapping = {normalize_quotes(k): v for k, v in orig_q["original_mapping"].items()}
                label = norm_mapping.get(selected_text, "UNKNOWN")
                if label == "UNKNOWN":
                    has_unknown = True
                remapped.append({
                    "trait": selected_q["trait"],
                    "question": selected_q["question"],
                    "selected_option": selected_q["selected_option"],
                    "response": label
                })
                match_found = True
                break
        if not match_found:
            print(f"[⚠] No match for: {selected_q['question'][:60]}..., {filename}")
    if has_unknown:
        with open(UNKNOWN_LOG_PATH, "a", encoding="utf-8") as log:
            log.write(filename + "\n")
    return remapped

# === PROCESS ALL BATCH FILES ===
success_count = 0
fail_count = 0

# Clear old log
with open(UNKNOWN_LOG_PATH, "w", encoding="utf-8") as f:
    f.write("Files with at least one UNKNOWN response:\n")

for filename in os.listdir(SELECTED_RESPONSES_DIR):
    selected_file = os.path.join(SELECTED_RESPONSES_DIR, filename)
    mapping_file = os.path.join(MAPPING_BATCHES_DIR, filename)

    if os.path.isfile(selected_file) and os.path.isfile(mapping_file):
        output = remap_selected_to_label(selected_file, mapping_file, filename)
        if output is not None:
            output_path = os.path.join(OUTPUT_DIR, filename)
            with open(output_path, "w", encoding="utf-8") as out_file:
                json.dump(output, out_file, indent=2, ensure_ascii=False)
            success_count += 1
        else:
            fail_count += 1

# === FINAL REPORT ===
print("\n📊 DONE")
print(f"✅ Successfully remapped: {success_count}")
print(f"❌ Failed/skipped: {fail_count}")
print(f"📁 Output saved to: {OUTPUT_DIR}")
print(f"📝 Logged unknown responses to: {UNKNOWN_LOG_PATH}")