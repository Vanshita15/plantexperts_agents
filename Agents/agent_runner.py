# import os
# from openai import OpenAI
# from dotenv import load_dotenv

# load_dotenv()
# api_key = os.getenv("OPENAI_API_KEY")
# print("OPENAI_API_KEY present?:", bool(api_key))
# if not api_key:
#     raise SystemExit("No OPENAI_API_KEY")

# client = OpenAI(api_key=api_key)
# try:
#     resp = client.chat.completions.create(
#         model="gpt-4.1",
#         messages=[{"role":"user","content":"Say hello in one line."}],
#         max_tokens=50
#     )
#     print("OK:", resp.choices[0].message.content)
# except Exception as e:
#     print("ERROR:", type(e).__name__, e)

import os, sys
from pathlib import Path
print("CWD:", os.getcwd())
print("This file:", Path(__file__).resolve())
print("sys.path[0]:", sys.path[0])
print("sys.path (first 10):")
for p in sys.path[:10]:
    print("  ", p)
print("Exists backend folder?:", Path("backend").exists())
print("backend files:", list(Path("backend").glob("*")) if Path("backend").exists() else "no backend")
