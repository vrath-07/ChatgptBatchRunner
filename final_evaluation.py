import os
import json
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict

# === CONFIGURATION ===
INPUT_DIR = r"G:\IITG\Fellowship\Experiment Design\Code\mapped Responses"
EXCEL_OUTPUT_PATH = os.path.join(INPUT_DIR, "trait_high_low_counts.xlsx")
SUBPLOT_OUTPUT_PATH = os.path.join(INPUT_DIR, "trait_trend_subplots.png")
TRAITS = [
    "Openness", "Conscientiousness", "Extraversion", "Agreeableness",
    "Neuroticism", "Machiavellianism", "Narcissism", "Psychopathy"
]

# === AGGREGATE BATCH-WISE TRAIT RESPONSES ===
batch_rows = []
overall_counts = defaultdict(lambda: {"high": 0, "low": 0, "total": 0})

for filename in sorted(os.listdir(INPUT_DIR)):
    if not filename.endswith(".json"):
        continue

    filepath = os.path.join(INPUT_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    trait_batch_row = {"Batch": filename}
    for trait in TRAITS:
        trait_batch_row[f"{trait}_high"] = 0
        trait_batch_row[f"{trait}_low"] = 0

    for item in data:
        trait = item.get("trait")
        if trait not in TRAITS:
            continue
        response = item.get("response")
        if response in ("response_high1", "response_high2"):
            trait_batch_row[f"{trait}_high"] += 1
            overall_counts[trait]["high"] += 1
        elif response in ("response_low1", "response_low2"):
            trait_batch_row[f"{trait}_low"] += 1
            overall_counts[trait]["low"] += 1
        overall_counts[trait]["total"] += 1

    batch_rows.append(trait_batch_row)

# === EXPORT TO EXCEL ===
df = pd.DataFrame(batch_rows)
df.to_excel(EXCEL_OUTPUT_PATH, index=False)

# === PRINT OVERALL PROFILE ===
print("\n🧠 Overall Personality Profile Across All Batches:\n")
print(f"{'Trait':<20}{'High':>10}{'Low':>10}{'Total':>10}{'Percent High':>15}")
print("-" * 65)
for trait in TRAITS:
    high = overall_counts[trait]["high"]
    low = overall_counts[trait]["low"]
    total = overall_counts[trait]["total"]
    percent = (high / total * 100) if total > 0 else 0.0
    print(f"{trait:<20}{high:>10}{low:>10}{total:>10}{percent:>14.2f}%")

print("\n✅ Excel summary created:", EXCEL_OUTPUT_PATH)

# === PLOT SUBPLOTS FOR EACH TRAIT WITH SMOOTHING ===
rolling_window = max(5, len(df) // 50)  # Dynamically chosen window size

fig, axes = plt.subplots(nrows=4, ncols=2, figsize=(18, 20), sharex=True)
axes = axes.flatten()

for i, trait in enumerate(TRAITS):
    ax = axes[i]

    high_series = df[f"{trait}_high"].rolling(window=rolling_window, min_periods=1).mean()
    low_series = df[f"{trait}_low"].rolling(window=rolling_window, min_periods=1).mean()

    ax.plot(high_series, label="High", color='blue', linewidth=1.5)
    ax.plot(low_series, label="Low", color='red', linestyle='--', linewidth=1.5)
    
    ax.set_title(trait, fontsize=14)
    ax.set_ylabel("Smoothed Count")
    ax.grid(True, linestyle='--', alpha=0.3)
    ax.legend()

# Set x-axis label only on bottom row
for ax in axes[-2:]:
    ax.set_xlabel("Batch Index", fontsize=12)

plt.suptitle("High vs Low Trait Responses Across Batches (Smoothed)", fontsize=20)
plt.tight_layout(rect=[0, 0.03, 1, 0.897])
plt.savefig(SUBPLOT_OUTPUT_PATH, dpi=300)
plt.show()

print("📊 Subplot-based (smoothed) trait trend graph saved as:", SUBPLOT_OUTPUT_PATH)

