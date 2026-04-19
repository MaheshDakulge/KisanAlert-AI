import sys, os
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv(".env")

key = os.getenv("GEMINI_API_KEY", "").strip().strip('"')
print(f"Key len: {len(key)}, starts: {key[:8]}")

import google.genai as genai
client = genai.Client(api_key=key)
r = client.models.generate_content(model="gemini-2.0-flash", contents="Say Hello in one word.")
print("Gemini reply:", r.text)
