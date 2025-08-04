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
UNKNOWN_QUE_LOG_PATH = os.path.join(OUTPUT_DIR, "files_with_unknown_questions.log")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# === UTILS ===
def regex_friendly_normalizer(text):
    if not isinstance(text, str):
        return text
    replacements = {
        '“': '"', '”': '"',
        '‘': "'", '’': "'",
        '\u00A0': ' ',
        '\u200B': '',
        '\u2013': '-',
        '\u2014': '-',
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    return unicodedata.normalize("NFKC", text.strip())

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
        print(f"\n\U0001F4C2 Processing: {os.path.basename(path)}")
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

            print("🔹 Step 3: Escape selected_option quotes...")
            raw = brute_force_escape_selected_option_quotes(raw)

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

# === MAIN MAPPING LOGIC ===
def remap_selected_to_label(selected_path, mapping_path, filename):
    selected_data = try_load_json(selected_path)
    original_data = try_load_json(mapping_path, fix_if_needed=False)

    if selected_data is None or original_data is None:
        return None

    remapped = []
    has_unknown = False

    for selected_q in selected_data:
        match_found = False
        norm_selected_q = regex_friendly_normalizer(selected_q["question"])
        for orig_q in original_data:
            norm_orig_q = regex_friendly_normalizer(orig_q["question"])
            if norm_selected_q == norm_orig_q:
                selected_text = regex_friendly_normalizer(selected_q["selected_option"])
                norm_mapping = {
                    regex_friendly_normalizer(k): v
                    for k, v in orig_q.get("original_mapping", {}).items()
                }

                label = norm_mapping.get(selected_text)

                if label is None:
                    best_match = None
                    best_score = 0.0
                    for k_norm, v in norm_mapping.items():
                        ratio = SequenceMatcher(None, k_norm, selected_text).ratio()
                        if ratio > best_score:
                            best_score = ratio
                            best_match = k_norm

                    print(f"❌ Could not map:\n→ Question: {selected_q['question']}\n→ Selected: {selected_text}\n→ Closest match: {best_match}\n→ Similarity: {best_score:.3f}\n→ Comment:\n")
                    with open(UNKNOWN_LOG_PATH, "a", encoding="utf-8") as log:
                        log.write(f"{filename} — Trait: {selected_q['trait']}\n")
                        log.write(f"→ Question: {selected_q['question']}\n")
                        log.write(f"→ Selected: {selected_text}\n")
                        log.write(f"→ Closest match: {best_match}\n")
                        log.write(f"→ Similarity: {best_score:.3f}\n")
                        log.write(f"→ Comment:\n\n")

                    label = "UNKNOWN"
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
            best_question_match = None
            best_question_score = 0.0
            for orig_q in original_data:
                ratio = SequenceMatcher(None, regex_friendly_normalizer(orig_q["question"]), norm_selected_q).ratio()
                if ratio > best_question_score:
                    best_question_score = ratio
                    best_question_match = orig_q["question"]

            with open(UNKNOWN_QUE_LOG_PATH, "a", encoding="utf-8") as log:
                log.write(f"{filename} — Trait: {selected_q['trait']}\n")
                log.write(f"→ Question: {selected_q['question']}\n")
                log.write(f"→ Closest match: {best_question_match}\n")
                log.write(f"→ Similarity: {best_question_score:.3f}\n")
                log.write(f"→ Comment:\n\n")

            print(f"[⚠] No question match for: {selected_q['question'][:60]}..., in file: {filename}")


    return remapped

# === PROCESS ALL BATCH FILES ===
success_count = 0
fail_count = 0

with open(UNKNOWN_LOG_PATH, "w", encoding="utf-8") as f:
    f.write("Files with at least one UNKNOWN response:\n\n")

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