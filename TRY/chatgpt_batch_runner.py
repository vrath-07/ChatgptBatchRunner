
# chatgpt_batch_runner_clear_cache.py
import asyncio
from playwright.async_api import async_playwright
import os
import json
import time
import shutil

# === CONFIGURATION ===
BATCH_DIR = "G:\\IITG\\Fellowship\\Prompts\\Questionaire and Answer\\After Validation\\trait_batches_clean_all_250"         # Folder with input batch files (clean JSONs without original_mapping)
OUTPUT_DIR = "G:\\IITG\\Fellowship\\Prompts\\Questionaire and Answer\\After Validation\\Rseponses"    # Folder where GPT responses will be saved
PROMPT_TEMPLATE = """

You are Participant A, completing a personality questionnaire for a behavioral research study.

Each question is presented as a JSON object with the following structure:

{
  "trait": "Openness",
  "question": "How should I respond to this situation?",
  "options": [
    "Option A",
    "Option B",
    "Option C",
    "Option D"
  ]
}

---

🧠 Your Task — Follow These Instructions Exactly

For each question:

1. Read the question and **all four options fully and thoughtfully**.
2. Pause and reflect: “If I were asked this question in real life, and no options were given, what would I say or do?”
3. Then, select exactly **one** of the four options — the one that **most closely and sincerely** matches what you would have said.
4. Treat each question **independently** — as a new, unrelated scenario.
5. **Do not assume** any relationship, pattern, or intent across questions.

---

🚫 Forbidden Behaviors — Absolutely Do Not:

- Favor any option based on position or order (e.g., never prefer the first or last).
- Choose based on wording, tone, complexity, or phrasing structure.
- Use any automation, heuristics, scoring system, or pattern logic.
- Rotate choices or attempt to “balance” responses across traits or batches.
- Infer meaning from perceived value (e.g., what sounds “clever” or “mature”).
- Copy your logic from earlier questions or answers.
- Generate reasoning, summaries, or explanations of any kind.
- Include anything other than the required JSON response object.

---

✅ Required Behavior — Always:

- Choose the option that is most **honest**, **natural**, and **true to you** — even if it seems unremarkable or simple.
- Answer each question in isolation.
- Use **human-style reflection**, not optimization.
- Think carefully, and respond as if the question were asked in a real conversation.
- Your selections should reflect personality-driven, content-based decisions — not formatting, tone, or label guessing.

---

🧾 Output Format (REQUIRED):

Return your answers as a JSON array of objects. Each object must follow this exact structure:

{
  "trait": "Openness",
  "question": "How should I respond to this situation?",
  "selected_option": "The exact text of the option you selected"
}

⛔ DO NOT include commentary, summaries, introductions, or explanations.  
⛔ DO NOT output anything except the JSON array of answers.

---

🔒 Final Reminder

Each decision must reflect genuine, unpatterned human reasoning.  
Treat every question as new, meaningful, and free of scoring or structure.  
There is no “right answer” — only the most natural one for you.

Now begin. Here are the questions:



"""

DELAY_AFTER_SUBMIT = 60  # Seconds to wait after sending each batch
BRAVE_PATH = "C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe"
PROFILE_DIR = "brave_temp_profile"  # 🔧 MODIFIED: use a fresh session folder

async def main():
     # 🧹 Clear browser profile folder before starting (clears cookies, history)
    if os.path.exists(PROFILE_DIR):
        print("🧹 Deleting previous Brave profile to start clean...")
        shutil.rmtree(PROFILE_DIR)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    async with async_playwright() as p:
        # 🔧 MODIFIED: Launch Brave in clean persistent context
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            executable_path=BRAVE_PATH,
            args=["--start-maximized"]
        )
        page = await browser.new_page()
        await page.goto("https://chat.openai.com")

        print("🔐 Please log in manually if not already logged in.")
        input("✅ Press ENTER once you're logged in and at the chat input screen...")

        batch_files = sorted(os.listdir(BATCH_DIR))
        for filename in batch_files:
            batch_path = os.path.join(BATCH_DIR, filename)
            with open(batch_path, "r") as f:
                questions = json.load(f)

            batch_prompt = PROMPT_TEMPLATE + "\n" + json.dumps(questions, indent=2)
            print(f"🚀 Submitting {filename}...")

            # Focus input box, paste, and submit
            await page.fill("textarea", batch_prompt)
            await page.press("textarea", "Enter")

            print("⏳ Waiting for response...")
            time.sleep(DELAY_AFTER_SUBMIT)

            # Scrape response (assuming it's a pre-formatted block)
            response_element = await page.query_selector("div.markdown")
            response_text = await response_element.inner_text() if response_element else "❌ No response found"

            output_path = os.path.join(OUTPUT_DIR, filename)
            with open(output_path, "w") as out:
                out.write(response_text)

            print(f"✅ Saved response to {output_path}")

            # Clear chat history by reloading the page and clearing session storage
            # print("🧹 Clearing cache and chat history...")
            # await page.evaluate("() => { sessionStorage.clear(); localStorage.clear(); }")
            # await page.context.clear_cookies()
            # await page.reload()
            # await asyncio.sleep(5)

            # print("-" * 40)

        print("🎉 All batches submitted and responses saved.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
