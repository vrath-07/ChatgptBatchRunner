import json
from huggingface_hub import login
# Paste your token here
login("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") 
from datasets import load_dataset
dataset = load_dataset("mirlab/TRAIT", cache_dir="./custom_hf_cache")
# Check available trait splits
print("Available Traits:", dataset.keys())

# Load a specific trait (e.g., Openness)
#openness_data = dataset["Openness"]

# Print the first question in the Openness trait
#print(openness_data[0])

# Combine questions from all traits into a single list
all_questions = []

for trait in dataset.keys():  # Loop through all traits
    trait_data = dataset[trait]
    for row in trait_data:
        all_questions.append({"trait": trait, "question": row["question"],"response_high1": row["response_high1"],
  "response_high2": row["response_high2"],
  "response_low1": row["response_low1"],
  "response_low2": row["response_low2"] })

# Print first few questions to verify
print(all_questions[:5])  # Displays sample questions from different traits
print(f"✅ Loaded {len(all_questions)} personality questions.")
# Step 4: Save the extracted questions to a JSON file
import json # Import the json module

with open("personality_questions.json", "w", encoding="utf-8") as f:
    json.dump(all_questions, f, indent=4, ensure_ascii=False)

