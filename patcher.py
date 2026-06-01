# patcher.py
import re

filename = "app.py"

print("🔄 Reading app.py...")
with open(filename, "r", encoding="utf-8") as f:
    code = f.read()

# Fix 1: Ensure logo_filename is safely defined at the very top of the script
if "logo_filename =" not in code[:2000]:
    print("📌 Injecting global asset initializations at the top...")
    setup_block = (
        "import os\n"
        "import base64\n"
        "import pandas as pd\n"
        "import streamlit as st\n\n"
        "# --- GLOBAL INITIALIZATIONS ---\n"
        "logo_filename = 'logo.png'\n"
        "logo_base64 = ''\n"
    )
    # Put it right after the very first line of the script
    code = setup_block + code

# Fix 2: Clean up the broken conditional block execution 
# by changing the global check to a safe string validation
print("🛠️ Fixing the line 532 error pattern...")
code = code.replace("if os.path.exists(logo_filename):", "if 'logo_filename' in globals() and os.path.exists(logo_filename):")

with open(filename, "w", encoding="utf-8") as f:
    f.write(code)

print("✅ Complete! Commit and push these updates, then refresh your Streamlit Cloud portal.")
