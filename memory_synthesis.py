import os
from datetime import datetime
from anthropic import Anthropic
from openai import OpenAI
from dotenv import load_dotenv

# Set up paths
MEM_DIR = os.path.expanduser("~/agent_memory")

load_dotenv(os.path.join(MEM_DIR, ".env"))

CURRENT_PATH = os.path.join(MEM_DIR, "CURRENT.md")
today_str = datetime.now().strftime("%Y-%m-%d")
DAILY_PATH = os.path.join(MEM_DIR, "daily", f"{today_str}.md")

# If no daily log today, exit
if not os.path.exists(DAILY_PATH):
    print(f"No daily log found for {today_str}. Exiting.")
    exit(0)

# Read files
with open(CURRENT_PATH, "r") as f:
    current_content = f.read()
with open(DAILY_PATH, "r") as f:
    daily_content = f.read()

# Call Claude API
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY")
)

prompt = f"""
You are the memory synthesis engine for Jake.
Review today's daily log and the active priorities file. 
If priorities have shifted or new tasks emerged, output the complete, updated CURRENT.md file. 
Keep the strict 100-line limit and markdown formatting. Do not output any conversational text, only the raw file content.

--- CURRENT.md ---
{current_content}

--- TODAY'S LOG ---
{daily_content}
"""

response = client.chat.completions.create(
    model="nvidia/nemotron-3-super-120b-a12b:free",
    messages=[{"role": "user", "content": prompt}]
)

new_current = response.content[0].text

# Overwrite CURRENT.md
with open(CURRENT_PATH, "w") as f:
    f.write(new_current)

print(f"Synthesis complete for {today_str}.")
