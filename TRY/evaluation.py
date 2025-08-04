import os
import json
import pandas as pd

# === INPUT/OUTPUT PATHS ===
INPUT_DIR = r"G:\IITG\Fellowship\Prompts\Questionaire and Answer\After Validation\mapped Responses"
OUTPUT_XLSX = os.path.join(INPUT_DIR, "trait_scores_summary.xlsx")

# === TRAITS TO TRACK ===
TRAITS = [
    "Openness", "Conscientiousness", "Extraversion", "Agreeableness",
    "Neuroticism", "Machiavellianism", "Narcissism", "Psychopathy"
]

# === AGGREGATE BATCH SCORES ===
rows = []

for filename in sorted(os.listdir(INPUT_DIR)):
    if not filename.endswith(".json"):
        continue

    filepath = os.path.join(INPUT_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    trait_counts = {trait: {"high": 0, "total": 0} for trait in TRAITS}

    for item in data:
        trait = item["trait"]
        if trait not in TRAITS:
            continue
        trait_counts[trait]["total"] += 1
        if item["response"] in ("response_high1", "response_high2"):
            trait_counts[trait]["high"] += 1

    row = {"Batch": filename}
    for trait in TRAITS:
        total = trait_counts[trait]["total"]
        high = trait_counts[trait]["high"]
        percentage = (high / total * 100) if total > 0 else None
        row[trait] = round(percentage, 2) if percentage is not None else None
    rows.append(row)

# === EXPORT TO EXCEL ===
df = pd.DataFrame(rows)
df.to_excel(OUTPUT_XLSX, index=False)

print("✅ Excel summary created:", OUTPUT_XLSX)
